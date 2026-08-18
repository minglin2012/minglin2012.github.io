---
layout: post
title: "npx skills：AI Agent 技能包管理器完全指南"
subtitle: "让你的AI助手从"通用大模型"变身"领域专家""
date: 2026-08-20
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Claude Code
  - Skill
  - 工具
  - AI
---

## 前言

你是否遇到过这样的场景：每次想让AI帮你完成某个特定任务，都要反复输入一大段提示词？或者在项目之间切换时，AI总是"失忆"，记不住你们之前约定好的工作流程？

如果你有这些困扰，那么今天要介绍的 `npx skills` 正是你需要的工具。它让AI助手获得"专业技能"的方式变得前所未有的简单——就像给手机安装App一样，一键为AI装上"能力包"。

## 什么是 npx skills？

**npx skills** 是开源 Agent Skills 生态系统的包管理工具。简单来说，它是一个**AI助手的"技能商店"**，让你能够以标准化的方式为 Claude Code、Cursor、Codex 等 41+ 种主流 AI 助手安装、管理和更新技能。

### 什么是 Agent Skill？

Skill 是一种模块化的知识包，以 **SKILL.md** 文件形式存在，包含了某个特定领域的工作流程、最佳实践和参考指南。

打个比方：如果把 AI 助手比作一个刚毕业的医学生，那么 Skill 就是各个科室的专业培训资料。有了外科手术指南，AI 就能更好地辅助外科手术；有了影像诊断指南，AI 就能更准确地判读医学影像。

**与传统 Prompt 的核心区别**：

| | Prompt | Skill |
|---|---|---|
| **本质** | 一次性对话指令 | 持久化能力模块 |
| **复用性** | 每次需要重新输入 | 一次安装，永久生效 |
| **上下文占用** | 全量加载 | 渐进式按需加载 |
| **版本管理** | 无 | Git 可追踪 |

## 核心原理：渐进式加载

Skills 最聪明的设计在于采用了 **"渐进式披露"（Progressive Disclosure）** 架构，不会把所有技能信息一次塞进上下文。

### 三层加载机制

```
┌─────────────────────────────────────────────────────────────┐
│  L1：元数据层（~100 tokens/skill）                         │
│  → 启动时加载：仅扫描技能名称和简短描述                      │
│  → 作用：让 AI 知道"有什么技能可以用"                       │
├─────────────────────────────────────────────────────────────┤
│  L2：指令层（< 5000 tokens）                               │
│  → 任务匹配后加载：完整的 SKILL.md 正文                     │
│  → 作用：提供详细的执行步骤、约束和输出格式                  │
├─────────────────────────────────────────────────────────────┤
│  L3：资源层（按需加载）                                     │
│  → 执行时加载：脚本、模板、参考文档等                       │
│  → 作用：提供执行任务所需的附加资源                         │
└─────────────────────────────────────────────────────────────┘
```

这种设计带来的直接好处是：**安装 10 个技能，每次对话只消耗约 1000 tokens 的元数据，而不是把 10000+ tokens 的完整内容全部塞进上下文**。上下文占用减少了约 **90%**！

## 环境准备

### 前置要求

- **Node.js 18 或更高版本**
- npm、pnpm、yarn 或 bun 任一包管理器

### 验证安装

```bash
# 检查 Node.js 版本
node --version

# 确认 npx skills 可用（首次运行会自动下载）
npx skills --version
```

## 核心命令详解

### 1. 搜索技能：`npx skills find`

在官方技能库中搜索可用的技能：

```bash
# 交互式搜索（支持 fzf 风格）
npx skills find

# 关键词搜索
npx skills find react performance
npx skills find pr review
npx skills find changelog
```

`find` 命令会返回技能的元数据，包括名称、来源仓库和安装量等信息。

### 2. 安装技能：`npx skills add`

这是最核心的命令，支持多种安装源格式：

```bash
# GitHub 简写（最常用）
npx skills add vercel-labs/agent-skills

# 完整 GitHub URL
npx skills add https://github.com/vercel-labs/agent-skills

# 指定子目录
npx skills add https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines

# SSH 方式
npx skills add git@github.com:vercel-labs/agent-skills.git

# 本地路径
npx skills add ./my-local-skills
```

**常用参数**：

| 参数 | 说明 |
|------|------|
| `-s, --skill <name>` | 指定安装的技能名称（可指定多个） |
| `-a, --agent <agents>` | 指定目标 AI 助手 |
| `-g, --global` | 全局安装（用户级别），默认是项目级别 |
| `-l, --list` | 仅列出可用技能，不实际安装 |
| `--copy` | 使用复制而非符号链接安装 |
| `-y, --yes` | 跳过所有确认提示 |
| `--all` | 安装所有技能到所有 Agent |

**典型使用场景**：

```bash
# 只安装某个仓库中的特定技能
npx skills add vercel-labs/agent-skills -s frontend-design

# 只安装给特定 AI 助手
npx skills add vercel-labs/agent-skills -a claude-code -a cursor

# 全局安装，所有项目都能用
npx skills add vercel-labs/agent-skills -g

# 一键全选安装（最省事）
npx skills add vercel-labs/agent-skills --all -y
```

