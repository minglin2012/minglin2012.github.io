---
layout: post
title: "AI Agent 开发范式深度解析：从 Function Call 到 MCP，从 ReAct 到 LLM Wiki"
subtitle: "一份学习笔记：Covering Tool Use、ReAct、RAG、LLM Wiki、MCP 协议等核心概念及它们之间的层级关系"
date: 2026-08-11
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - AI
  - Agent
  - MCP
  - Claude Code
---

## 1. 从一个问题开始：Claude Code CLI 能粘贴图片吗？

答案是**能**，但有平台差异：

| 平台 | 快捷键 |
|------|--------|
| Windows | **Alt + V**（Ctrl+V 是粘贴文本） |
| macOS | Cmd + V |
| Linux | Ctrl + V |

粘贴成功后会在输入框显示 `[Image #N]` 占位符。

但真正的问题是：**我的客户端用的是 DeepSeek 模型，它没有原生视觉能力**，粘贴的图片只会显示 `[Unsupported Image]`。于是引出了接下来的问题——如何让没有视觉能力的模型"看见"图片？

答案就是：**Skill 编排 + Function Call 执行**。

---

## 2. Skill 和 Function Call，不是一回事

这是很多初学者容易混淆的概念。用一个类比来说明：

```
Skill（技能）        ≈  菜谱（什么时候用、怎么组合）
Function Call（工具） ≈  刀、锅、火（真正执行动作的）
```

### 2.1 Function Call = 原子能力

Claude Code 内置了 40+ 个 function call，从底层到高层都有：

| 层级 | 示例 |
|------|------|
| 系统级 | `Bash`、`PowerShell`、`Read`、`Write` |
| 网络级 | `WebSearch`、`WebFetch` |
| 浏览器级 | `browser_navigate`、`browser_click`、`browser_snapshot` |
| 任务级 | `TaskCreate`、`TaskUpdate` |

### 2.2 Skill = 编排指令

SKILL.md 是一份**说明书**，告诉 AI：

- **何时**触发（触发词/场景）
- **用什么工具**来完成任务
- **按什么步骤**组合这些工具

以 `set-alarm` 技能为例，它的目录结构：

```
~/.claude/skills/set-alarm/
├── SKILL.md              ← 说明书（Markdown）
└── scripts/
    └── alarm_gui.py      ← 实际工具（Python 脚本）
```

SKILL.md 自己不会设闹钟，但它编排了 `Bash`（跑 Python 脚本）和 `CronCreate`（设置后备提醒）两个 function call。

### 2.3 一个完整的例子：Vision Skill

为了让我能在 DeepSeek 下"看图"，我经历了完整的搭建过程：

**第一版（架构错误）：**

```
C:\Users\user\
├── CLAUDE.md          ← 放错位置
├── claude-vision-skill/ ← 技能和工具混在一起
│   ├── vision.js
│   ├── .env
│   └── node_modules/
```

**最终版（标准 Skill 模式）：**

```
~/.claude/skills/vision/
├── SKILL.md              ← 说明书：告诉 AI 何时调用 vision.js
└── scripts/
    ├── vision.js         ← 实际工具：调千问 VL API
    └── .env              ← API Key 配置
```

`vision.js` 核心逻辑出奇地简单——就是读取图片 → base64 → 发 HTTP 请求 → 返回文字描述：

```javascript
// 识图脚本核心：图片 → base64 → OpenAI 兼容 API → 文字描述
const data = fs.readFileSync(imagePath);
const imageUrl = `data:image/${ext};base64,${data.toString("base64")}`;

const result = await request({
  model: "qwen3.5-omni-plus",
  messages: [{
    role: "user",
    content: [
      { type: "image_url", image_url: { url: imageUrl } },
      { type: "text", text: "用中文描述这张图片" }
    ]
  }],
});
```

**三层架构清晰可见：**

```
┌─────────────────────────────────┐
│  SKILL.md（编排层）              │  ← "遇到图片 → 调 vision.js"
├─────────────────────────────────┤
│  Function Call（执行层）          │  ← PowerShell 执行 node vision.js
├─────────────────────────────────┤
│  外部 API（底层）                 │  ← 千问 VL 模型
└─────────────────────────────────┘
```

---

## 3. Tool Calling 到底是谁的能力？

**它是 LLM 和运行框架的协作结果，不是单独某一方的能力。**

