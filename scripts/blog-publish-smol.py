#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博客发布一次性脚本（smolagents 版，替代 reasonix 引擎）。

用法:
    python blog-publish-smol.py <草稿路径> [--force] [--dry-run | --dry-run-agent]

    <草稿路径>  可传完整 _drafts/xxx 或仅文件名/子路径；文件必须存在。
    --force     跳过发布前的交互确认（用于脚本/定时场景）。
    --dry-run      模拟运行（零 token）：校验草稿/任务模板/依赖/key/git，不调用模型、不写文件。
    --dry-run-agent 完整模拟（消耗 token）：在临时副本中跑完整流程（smolagents + 写 _posts/ +
                   git push 到本地 origin），不触碰真实仓库与远端。

职责划分（本脚本 vs smolagents 代理）:
  - smolagents 代理（ToolCallingAgent，仅两个工具 read_file/write_file）：只做内容——读草稿、
    优化正文、写 frontmatter、写入 _posts/。不做 git，也不删除草稿（均由本脚本确定性处理）。
  - 本脚本：确定性收尾——删除草稿、修复 frontmatter 的 YAML 引号问题、精确 git add/commit/push。
    无论代理退出状态如何，只要新文章已写入，就保证落库并推送到远端。

设计要点:
  1. 固定前缀提升缓存命中（与 reasonix 版同思路）:
     模板 scripts/blog-publish.prompt.md 除文末「任务参数」块外完全静态；system_prompt 取静态段
     （第 1-15 行逐字），task 取「任务参数」块并替换 __DRAFT__/__DATE__ 两个动态占位符。
     smolagents 的 system message + 工具 schema 是确定性生成的固定前缀 → 命中 DeepSeek 服务端
     prompt cache（缓存命中/未命中字段通过 litellm CustomLogger 拦截原始响应读取）。
  2. 低 token 消耗: 仅两个工具、模板精简；--output-format 由库内结构化日志取代正则解析。
  3. 成本核算: litellm 价格表无 deepseek-v4-flash 且无法表达峰谷价 → 本脚本按官方价（北京
     峰 9-12/14-18、谷半价）自行计算 CNY。
  4. 多底座: 通过 litellm 换 model_id 前缀即可切模型；PUBLISH_MODEL/PUBLISH_API_BASE 可覆盖。
  5. API key: OS 环境变量 → 仓库 .env → 首次从 reasonix 全局 .env 自动迁移到仓库 .env。

模型配置（环境变量可覆盖，默认 DeepSeek V4 Flash）:
    PUBLISH_MODEL       默认 deepseek/deepseek-v4-flash
    PUBLISH_API_BASE    默认 https://api.deepseek.com
    PUBLISH_TEMPERATURE 默认 0.3
    PUBLISH_MAX_TOKENS  默认 8192
    PUBLISH_MAX_STEPS   默认 10