### 3. 查看已安装技能：`npx skills list`

```bash
# 列出所有已安装技能
npx skills list

# 列出全局安装的技能
npx skills list -g

# 列出特定助手的技能
npx skills list -a claude-code
```

### 4. 更新技能：`npx skills update`

```bash
# 检查是否有更新
npx skills check

# 更新所有技能
npx skills update

# 更新指定技能
npx skills update web-design-guidelines
```

### 5. 移除技能：`npx skills remove`

```bash
# 交互式移除
npx skills remove

# 移除指定技能
npx skills remove web-design-guidelines

# 全局移除
npx skills remove --global my-skill

# 移除所有技能
npx skills remove --all -y
```

### 6. 创建技能：`npx skills init`

```bash
# 在当前目录创建 SKILL.md 模板
npx skills init

# 在子目录创建新技能
npx skills init my-skill
```

## 安装位置

不同 AI 助手的技能安装路径各有不同，CLI 工具会自动识别并安装到正确位置：

| AI 助手 | 项目级路径 | 全局路径 |
|---------|-----------|----------|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` | `~/.cursor/skills/` |
| Codex | `.codex/skills/` | `~/.codex/skills/` |
| OpenCode | `.agents/skills/` | `~/.config/opencode/skills/` |
| GitHub Copilot | `.agents/skills/` | `~/.copilot/skills/` |
| Windsurf | `.windsurf/skills/` | `~/.windsurf/skills/` |

除了这些助手专属路径，CLI 还会将技能文件的源副本统一存储在 `~/.agents/skills/` 目录下，方便统一管理。

## 实战案例：安装并使用 ModLens 技能

ModLens 是一个图像分析 AI 技能包，支持通过 AI 模型分析图片内容。以下是完整安装流程：

### 第一步：安装技能包（说明书）

```bash
npx skills add liustack/modlens
```

这一步会在 `~/.agents/skills/modlens/` 目录下安装 SKILL.md 说明书和启动脚本。

### 第二步：安装工具本体

Skill 只是"操作手册"，要真正执行图像分析，还需要安装可执行程序：

```bash
# 方式一：全局安装（推荐，一劳永逸）
npm install -g @liustack/modlens

# 方式二：每次通过 npx 临时运行（无需安装）
npx @liustack/modlens doctor
```

### 第三步：诊断与使用

```bash
# 运行诊断，检查环境
~\.agents\skills\modlens\scripts\run.ps1 doctor
```

执行 `doctor` 诊断后，会显示以下关键信息：

```
selected path:  path    # 或 npx，表示当前使用的来源
pinned version: 3.20.0  # 技能包锁定的版本
modlens on PATH: D:\...\modlens.ps1 (version 3.21.1, compatible)
```

- `selected path: path` → 使用全局安装的 modlens
- `selected path: npx` → 使用 npx 临时下载运行

## Skill 与 MCP：别再混淆了

很多开发者容易把 Skill 和 MCP（Model Context Protocol）混为一谈，它们其实是两个不同层次的概念：

| | MCP | Skill |
|---|---|---|
| **核心作用** | 给模型接入外部能力 | 规范模型的做事方式 |
| **关注重点** | 数据、工具、系统接口 | 任务方法论、执行步骤 |
| **解决问题** | 模型去哪拿数据、能调哪些工具 | 这类事应该按什么流程做 |
| **本质定位** | 能力供给层 | 行为规范层 |

> **一句话总结**：MCP 解决的是"模型能用什么"，Skills 解决的是"模型该怎么用"。两者是协作关系，而非替代关系。

## 最佳实践

### 1. 选择高质量技能

安装前先查看技能的质量指标：
- **安装量 1K+**：说明经过充分验证
- **官方来源**：如 `vercel-labs`、`anthropics`、`microsoft`
- **GitHub Stars**：仓库 stars 越多越可靠

可以在 [skills.sh](https://skills.sh/) 查看技能排行榜。

### 2. 选择合适的安装范围

- **项目级别**（默认）：技能随项目提交，团队成员共享同一套配置
- **全局级别**（`-g`）：技能对所有项目生效，适合个人常用工具

### 3. 版本锁定的理解

技能包通过 `SKILL.md` 中的 `pinnedVersion` 锁定版本，确保 AI 助手的行为一致性。即使工具本体更新，技能包仍会按照锁定的版本工作，直到你显式更新。

## 总结

`npx skills` 正在改变我们与 AI 助手交互的方式。它将"临时起意的提示词"升级为"可积累的技能资产"，让 AI 从通用助手真正转变为领域专家。

**核心要点回顾**：

1. **Skill = 操作手册**：SKILL.md 文件，告诉 AI 如何完成特定任务
2. **工具本体 ≠ Skill**：Skill 只是说明书，具体执行还需要安装对应的 CLI 程序
3. **渐进式加载**：三层架构大幅节省上下文 token 消耗
4. **跨 Agent 兼容**：一套 Skill 可同时用于 Claude Code、Cursor、Codex 等多种 AI 助手

## 参考资源

- [Skills 官网](https://skills.sh/)
- [GitHub 仓库](https://github.com/antfu/skills-cli)
- [官方文档](https://mintlify.wiki/vercel-labs/skills/installation)
