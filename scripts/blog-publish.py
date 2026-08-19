#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博客发布一次性脚本（基于 reasonix run）。

用法:
    python blog-publish.py <草稿路径> [--force]

    <草稿路径>  可传完整 _drafts/xxx 或仅文件名/子路径；文件必须存在。
    --force     跳过发布前的交互确认（用于脚本/定时场景）。

职责划分（本脚本 vs reasonix 代理）:
  - reasonix 代理（scripts/blog-publish.prompt.md）：只做内容——读草稿、优化正文、
    写 frontmatter、写入 _posts/、删除草稿。不做 git。
    git 移出代理后，reasonix 对 git push 的 todo/最终答案验证护栏不再触发
    （实测：代理内执行 git push 会导致 final-answer 被拒、任务报失败）。
  - 本脚本：确定性收尾——修复 frontmatter 的 YAML 引号问题（避免 Jekyll 构建失败）、
    精确 git add/commit/push。无论 reasonix 退出码如何，只要新文章已写入，
    就保证落库并推送到远端。

设计要点（对应需求）:
  1. 固定前缀提升缓存命中:
     任务提示词模板 scripts/blog-publish.prompt.md 除文末「任务参数」块外完全静态；
     该块含两个动态占位符 __DRAFT__（草稿路径）与 __DATE__（今天日期），
     task 作为整体前缀传给 reasonix，前缀跨运行、跨每日保持一致 → 命中 provider 的
     prompt cache。
  2. 低 token 消耗:
     模板为逐条精简指令；git 移出代理后无需 todo/complete_step/update_goal 的往返；
     --output-format text 精简输出；指令里要求模型不要浏览仓库其它文件。
  3. 本地 python 环境:
     调用者使用仓库根目录 venv 的 python 运行本脚本，脚本自身无第三方依赖（仅标准库）。
  4. token 反馈:
     reasonix run 带 --metrics，执行后打印输入 token/缓存命中率/耗时/成本。
  5. 日期确定性:
     __DATE__ 注入今天日期；执行后再用 ensure_date 兜底纠正 frontmatter date 与
     文件名前缀，避免模型猜错日期（实测出现过 2025-01-01）。

调用 reasonix 的健壮性:
  - 直接调用 node.exe + node_modules/reasonix/bin/reasonix.js（shell=False），
    绕开 Windows 的 .cmd shim。原因：cmd 批处理在 %* 透传参数时，会把含换行的
    参数截断到第一个换行——实测多行任务模板到达 reasonix 时只剩第一行，导致代理
    拿不到文末的草稿路径而阻塞。直接 node 调用经 CreateProcessW 传参，多行中文
    任务完整无损（实测校验通过）。
  - 输出统一按 UTF-8 解码（避免系统 gbk 解码中文报错）。
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FILE = os.path.join(ROOT, "scripts", "blog-publish.prompt.md")
POSTS_DIR = os.path.join(ROOT, "_posts")
# 两个动态参数都放在模板文末的「任务参数」块，保证前面全部静态 → 前缀缓存命中
PLACEHOLDER_DRAFT = "__DRAFT__"
PLACEHOLDER_DATE = "__DATE__"
GIT_NAME = "wangyajun"
GIT_EMAIL = "hust_wangyajun@163.com"


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


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


def find_reasonix():
    """定位 reasonix 的 node 入口 [node.exe, reasonix.js]。

    不用 cmd 的 .cmd shim（其 %* 会把含换行的任务截断到第一个换行），而是从 shim
    同目录解析出 node.exe 与 reasonix.js 直接调用，保证多行任务完整传递。
    """
    shim = shutil.which("reasonix.cmd") or shutil.which("reasonix")
    if not shim:
        sys.exit("错误: 未在 PATH 中找到 reasonix，请确认已安装并加入 PATH。")
    base = os.path.dirname(shim)
    node = os.path.join(base, "node.exe")
    if not os.path.isfile(node):
        node = shutil.which("node")
    js = os.path.join(base, "node_modules", "reasonix", "bin", "reasonix.js")
    if not node or not os.path.isfile(js):
        sys.exit(f"错误: 无法定位 node.exe 或 reasonix.js（base: {base}）。")
    return [node, js]


def build_task(rel_path):
    """读取固定前缀模板并替换文末两个动态占位符（草稿路径、今天日期），返回完整 task。"""
    if not os.path.isfile(PROMPT_FILE):
        sys.exit(f"错误: 找不到提示词模板 {PROMPT_FILE}")
    with open(PROMPT_FILE, encoding="utf-8") as f:
        body = f.read()
    for ph in (PLACEHOLDER_DRAFT, PLACEHOLDER_DATE):
        cnt = body.count(ph)
        if cnt != 1:
            sys.exit(f"错误: 模板中 {ph} 占位符数量为 {cnt}（应为 1）")
    # 两个动态值都在文末「任务参数」块；其前面的模板保持完全静态 → 前缀缓存命中
    return (body.replace(PLACEHOLDER_DRAFT, rel_path)
                .replace(PLACEHOLDER_DATE, today_str()))


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