"""

import datetime
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FILE = os.path.join(ROOT, "scripts", "blog-publish.prompt.md")
POSTS_DIR = os.path.join(ROOT, "_posts")
REPO_ENV = os.path.join(ROOT, ".env")
REASONIX_ENV = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "reasonix", ".env")
PLACEHOLDER_DRAFT = "__DRAFT__"
PLACEHOLDER_DATE = "__DATE__"
PARAM_HEADING = "## 任务参数"
GIT_NAME = "wangyajun"
GIT_EMAIL = "hust_wangyajun@163.com"
BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def beijing_now():
    """当前北京时刻（固定 +8 偏移，不依赖 Windows 时区数据库）。"""
    return datetime.datetime.now(BEIJING_TZ)


def is_peak(dt):
    """DeepSeek 峰时：北京 9-12 与 14-18（含边界 9/12/14/18 之外为谷）。"""
    return (9 <= dt.hour < 12) or (14 <= dt.hour < 18)


PRICES = {
    "peak": {"hit": 0.10, "miss": 3.00, "out": 9.00},  # 元 / 1M tokens
    "off": {"hit": 0.05, "miss": 1.50, "out": 4.50},
}


def compute_cost(hit, miss, out):
    """按当前北京峰/谷价表计算 CNY 成本，返回 (cost, price_table)。"""
    table = PRICES["peak"] if is_peak(beijing_now()) else PRICES["off"]
    cost = (hit * table["hit"] + miss * table["miss"] + out * table["out"]) / 1_000_000.0
    return cost, table


def model_config():
    """读取模型配置（环境变量覆盖默认值）。"""
    # DeepSeek V4 默认开 thinking，而 thinking 模式不接受 tool_choice="required"
    # （smolagents 默认强制调用工具）→ 默认关闭 thinking（extra_body 透传）。
    # 换到支持 thinking+工具并存的底座时设 PUBLISH_THINKING=on。
    return {
        "model_id": os.environ.get("PUBLISH_MODEL", "deepseek/deepseek-v4-flash"),
        "api_base": os.environ.get("PUBLISH_API_BASE", "https://api.deepseek.com"),
        "temperature": float(os.environ.get("PUBLISH_TEMPERATURE", "0.3")),
        "max_tokens": int(os.environ.get("PUBLISH_MAX_TOKENS", "8192")),
        "max_steps": int(os.environ.get("PUBLISH_MAX_STEPS", "10")),
        "thinking": os.environ.get("PUBLISH_THINKING", "off").lower() == "on",
    }


def git(args, check=True, retry=False):
    """在仓库根目录执行 git；retry=True 时失败后短暂重试一次（应对偶发网络抖动）。"""
    r = subprocess.run(["git"] + args, cwd=ROOT, encoding="utf-8",
                       errors="replace", capture_output=True)
    if retry and r.returncode != 0:
        time.sleep(2)
        r = subprocess.run(["git"] + args, cwd=ROOT, encoding="utf-8",
                           errors="replace", capture_output=True)
    if check and r.returncode != 0:
        sys.exit(f"错误: git {' '.join(args)} 失败 -> {r.stderr.strip()}")
    return r


def ensure_git_identity():
    """若本仓库未配置 git 身份，则补配（仅仓库级，不改全局）。"""
    name = git(["config", "user.name"], check=False).stdout.strip()
    email = git(["config", "user.email"], check=False).stdout.strip()
    if not name or not email:
        if not name:
            git(["config", "user.name", GIT_NAME])
        if not email:
            git(["config", "user.email", GIT_EMAIL])
        print(f"[提示] 已为本仓库设置 git 身份: {GIT_NAME} <{GIT_EMAIL}>")


def normalize_rel(raw):
    """归一化草稿路径为仓库相对路径（要求位于 _drafts/ 下）。"""
    raw = raw.strip().replace("\\", "/").lstrip("./").strip("/")
    # 兼容单数 _draft/ 前缀（用户口语常写 _draft/1.md）
    if raw.startswith("_draft/"):
        raw = "_drafts/" + raw[len("_draft/"):]
    if raw.startswith("_drafts/"):
        rel = raw
    else:
        rel = f"_drafts/{raw}"
    return rel


def build_parts(rel):
    """拆分提示词模板 → (system_prompt, task)。

    system_prompt = 模板固定指令段（「任务参数」之前，逐字保留）→ 字节级稳定的缓存前缀。
    task          = 「任务参数」块 + 替换 __DRAFT__/__DATE__ 两个动态值。
    """
    if not os.path.isfile(PROMPT_FILE):
        sys.exit(f"错误: 找不到提示词模板 {PROMPT_FILE}")
    with open(PROMPT_FILE, encoding="utf-8") as f:
        body = f.read()
    for ph in (PLACEHOLDER_DRAFT, PLACEHOLDER_DATE):
        cnt = body.count(ph)
        if cnt != 1:
            sys.exit(f"错误: 模板中 {ph} 占位符数量为 {cnt}（应为 1）")
    idx = body.rfind(PARAM_HEADING)
    if idx < 0:
        sys.exit("错误: 模板中缺少「## 任务参数」块")
    system_prompt = body[:idx].rstrip("\n")
    task = (body[idx:].replace(PLACEHOLDER_DRAFT, rel)
                       .replace(PLACEHOLDER_DATE, today_str()))
    return system_prompt, task


def _parse_simple_env(path):
    """极简 KEY=value 解析器（python-dotenv 不可用时的兜底）。"""
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_repo_env():
    """加载仓库 .env 到进程环境（不覆盖已存在的 OS 环境变量）。"""
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ENV)
    except ImportError:
        for k, v in _parse_simple_env(REPO_ENV).items():
            os.environ.setdefault(k, v)


def resolve_api_key(allow_write=True):
    """解析 DEEPSEEK_API_KEY。优先级: OS 环境变量 → 仓库 .env → reasonix 全局 .env。

    allow_write=True 时若仓库 .env 缺失但 reasonix 有 key，则首次自动复制到仓库 .env
    （已 gitignore）。返回 (key, 来源说明)。
    """
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"], "OS 环境变量"
    load_repo_env()
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"], "仓库 .env"
    if os.path.isfile(REASONIX_ENV):
        key = _parse_simple_env(REASONIX_ENV).get("DEEPSEEK_API_KEY")
        if key and allow_write and not os.path.isfile(REPO_ENV):
            with open(REPO_ENV, "w", encoding="utf-8") as f:
                f.write(f"DEEPSEEK_API_KEY={key}\n")
            print("[提示] 已从 reasonix 配置自动创建仓库级 .env（已加入 .gitignore）")
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key
            label = ("仓库 .env（已从 reasonix 复制）" if allow_write
                     else "reasonix .env（真实运行将复制到仓库 .env）")
            return key, label
    sys.exit("错误: 未找到 DEEPSEEK_API_KEY（请设置环境变量或在仓库 .env 中提供）")


def snapshot_posts():
    """返回当前 _posts/ 下 .md 文件名集合。"""
    if not os.path.isdir(POSTS_DIR):
        return set()
    return {f for f in os.listdir(POSTS_DIR) if f.endswith(".md")}


def find_new_posts(before):
    after = {f for f in os.listdir(POSTS_DIR) if f.endswith(".md")} if os.path.isdir(POSTS_DIR) else set()
    return sorted(after - before)


def fix_frontmatter(path):
    """确定性修复 title/subtitle 行的 YAML 双引号嵌套问题；返回是否改动。

    典型坏例（模型未处理内层引号时产生）:
        title: "AI正从"功能"演变为"基础设施"——…"
    修复为合法 YAML（单引号括起，内层双引号原样保留）:
        title: 'AI正从"功能"演变为"基础设施"——…'
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return False
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return False
    pat = re.compile(r'^(title|subtitle):(\s*)(")(.*)(")\s*$')
    changed = False
    for i in range(1, end):
        m = pat.match(lines[i])
        if m and '"' in m.group(4):
            safe = m.group(4).replace("'", "''")  # 单引号字符串内需翻倍转义
            lines[i] = f"{m.group(1)}:{m.group(2)}'{safe}'\n"
            changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    return changed