```
┌──────────────────────────────────────────┐
│  LLM 的能力（决策引擎）                    │
│  训练时会输出结构化 JSON，而不是纯文本      │
│  {"tool": "bash", "args": {"cmd": "ls"}} │
│  它知道"该调用什么、传什么参数"             │
│  但它 **不能真正执行**                     │
└──────────────────┬───────────────────────┘
                   │ 输出的 JSON
                   ▼
┌──────────────────────────────────────────┐
│  框架/运行时（执行引擎）                   │
│  收到 LLM 的工具调用请求 → 真正去执行       │
│  → 把结果喂回给 LLM → LLM 继续推理        │
└──────────────────────────────────────────┘
```

核心就是那个 **think-act-observe 循环**：

```python
while True:
    output = llm.generate(messages, tools)   # LLM 决策
    if output is text: break                  # 结束
    if output is tool_call:                   # LLM 要调工具
        result = execute_tool(output)          # 框架执行
        messages.append(result)                # 结果喂回去
```

不管是 Claude Code、LangChain、还是你自己写的 agent_orchestrator，底层都是这个循环。差别只在于**工具的丰富程度**和**工程化水平**。

### 顺便说一句：Function Call 和 Prompt 调用是两回事

| | Function Call | Prompt 调用 |
|---|---|---|
| 输出格式 | `{"tool": "x", "args": {}}` | "请帮我调用 X 功能查 Y" |
| 精度 | 高，严格匹配 Schema | 低，需额外解析自然语言 |
| 依赖 | 需要模型训练过 tool calling | 任何模型都能用 |
| 趋势 | 主流 | 逐渐被替代 |

---

## 4. Memory 完全跟 LLM 无关

LLM 本身只有**注意力**（context window），没有**记忆力**。

Claude Code 的 memory 是这样工作的：

```
用户让 Claude 记住某事
        │
        ▼
写文件到磁盘 →  ~/.claude/projects/<项目>/memory/某事实.md
        │
        ▼
下次启动 → 读取 MEMORY.md → 筛选相关记忆 → 注入 system prompt
        │
        ▼
LLM 看到 system reminder 里的"背景知识"，像"事先就知道"一样
```

其实，**无论是记忆、CLAUDE.md、还是 Skill 说明书，最终都映射到 API 的两个字段**：

```
POST https://api.anthropic.com/v1/messages
{
  "system": "CLAUDE.md 的内容     ← 都在这里
             Skill 说明书          ← 都在这里
             相关 memory           ← 都在这里
             系统指令",            ← 都在这里
  "messages": [
    {"role": "user", "content": "当前问题"},
    ...
  ]
}
```

从 LLM 的视角看，这一切就是一串 token 流。`system` vs `messages` 的区别只是协议层面的。

---

## 5. 当前 Agent 开发的九大范式

### 5.1 ReAct（Reasoning + Acting）⭐ 基础中的基础

```
思考 → 行动 → 观察 → 思考 → 行动 → 观察 → ...
```

最基础的闭环。90% 的 Agent 都是这个模式或其变体。

### 5.2 Plan-then-Execute（先规划再执行）

```
目标 → 分解为步骤 → 用户审批 → 逐个执行
```

Claude Code 的 `/plan` 模式就是这个。

### 5.3 Router / Intent Classifier（路由分发）

```
           ┌→ 代码专家 Agent
用户输入 → Router ─┼→ 数据分析 Agent
           └→ 客服 Agent
```

### 5.4 Multi-Agent / Swarm（多智能体协作）

```
┌─ 研究员 Agent（搜索资料）
├─ 写手 Agent（撰写初稿）        ┌→ 综合 Agent
├─ 审校 Agent（检查事实）────────┤   整合输出
└─ 设计师 Agent（配图排版）
```

Claude Code 的 Workflow（`parallel()`, `pipeline()`）就是做这件事的基础设施。

### 5.5 RAG（检索增强生成）

```
用户问题 → 向量检索 → 相关文档 → 拼入 prompt → LLM 生成
```

把"查资料"和"生成回答"解耦。

### 5.6 LLM Wiki（Karpathy 范式）⭐ 与 RAG 互补

Karpathy 提出了一个与 RAG 截然不同的思路：

```
RAG：每次查询临时检索 → 用完即抛 → 无积累
LLM Wiki：提前消化 → 写入 wiki → 知识持续增长
```

核心比喻：**"Obsidian 是 IDE，LLM 是程序员，Wiki 是代码库"**。

架构分三层：