def run_reasonix(task, root, rel, metrics_path):
    """以 reasonix run 执行一次性任务；低 token 参数，并输出 --metrics 供反馈。"""
    rx = find_reasonix()
    # 固定命令参数 + task 作为最后一个参数。直接 node 调用（shell=False），
    # 不经 cmd shim，确保多行中文任务完整传递。
    cmd = rx + ["run",
                "--permission-mode", "auto",
                "--output-format", "text",
                "--metrics", metrics_path,
                "--dir", root,
                task]
    print(f"==> 将调用 reasonix 优化并写入：{rel}")
    return subprocess.run(cmd, shell=False, encoding="utf-8", errors="replace")


def parse_metrics(path):
    """读取 reasonix --metrics 生成的 JSON，抽取 token/缓存/成本等摘要；失败返回 None。"""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    cny = usd = model = None
    quotes = d.get("cost_quotes") or []
    if quotes:
        q = quotes[0]
        model = q.get("modelRef")
        vals = q.get("valuations") or {}
        if "CNY" in vals:
            cny = vals["CNY"].get("money", {}).get("amount")
        if "USD" in vals:
            usd = vals["USD"].get("money", {}).get("amount")
    return {
        "prompt": d.get("prompt_tokens", 0),
        "completion": d.get("completion_tokens", 0),
        "hit": d.get("cache_hit_tokens", 0),
        "miss": d.get("cache_miss_tokens", 0),
        "cost_usd": d.get("cost"),
        "cny": cny,
        "usd": usd,
        "model": model,
        "duration_ms": d.get("duration_ms"),
        "outcome": d.get("outcome"),
    }


def print_metrics(s):
    """打印一行 token/缓存命中率/耗时/成本摘要。"""
    total_in = s["hit"] + s["miss"]
    hit_rate = f"{s['hit'] / total_in * 100:.1f}%" if total_in else "n/a"
    line = (f"[token] 输入 {s['prompt']}（缓存命中 {s['hit']} / 新 {s['miss']}，"
            f"命中率 {hit_rate}）· 输出 {s['completion']}"
            f" · 耗时 {s['duration_ms'] / 1000:.1f}s")
    if s["cny"] is not None:
        line += f" · 成本 ¥{float(s['cny']):.4f}"
    elif s["cost_usd"] is not None:
        line += f" · 成本 ${s['cost_usd']:.4f}"
    if s.get("model"):
        line += f" · {s['model']}"
    if s.get("outcome"):
        line += f" · outcome {s['outcome']}"
    print(line)


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
    """确定性兜底：确保 frontmatter 的 date 与文件名日期前缀均为 today；返回最终路径。

    模型可能猜错/沿用旧日期（实测出现过 2025-01-01）。文件名与 frontmatter 的 date
    是发布正确性的关键，这里做硬性纠正。
    """
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    if len(args) != 1:
        print("用法: python blog-publish.py <草稿路径> [--force]")
        print("例:   python blog-publish.py _drafts/10")
        sys.exit(2)

    rel = normalize_rel(args[0])
    src = os.path.join(ROOT, rel)
    if not os.path.isfile(src):
        sys.exit(f"错误: 草稿不存在 -> {rel}")

    if not force:
        try:
            input(f"将发布草稿：{rel}\n按回车继续，Ctrl+C 取消... ")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            sys.exit(130)

    ensure_git_identity()
    before = snapshot_posts()
    task = build_task(rel)
    metrics_path = os.path.join(tempfile.gettempdir(), f"rx-metrics-{int(time.time())}.json")
    result = run_reasonix(task, ROOT, rel, metrics_path)

    # ---- token/命中率/成本反馈 ----
    summ = parse_metrics(metrics_path)
    if summ:
        print_metrics(summ)
    else:
        print("[token] 未获取到 reasonix metrics（运行可能被中断）")
    try:
        os.remove(metrics_path)
    except OSError:
        pass

    # ---- 确定性收尾：不依赖 reasonix 退出码，只看实际产物 ----
    new = find_new_posts(before)
    if len(new) != 1:
        print(f"错误: 未能唯一识别新文章（新增 {len(new)} 个: {new}）")
        sys.exit(result.returncode or 1)

    post = new[0]
    post_path = os.path.join(POSTS_DIR, post)

    if fix_frontmatter(post_path):
        print(f"[修复] frontmatter 中 title/subtitle 含未转义双引号，已改写为合法 YAML: {post}")
    post_path = ensure_date(post_path, today_str())
    post = os.path.basename(post_path)

    # 模型第五步删除草稿；若未删，此处兜底补删（_drafts/ 已被 gitignore，不影响 git）
    if os.path.isfile(src):
        os.remove(src)
        print(f"[提示] 已补删草稿: {rel}")

    title = read_title(post_path) or post
    sha = publish_git(post, title)

    print(f"已发布 _posts/{post} · {sha}")
    if result.returncode != 0:
        print(f"注意: reasonix 退出码 {result.returncode}（内容已写入并完成 git 发布，可忽略）")
    sys.exit(0)


if __name__ == "__main__":
    main()