def ensure_date(path, today):
    """确定性兜底：确保 frontmatter 的 date 与文件名日期前缀均为 today；返回最终路径。"""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if len(lines) >= 2 and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end:
            for i in range(1, end):
                if lines[i].startswith("date:"):
                    if today not in lines[i]:
                        lines[i] = f"date: {today}\n"
                        print(f"[修复] frontmatter date 改为今天: {today}")
                    break
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
    name = os.path.basename(path)
    if not name.startswith(today + "-"):
        m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", name)
        slug = m.group(1) if m else name
        new_path = os.path.join(os.path.dirname(path), f"{today}-{slug}")
        if os.path.exists(new_path):
            print(f"[警告] 目标文件已存在，将被本次发布覆盖: {os.path.basename(new_path)}")
        os.replace(path, new_path)  # 原子替换，跨平台
        print(f"[修复] 文件名日期前缀改为今天: {os.path.basename(new_path)}")
        return new_path
    return path


def read_title(path):
    """从 frontmatter 读取 title（去掉包裹引号）；失败返回 None。"""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("title:"):
                v = line[len("title:"):].strip()
                if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
                    v = v[1:-1]
                return v
    return None


def publish_git(post_name, title):
    """精确提交并推送新文章，返回 commit 短哈希。"""
    git(["add", os.path.join("_posts", post_name)])
    # 若模型已自行提交过（staged 为空），则跳过 commit，仅补 push
    if git(["diff", "--cached", "--quiet"], check=False).returncode != 0:
        git(["commit", "-m", f"blog: 发布 {title}"])
    git(["push", "origin", "master"], retry=True)
    return git(["rev-parse", "--short", "HEAD"], check=False).stdout.strip()


