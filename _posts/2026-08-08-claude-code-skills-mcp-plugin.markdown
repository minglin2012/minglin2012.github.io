---
layout: post
title: "深入理解 Claude Code 的 Skills、MCP 与 Plugin：它们到底有什么区别？"
subtitle: "从 Playwright 插件源码出发，搞清楚三种扩展机制的运行方式、进程模型与适用场景"
date: 2026-08-08
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Claude Code
  - MCP
  - Skill
  - 工具
---

## 引言

在使用 Claude Code 的过程中，我安装了一个 Playwright 插件用于浏览器自动化操作。但随之而来一系列疑问：这个"插件"到底装了什么？它是 Skill、MCP Server 还是 Plugin？它们之间有什么区别？`.claude/` 目录下哪些地方可以放自定义脚本？

本文记录了我的完整探索过程。

---

## 一、从一个 Playwright 安装说起

我在 Claude Code 的 `settings.json` 中加了一行配置：

```json
{
  "enabledPlugins": {
    "playwright@claude-plugins-official": true
  }
}
```

重启后，我的工具列表多了 24 个浏览器工具：`browser_navigate`、`browser_click`、`browser_snapshot` 等。那么问题来了——这些工具是怎么来的？

### 1.1 从插件到 MCP Server

安装的插件文件位于：

```
C:\Users\<用户名>\.claude\plugins\cache\claude-plugins-official\playwright\
```

关键文件是 `.mcp.json`：

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
```

所以这个"插件"本质上就是一个**配置封装**——它告诉 Claude Code：启动时通过 `npx` 拉起 `@playwright/mcp` 这个 MCP Server。

### 1.2 真正干活的代码在哪里？

MCP Server 的实际代码在 npx 的缓存目录：

```
%LOCALAPPDATA%\npm-cache\_npx\9833c18b2d85bc59\node_modules\@playwright\mcp\
├── package.json    → @playwright/mcp v0.0.78，由 Microsoft 维护
├── cli.js          → 入口：调用 playwright-core 的 MCP 工具注册函数
└── index.js        → 导出 createConnection

依赖：
├── playwright      → v1.62.0-alpha    ← 真正的浏览器控制引擎
└── playwright-core → v1.62.0-alpha    ← MCP 协议实现
```

调用路径如下：

```
Claude Code
  └─ 启动时 spawn npx @playwright/mcp（常驻进程，PID 41664）
       └─ node cli.js
            └─ 加载 playwright-core
                 └─ 启动 Chromium 浏览器实例
                      └─ 等待 JSON-RPC 指令
```

我在终端验证了这一点——电脑上确实有 4 个 node 进程在跑，其中 2 个是 `npx` 壳进程，2 个是 `cli.js` MCP Server（一个是旧实例，一个是当前活跃实例）。

---

## 二、Skill、MCP、Plugin 的三角关系

通过 Playwright 和另一个开源项目 [claude-vision-skill](https://github.com/asuojun/claude-vision-skill) 的对比，我搞清了三种模式的区别。

### 2.1 三种模式对比表

| 维度 | Skill | MCP Server | Plugin |
|------|-------|------------|--------|
| **本质** | 注入到 Claude 的 prompt 指令 | 独立运行的常驻进程 | Skill + MCP + Hook 的打包 |
| **有进程吗** | 无 | 有（node 常驻进程） | 取决于内含什么 |
| **通信方式** | 纯文本，写在 prompt 里 | stdin/stdout JSON-RPC | 组合上述两种 |
| **安装方式** | 放 `.claude/skills/<name>/SKILL.md` | 放 `.mcp.json` 或 `settings.json` | `/plugin install` 自动下载 |
| **何时用** | 告诉 Claude 怎么想/怎么做 | 需要运行时代码（浏览器、数据库、API） | 一个功能需要多部分配合 |

### 2.2 案例分析：claude-vision-skill

这个开源项目的文件结构非常简单：

```
claude-vision-skill/
├── CLAUDE.md      ← 告诉 Claude："遇到图片不要用 Read，调 node vision.js"
└── vision.js      ← 一个独立脚本，调千问 VL API 识图
```

`vision.js` 不是常驻进程，被 `node vision.js xxx.jpg` 一次性调用就退出。所以它天然适合用 **Skill** 方式接入。

接入方法：把 `CLAUDE.md` 改名为 `SKILL.md`，顶部加上 YAML frontmatter：

```markdown
---
name: vision
description: 让无识图能力的模型通过调用千问 VL API 实现识图
---