```
1. Raw sources  — 不可变的原始文档（论文、文章）
2. Wiki         — LLM 生成并维护的 markdown 知识库
3. Schema       — 配置文件，定义结构和规范
```

三种核心操作：

- **Ingest**：投喂新来源，LLM 自动更新 10+ 个相关页面
- **Query**：查 wiki，出带引用的回答，好回答可以反写回 wiki
- **Lint**：周期性健康检查——矛盾检测、过时信息、死链接

最精辟的洞见：**"人类放弃 Wiki 是因为维护负担比价值增长得快，LLM 不会烦。"**

### 5.7 Reflection / Self-Correction（反思自纠正）

```
生成 → 自我审查 → 发现问题 → 修正 → 最终输出
```

### 5.8 Tool Use / Function Calling（工具调用）

最底层的构建块，几乎所有范式都依赖它。

### 5.9 Human-in-the-Loop（人机协作）

关键节点需人类审批。Claude Code 的 Allow/Deny 弹窗就是最直接的例子。

---

## 6. 一张图总结所有范式的关系

```
┌──────────────────────────────────────────────────┐
│  编排层    Plan-then-Execute    Multi-Agent       │
│            Router               Reflection        │
├──────────────────────────────────────────────────┤
│  积累层    LLM Wiki              Memory / RAG      │
├──────────────────────────────────────────────────┤
│  增强层    Human-in-the-Loop                       │
├──────────────────────────────────────────────────┤
│  基础层    ReAct（think-act-observe 循环）          │
├──────────────────────────────────────────────────┤
│  原子层    Tool Use / Function Calling             │
├──────────────────────────────────────────────────┤
│  协议层    MCP（Model Context Protocol）           │
└──────────────────────────────────────────────────┘
```

---

## 7. MCP 带来了什么？

**MCP 让 Function Call 从"自己写"变成了"拿来就用"。**

```
没有 MCP：                    有了 MCP：
每个工具自己实现、测试、维护     市场上几千个现成的 MCP Server
Postgres → 自己写 SQL 连接     npm install → 直接用
GitHub → 自己调 REST API      一行配置 → 直接用
文件系统 → 自己写 fs 操作      社区维护 → 直接用
```

类比：

```
Function Call / Skill   =   自己写菜谱 + 自己做菜
MCP                     =   外卖平台
    
    你不需要会做菜，点就行了。
    餐厅负责做，你负责吃。
```

**MCP 和 Function Call 不冲突。** MCP Server 最终暴露给你用的，还是一个个 function call。差别只是——你不用写了，也不用自己的环境去跑。

---

## 8. 这些范式能成为"设计模式"吗？

**还在路上，但几块基石已经成型。**

```
GoF 设计模式（1994）：████████████████████  100%
Agent 范式（现在）：   ████████░░░░░░░░░░░░  ~40%

类比：
1970s — OOP 诞生          2022  — ReAct 论文
1994 — GoF 统一术语       2025+ — MCP/A2A 协议出现
2000s — 进入教科书          ?    — 真正的"Agent 设计模式"
```

| 范式 | 成熟度 | 判断 |
|------|--------|------|
| Tool Use / Function Call | ⭐⭐⭐⭐⭐ | 已是事实标准，JSON Schema 格式统一 |
| ReAct | ⭐⭐⭐⭐ | 论文引用破万，但实现方式各异 |
| RAG | ⭐⭐⭐⭐ | 概念统一，具体架构千差万别 |
| LLM Wiki | ⭐⭐ | 思路很好，工程化还很早期 |
| Multi-Agent | ⭐⭐⭐ | 各家互不兼容 |
| MCP | ⭐⭐⭐ | 协议已发布，生态正在形成 |

---

## 9. 写在最后

折腾一圈的收获：

1. **Skill = 编排，Function Call = 执行。** 分清这两层就不会搞混架构。
2. **LLM 只管决策，不管执行。** 所有"Agent 能力"都是框架层面的。
3. **知识积累（LLM Wiki）比知识检索（RAG）更接近真正的"记忆"。** Karpathy 的洞见很有启发。
4. **MCP 不是新范式，是标准化。** 它让工具从"各写各的"变成"写一次到处用"。
5. **这些范式还不是 GoF，但 Tool Use + ReAct + RAG 三个基石已经接近不可逆了。**

---

> 本文配套实践：在 Windows 10 + Claude Code（DeepSeek）上搭建了完整的 vision skill，通过千问 qwen3.5-omni-plus 实现了非视觉模型的"看图"能力。相关代码见 `~/.claude/skills/vision/`。