# ---------------------------------------------------------------- smolagents ---

def _import_smolagents():
    """导入 smolagents 相关符号；版本差异处做兜底。返回 (model_cls, agent_cls, tool_dec, log_level, err_cls)。"""
    try:
        from smolagents import LiteLLMModel, ToolCallingAgent, tool
    except ImportError as e:
        sys.exit(f"错误: 未安装 smolagents，请先运行:\n"
                 f"  .\\.venv\\Scripts\\python.exe -m pip install \"smolagents[litellm]==1.26.0\"\n({e})")
    try:
        from smolagents import LogLevel
    except Exception:
        try:
            from smolagents.logger import LogLevel
        except Exception:
            LogLevel = None
    # 异常类逐项导入兜底（版本差异：1.26 无 ModelLimitHitError）
    AgentError = AgentMaxStepsError = ModelLimitHitError = None
    try:
        from smolagents import AgentError
    except Exception:
        pass
    try:
        from smolagents import AgentMaxStepsError
    except Exception:
        pass
    try:
        from smolagents import ModelLimitHitError
    except Exception:
        pass
    return LiteLLMModel, ToolCallingAgent, tool, LogLevel, (AgentError, AgentMaxStepsError, ModelLimitHitError)


def _resolve_under_root(path):
    """把仓库相对路径解析到 ROOT 内绝对路径；越界则抛 ValueError（防止模型访问仓库外）。"""
    p = os.path.normpath(os.path.join(ROOT, path))
    if os.path.commonpath([ROOT, p]) != os.path.normpath(ROOT):
        raise ValueError(f"路径越界（不允许访问仓库外部）: {path}")
    return p