# 识图能力

你的底层模型不具备原生识图能力。遇到图片时，**不要用 Read 工具**，
改用 vision.js：`node vision.js "<图片路径>" "用中文描述这张图片"`
```

然后放入 `.claude/skills/vision/SKILL.md`，`vision.js` 放入同目录 `scripts/` 下。

### 2.3 决策流程

当你拿到一个开源仓库，按下面的线索判断：

```
看仓库里有什么文件
  │
  ├── 只有 .md / prompt 文件？
  │     → Skill，不需要二进制，放 .claude/skills/
  │
  ├── 有 package.json + bin 入口（如 cli.js）？
  │     → MCP Server，npx 启动，配置在 .mcp.json
  │
  └── 同时有 .mcp.json + plugin.json + skill 提示词？
        → Plugin，走 /plugin install
```

---

## 三、`.claude/` 目录的标准结构

经过查证，**官方推荐**的 `.claude/` 目录结构如下：

```
项目根目录/
├── CLAUDE.md                    ← 项目说明（自动加载）
├── .mcp.json                    ← MCP Server 定义
├── .claude/
│   ├── settings.json            ← 项目级配置
│   ├── settings.local.json      ← 本地配置（不提交 git）
│   ├── commands/                ← 自定义斜杠命令（/xxx）
│   │   └── deploy.md
│   ├── agents/                  ← 子智能体定义
│   │   └── code-reviewer.md
│   ├── skills/                  ← 技能
│   │   └── vision/
│   │       ├── SKILL.md         ← 技能说明
│   │       └── scripts/         ← 技能引用的脚本 ✅
│   │           └── vision.js
│   └── rules/                   ← 条件规则（glob 匹配加载）
│       └── frontend.md
```

**关键结论：**

1. **Skill 的 `scripts/` 目录可以放源码**——这是设计意图，不是滥用
2. **普通项目脚本不要放 `.claude/` 下**——它们是通用工具，属于项目 `scripts/` 目录
3. **没有 `.claude/tools/` 这个目录**——这是我之前猜的，经查证并不存在

---

## 四、附加思考：npm vs npx vs pipx

在探讨二进制管理方式时，还延伸出了关于包管理的对比。

### 4.1 npm 的隔离方式

```
npm install（局部）              npm install -g（全局）
───────────────              ─────────────────
node_modules/                 全局 node_modules/
  ├── package-a/              所有包混在一起
  ├── package-b/              升级冲突是常态
  └── package-c/
        └── node_modules/      ← 冲突时嵌套解决
              └── dep@2.0/
```

Node 生态不太需要 "pipx 等价物"，因为 `npm install` 默认局部隔离，且有嵌套解决冲突的能力。

### 4.2 Python 为什么需要 pipx

```python
# pip 的 site-packages 是**纯扁平**的
site-packages/
├── package_a/
├── package_b/
├── dep_x/         ← 只有一个版本！A 和 C 冲突即炸
└── dep_y/
```

所以 Python 需要 pipx/venv 做物理隔离。

### 4.3 快速对照

| 场景 | Node | Python |
|------|------|--------|
| 局部隔离 | `npm install`（天生） | `venv` + `pip install` |
| 全局隔离 | 不太需要 | `pipx install` ✅ |
| 即用即走 | `npx`（缓存 14 天） | `pipx run` |
| 依赖冲突处理 | 嵌套 node_modules | 不支持，靠 venv 物理分隔 |

---

## 五、总结

1. **Skill** = 注入 prompt 的文字指令，可附带脚本在 `scripts/` 目录
2. **MCP Server** = 常驻后台进程，通过 JSON-RPC 与 Claude Code 通信
3. **Plugin** = Skill + MCP + Hook 的打包，一键安装
4. 区分三者的最快方法：看仓库里有没有 `package.json` + bin 入口
5. `.claude/skills/` 是放自定义 Skill 和脚本的正确位置
6. Python 工具用 `pipx`，Node 工具用 `npx`/局部 `npm install`，各取所需

---

*本文基于 Claude Code + DeepSeek v4-pro 环境实测，所有进程状态、文件路径均为真实输出。*