def make_tools(tool):
    """构造供代理使用的两个自定义工具（仅内容读写，UTF-8）。"""
    @tool
    def read_file(path: str) -> str:
        """读取仓库内的文本文件（UTF-8）。

        Args:
            path: 仓库相对路径，如 _drafts/3 或 _posts/2026-08-19-xxx.md。
        Returns:
            文件完整内容；若文件不存在或读取失败，返回以“错误：”开头的字符串。
        """
        try:
            p = _resolve_under_root(path)
        except ValueError as e:
            return f"错误：{e}"
        if not os.path.isfile(p):
            return f"错误：文件不存在 -> {path}"
        try:
            with open(p, encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            return f"错误：读取失败 {path} -> {e}"

    @tool
    def write_file(path: str, content: str) -> str:
        """将完整内容写入仓库内文件（UTF-8），父目录不存在时自动创建。

        Args:
            path: 仓库相对路径，如 _posts/2026-08-19-xxx.md。
            content: 要写入的完整文件内容。
        Returns:
            成功返回“已写入 <path>”；失败返回以“错误：”开头的字符串。
        """
        try:
            p = _resolve_under_root(path)
        except ValueError as e:
            return f"错误：{e}"
        try:
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            return f"错误：写入失败 {path} -> {e}"
        return f"已写入 {path}"

    return [read_file, write_file]


# ------------------------------------------------------------------ litellm ---

def make_usage_logger():
    """注册 litellm 成功回调，累计 token / 缓存命中，供指标行使用。"""
    import litellm

    class UsageLogger(litellm.CustomLogger):
        def __init__(self):
            self.input_tokens = 0
            self.output_tokens = 0
            self.cache_hit = 0
            self.have_split = False  # 是否至少一次拿到缓存命中字段
            self.model_calls = 0

        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            self.model_calls += 1
            usage = getattr(response_obj, "usage", None)
            if usage is None:
                return
            inp = int(getattr(usage, "prompt_tokens", 0) or 0)
            out = int(getattr(usage, "completion_tokens", 0) or 0)
            self.input_tokens += inp
            self.output_tokens += out
            # DeepSeek 原生 prompt_cache_hit_tokens；litellm 通常归一化为
            # usage.prompt_tokens_details.cached_tokens，两个都读，取其一。
            details = getattr(usage, "prompt_tokens_details", None)
            cached = getattr(details, "cached_tokens", None) if details is not None else None
            if cached is None:
                cached = getattr(usage, "prompt_cache_hit_tokens", None)
            if cached is not None:
                self.cache_hit += int(cached)
                self.have_split = True
            # cache_miss = input_tokens - cache_hit 在打印时推导（DeepSeek 上二者之和即 prompt_tokens）

    logger = UsageLogger()
    litellm.success_callback = [logger]
    try:
        litellm.suppress_debug_info = True
    except Exception:
        pass
    return logger


# --------------------------------------------------------------- agent 运行 ---

def extract_target(name, arguments):
    """从工具调用参数里挑简短目标用于展示（path 取 basename）。arguments 可能是 dict 或 JSON 字符串。"""
    path = None
    if isinstance(arguments, dict):
        path = arguments.get("path")
    else:
        s = str(arguments).strip()
        try:
            path = json.loads(s).get("path")
        except ValueError:
            m = re.search(r'"path"\s*:\s*"((?:[^"\\]|\\.)*)"', s)
            path = m.group(1) if m else None
    return os.path.basename(str(path)) if path else ""


def run_agent(model_cls, agent_cls, tool, log_level, err_cls, cfg, api_key, system_prompt, task):
    """装配模型与代理，流式执行任务，实时编号展示工具调用。

    返回 (steps, model_calls, final_answer, outcome, model_id)。
    """
    model_kwargs = dict(
        model_id=cfg["model_id"],
        api_key=api_key,
        api_base=cfg["api_base"],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )
    if not cfg["thinking"]:
        # 关闭 DeepSeek V4 thinking：thinking 模式不接受 tool_choice（smolagents 默认 required）。
        # litellm 会把 extra_body 合并进 OpenAI 兼容请求体（llm_http_handler.py:236/278）。
        model_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    model = model_cls(**model_kwargs)
    agent_kwargs = dict(
        tools=make_tools(tool),
        model=model,
        add_base_tools=False,
        max_steps=cfg["max_steps"],
    )
    if log_level is not None:
        agent_kwargs["verbosity_level"] = log_level.OFF
    agent = agent_cls(**agent_kwargs)
    # 1.26.0 中 system_prompt 为只读属性，需直接覆写模板（PromptTemplates 是 TypedDict/dict）
    agent.prompt_templates["system_prompt"] = system_prompt

    AgentError, AgentMaxStepsError, ModelLimitHitError = err_cls
    steps = []
    model_calls = 0
    final_answer = ""
    outcome = "completed"
    try:
        for step in agent.run(task, stream=True, reset=True):
            # 最终答案步骤：1.26 字段为 output（旧版为 final_answer），两者都读
            fa = getattr(step, "output", None)
            if fa is None:
                fa = getattr(step, "final_answer", None)
            if fa is not None:
                final_answer = str(fa)
                continue
            tool_calls = getattr(step, "tool_calls", None)
            if tool_calls:
                for call in tool_calls:
                    name = getattr(call, "name", "") or ""
                    if name == "final_answer":  # 内置 final_answer 工具不展示
                        continue
                    target = extract_target(name, getattr(call, "arguments", None))
                    steps.append((name, target))
                    print(f"   · {len(steps)}) {name} {target}", flush=True)
            if getattr(step, "token_usage", None) is not None:
                model_calls += 1
            if getattr(step, "error", None):
                print(f"   ! {getattr(step, 'error')}", flush=True)
    except Exception as e:
        if AgentMaxStepsError is not None and isinstance(e, AgentMaxStepsError):
            outcome = "max_steps"
            print("   ! 达到最大步数，返回部分结果（后续仍按实际落盘文件收尾）", flush=True)
        elif ModelLimitHitError is not None and isinstance(e, ModelLimitHitError):
            outcome = "model_limit"
            print("   ! 模型输出长度/上下文上限触发", flush=True)
        else:
            outcome = "error"
            print(f"   ! 代理异常: {e}", flush=True)
    # 部分版本最终答案只在运行后暴露
    if not final_answer:
        final_answer = str(getattr(getattr(agent, "state", None), "final_answer", "") or "")
    return steps, model_calls, final_answer, outcome, cfg["model_id"]


def print_summary(steps, model_calls, final_answer):
    """打印执行摘要框：工具调用次数与序列、模型调用次数、最终答案。"""
    line = "── smolagents 执行摘要 "
    line += "─" * max(2, 42 - len(line))
    print(line)
    if steps:
        seq = " → ".join(f"({i}){steps[i - 1][0]}" for i in range(1, len(steps) + 1))
        print(f"工具调用 {len(steps)} 次: {seq}")
    if model_calls:
        print(f"模型调用 {model_calls} 次")
    if final_answer:
        print(f"最终: {final_answer.strip()}")
    print("─" * 46)


def print_metrics(usage, elapsed, model, outcome):
    """打印 token/缓存命中率/耗时/成本 摘要行。"""
    total_in = usage.input_tokens
    out = usage.output_tokens
    hit = usage.cache_hit
    miss = total_in - hit
    if usage.have_split and total_in:
        hit_rate = f"{hit / total_in * 100:.1f}%"
        line = (f"   · 输入 {total_in:,}（缓存命中 {hit:,} / 新 {miss:,}，命中率 {hit_rate}）"
                f" · 输出 {out:,} · 耗时 {elapsed:.1f}s")
    else:
        line = (f"   · 输入 {total_in:,}（缓存命中 n/a / 新 n/a，命中率 n/a）"
                f" · 输出 {out:,} · 耗时 {elapsed:.1f}s")
    if total_in:
        cost, _ = compute_cost(hit, miss, out)
        line += f" · 成本 ¥{cost:.4f}"
    line += f" · {model}"
    if outcome:
        line += f" · outcome {outcome}"
    print(line)


# ------------------------------------------------------------------- 模式 ---

def dry_run_check(rel, src):
    """--dry-run：零 token 校验。不调用模型、不写任何文件。"""
    print("== 模拟运行（--dry-run，零 token：不调用模型、不改文件、不推 git）==")
    if not os.path.isfile(src):
        sys.exit(f"错误: 草稿不存在 -> {rel}")
    print(f"[1] 草稿: {rel}（{os.path.getsize(src)} 字节）")
    try:
        import smolagents
        import litellm
    except ImportError as e:
        sys.exit(f"错误: 缺少依赖，请先安装:\n"
                 f"  .\\.venv\\Scripts\\python.exe -m pip install \"smolagents[litellm]==1.26.0\"\n({e})")
    def _ver(name):
        try:
            return importlib.metadata.version(name)
        except Exception:
            return "?"
    print(f"[2] 依赖: smolagents {_ver('smolagents')} · litellm {_ver('litellm')}")
    key, key_src = resolve_api_key(allow_write=False)
    print(f"[3] API key: 已获取（来源: {key_src}）")
    cfg = model_config()
    print(f"[4] 模型: {cfg['model_id']} · api_base={cfg['api_base']} · "
          f"temperature={cfg['temperature']} · max_tokens={cfg['max_tokens']} · max_steps={cfg['max_steps']} · "
          f"thinking={'on' if cfg['thinking'] else 'off'}")
    system_prompt, task = build_parts(rel)
    if PLACEHOLDER_DRAFT in task or PLACEHOLDER_DATE in task:
        sys.exit("错误: 任务中仍残留占位符（build_parts 异常）")
    print(f"[5] 任务: system_prompt {len(system_prompt.encode('utf-8'))} 字节（固定缓存前缀）· "
          f"task 共 {len(task)} 字符 · 占位符已替换")
    print("    system_prompt 开头:", system_prompt.splitlines()[0][:60], "…")
    print("    任务参数块:")
    for ln in task.splitlines():
        print("      " + ln)
    _, agent_cls, tool, log_level, err_cls = _import_smolagents()
    # 仅构造工具与代理，验证 schema/docstring 无错（不联网）
    tools = make_tools(tool)
    print(f"[6] 工具: {[t.name for t in tools]}")
    before = snapshot_posts()
    print(f"[7] _posts/ 现有文章: {len(before)} 篇")
    name = git(["config", "user.name"], check=False).stdout.strip()
    email = git(["config", "user.email"], check=False).stdout.strip()
    print(f"[8] git 身份: {name or '(未设置，发布时自动补配)'} <{email or '?'}>")
    remote = git(["remote", "get-url", "origin"], check=False).stdout.strip()
    print(f"[9] git 远端: {remote or '(无)'}")
    print("== 校验通过。去掉 --dry-run 执行真实发布 ==")
    sys.exit(0)


def dry_run_agent(rel):
    """--dry-run-agent：完整模拟（消耗 token）。在临时副本里跑真实 smolagents + git
    push 到本地 bare origin，真实仓库与远端零改动。"""
    resolve_api_key(allow_write=True)  # 确保仓库 .env 存在，副本随之携带
    tmp_root = tempfile.mkdtemp(prefix="rx-sim-")
    work = os.path.join(tmp_root, "work")
    remote = os.path.join(tmp_root, "remote.git")
    try:
        # 忽略清单不包含 .env：副本必须携带仓库 .env 供子进程读取 key
        ignore = shutil.ignore_patterns(
            ".git", ".venv", ".reasonix", ".claude", "node_modules",
            "_site", ".jekyll-cache", "__pycache__", "us.stackdump", "*.pyc")
        shutil.copytree(ROOT, work, ignore=ignore)
        if not os.path.isfile(os.path.join(work, rel)):
            sys.exit(f"错误: 临时副本中找不到草稿 -> {rel}")
        subprocess.run(["git", "init", "-b", "master", work], check=True, capture_output=True)
        subprocess.run(["git", "init", "--bare", remote], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=work,
                       check=True, capture_output=True)
        print(f"== 模拟运行（--dry-run-agent）于临时副本: {work}")
        print("== 会真实调用模型（消耗 token），但只在副本内写文件并推送到本地 origin ==")
        r = subprocess.run(
            [sys.executable, os.path.join(work, "scripts", "blog-publish-smol.py"),
             rel, "--force"],
            cwd=work, encoding="utf-8", errors="replace")
        orig = snapshot_posts()
        work_posts = {f for f in os.listdir(os.path.join(work, "_posts"))
                      if f.endswith(".md")}
        added = sorted(work_posts - orig)
        loc = subprocess.run(["git", "rev-parse", "master"], cwd=work,
                             capture_output=True, text=True).stdout.strip()
        rem = subprocess.run(["git", "rev-parse", "master"], cwd=remote,
                             capture_output=True, text=True).stdout.strip()
        print("==")
        print(f"模拟结果: 新增文章 {added if added else '(无)'} · 子进程退出码 {r.returncode}")
        print(f"模拟推送: 本地 {loc[:8] or '(无)'} · 本地origin {rem[:8] or '(无)'} · 同步={bool(loc) and loc == rem}")
        print("== 模拟结束：真实仓库与远端未被修改 ==")
        return r.returncode or 0
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# -------------------------------------------------------------------- main ---

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # 抑制 litellm/httpx 响应序列化时的 Pydantic 噪音警告
    warnings.filterwarnings("ignore", message=r"Pydantic serializer warnings", category=UserWarning)
    os.chdir(ROOT)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    dry_run = "--dry-run" in sys.argv[1:]
    dry_agent = "--dry-run-agent" in sys.argv[1:]
    if len(args) != 1 or (dry_run and dry_agent):
        print("用法: python blog-publish-smol.py <草稿路径> [--force] [--dry-run | --dry-run-agent]")
        print("例:   python blog-publish-smol.py _drafts/3")
        print("      --dry-run       零 token 流程校验（不调用模型、不改文件）")
        print("      --dry-run-agent 临时副本完整模拟（消耗 token，不触碰真实仓库/远端）")
        sys.exit(2)

    rel = normalize_rel(args[0])
    src = os.path.join(ROOT, rel)
    if not os.path.isfile(src):
        sys.exit(f"错误: 草稿不存在 -> {rel}")

    if dry_run:
        dry_run_check(rel, src)
    if dry_agent:
        sys.exit(dry_run_agent(rel))

    if not force:
        try:
            input(f"将发布草稿：{rel}\n按回车继续，Ctrl+C 取消... ")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            sys.exit(130)

    model_cls, agent_cls, tool, log_level, err_cls = _import_smolagents()
    usage = make_usage_logger()

    # ---- 步骤 1/4：前置校验与构建任务 ----
    print("[1/4] 校验草稿与构建任务")
    print(f"   · 草稿: {rel}（{os.path.getsize(src)} 字节）")
    ensure_git_identity()
    before = snapshot_posts()
    print(f"   · _posts/ 现有文章: {len(before)} 篇")
    system_prompt, task = build_parts(rel)
    key, key_src = resolve_api_key(allow_write=True)
    print(f"   · API key 来源: {key_src}")
    cfg = model_config()
    print(f"   · 模型: {cfg['model_id']} · api_base={cfg['api_base']}")

    # ---- 步骤 2/4：调用 smolagents 代理 ----
    print("[2/4] 调用 smolagents 优化内容（git/删稿由本脚本完成）")
    t0 = time.monotonic()
    steps, model_calls, final_answer, outcome, model_id = run_agent(
        model_cls, agent_cls, tool, log_level, err_cls, cfg, key, system_prompt, task)
    elapsed = time.monotonic() - t0

    # ---- 执行摘要 + token 反馈 ----
    print_summary(steps, model_calls, final_answer)
    print_metrics(usage, elapsed, model_id, outcome)

    # ---- 步骤 3/4：确定性收尾（只看实际落盘的新文章，不依赖代理报告） ----
    new = find_new_posts(before)
    if len(new) != 1:
        print(f"错误: 未能唯一识别新文章（新增 {len(new)} 个: {new}）")
        sys.exit(1)
    post = new[0]
    post_path = os.path.join(POSTS_DIR, post)
    print("[3/4] 确定性收尾（frontmatter / 日期 / 删稿）")
    if fix_frontmatter(post_path):
        print(f"   · [修复] frontmatter title/subtitle 含未转义双引号，已改写为合法 YAML: {post}")
    post_path = ensure_date(post_path, today_str())
    post = os.path.basename(post_path)

    # 代理不删除草稿（模板已移除该步骤）；统一由本脚本删除（_drafts/ 已被 gitignore，不影响 git）
    if os.path.isfile(src):
        os.remove(src)
        print(f"   · 已删除草稿: {rel}")

    # ---- 步骤 4/4：git 提交并推送 ----
    print("[4/4] git 提交并推送")
    title = read_title(post_path) or post
    sha = publish_git(post, title)

    print()
    print(f"✓ 已发布 _posts/{post} · {sha}")
    if outcome != "completed":
        print(f"注意: 代理 outcome={outcome}（内容已写入并完成 git 发布，可忽略）")
    sys.exit(0)


if __name__ == "__main__":
    main()
