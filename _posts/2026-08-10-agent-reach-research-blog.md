---
layout: post
title: "我用 Agent Reach 生成了 Claude Code 年度生态报告：一篇实战演练"
subtitle: "15个平台，0成本，一份终端指令生成万字深度调研报告"
date: 2026-08-10
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Claude Code
  - Agent Reach
  - 工具
  - AI
---

最近我需要调研 Claude Code 过去一年的生态发展，涉及 MCP、Skills、Agent Teams、Plugins 等多个维度。传统做法是：手动打开 Google → 搜索 → 打开几十个网页 → 复制粘贴 → 整理。这次我换了一个新方式——**让 Agent Reach 替我做这件事**。

结果？**一次对话，30 个数据源，一篇万字报告**。这篇文章记录了整个实战过程。

---

## 什么是 Agent Reach？

Agent Reach 是一个开源的 CLI 脚手架，专门解决 "AI Agent 没有互联网" 的问题。它的核心思路很简单：

> 不发明新协议，而是教会 Agent 使用已有的成熟 CLI 工具。

它的 `SKILL.md` 文件告诉 Claude Code："当你遇到任务类型 X，就用命令 Y"。15 个平台覆盖了搜索、社交、开发、视频、网页、职场六大领域。

**安装：**

```bash
pip install agent-reach
agent-reach install
```

安装后跑一下体检，看看哪些通道可用：

```bash
agent-reach doctor --json
```

---

## 实战：生成 Claude Code 年度生态报告

### 第一步：体检

```bash
$ agent-reach doctor --json
```

输出告诉我当前可用的通道：

| 通道 | 状态 | 后端 |
|------|------|------|
| **Exa 搜索** | ✅ | mcporter |
| **GitHub (gh CLI)** | ✅ | 已认证 |
| **YouTube** | ✅ | yt-dlp |
| **Jina Reader** | ✅ | curl r.jina.ai |
| RSS | ✅ | feedparser |
| Twitter | ❌ | 未安装 twitter-cli |
| Reddit | ❌ | 未安装 |
| 小红书 | ❌ | 未安装 |

不用慌——Reddit 和 Twitter 不可用不代表做不了调研。**核心三件套（Exa + GitHub + Jina）都在线**，足够完成任务。

### 第二步：并行搜索

Agent Reach 的最大优势是**多平台并行**。以下命令几乎同时发出：

#### GitHub 搜索（gh CLI）

```bash
# 搜索 Claude Code 生态仓库
gh search repos "claude-code" --sort stars --limit 15 \
  --json name,fullName,url,stargazersCount,description,updatedAt

# 搜索 MCP 相关仓库
gh search repos "claude-code-mcp" --sort stars --limit 15 \
  --json name,fullName,url,stargazersCount,description,updatedAt
```

返回了 anthropics/claude-code（140K stars）、ECC（237K stars）、garrytan/gstack（126K stars）等关键仓库及其精确的 star 数。

#### Exa 语义搜索（mcporter）

```bash
mcporter call 'exa.web_search_exa(query: "Claude Code CLI ecosystem development 2025 2026 MCP skills agents", numResults: 10)'

mcporter call 'exa.web_search_exa(query: "Claude Code MCP server protocol ecosystem growth 2025 2026", numResults: 10)'
```

Exa 擅长英文技术内容，搜索质量远超通用搜索引擎。返回了高质量的技术文章——Arize 的 MCP vs Skills 评测、Anthropic 官方的 MCP 2026-07-28 规范博客、Towards AI 的扩展机制深度解析等。

#### 文章抓取（Jina Reader）

拿到搜索结果后，用 Jina Reader 批量抓取全文：

```bash
curl -s "https://r.jina.ai/https://pub.towardsai.net/claude-code-extensions-explained" | head -300
curl -s "https://r.jina.ai/https://arize.com/blog/mcp-vs-cli-skills-for-agents" | head -300
curl -s "https://r.jina.ai/https://www.tembo.io/blog/claude-code-multi-agent-orchestration" | head -200
```

Jina Reader 把网页转成干净的 Markdown，去掉了导航栏、广告、侧边栏等噪声。Agent 可以直接消费结构化内容，不需要处理 DOM。

#### 补充搜索（内置 WebSearch）

Agent Reach 覆盖 15 个平台，但 Claude Code 的内置 WebSearch 也可以做补充：

```
WebSearch: "Claude Code skills market growth statistics 2026"
WebSearch: "Claude Code vs Cursor vs Codex CLI market share enterprise adoption 2026"
WebSearch: "MCP protocol 400 million monthly downloads stateless 2026 Linux Foundation"
```

### 第三步：数据汇总

30 多个搜索结果回来后，关键步骤是**结构化汇总**。我让 Claude Code 做以下工作：

1. 将 GitHub star 数据按主题分组（MCP 项目、Skills 项目、插件项目）
2. 将文章信息按时间线整理（MCP 各版本发布时间、Skills 增速数据）
3. 交叉验证关键数字（例如 MCP 月下载量在不同来源中是否一致）
4. 识别数据缺口，针对性补搜

### 第四步：输出报告

最终输出为结构化 Markdown 报告，包含：

- 📊 总体概览（6 个关键指标一表呈现）
- 🕐 六大扩展机制时间线
- 📈 MCP / Skills / Agent Reach / Agent Teams / Plugins 五大维度深析
- 🏆 市场竞争格局（Copilot vs Claude Code vs Cursor vs Codex）
- 🔮 9 个发展趋势

全部数据标注了来源链接。

---

## 为什么用 Agent Reach 而不是纯 WebSearch？

| 维度 | 纯 WebSearch | WebSearch + Agent Reach |
|------|-------------|------------------------|
| GitHub 仓库数据 | 搜不到 star 数、更新时间 | `gh search` 精确字段查询 |
| 英文技术文章 | 质量参差不齐 | Exa 语义搜索，技术内容精准 |
| 长文抓取 | 摘要丢失细节 | Jina Reader 完整 Markdown 转换 |
| 多平台并行 | 串行搜索 | Exa + gh + Jina 同时发出 |
| 数据验证 | 单一来源 | 多平台交叉验证 |

**核心差异**：WebSearch 返回的是搜索引擎的摘要索引，Agent Reach 走的是各平台的原生 API/CLI——更精确、更结构化、更适合 Agent 消费。

---

## Agent Reach 的通道选择策略

实践中总结出三条原则：

### 1. 先体检，后选通道

```bash
agent-reach doctor --json
```

不要假设通道可用。比如这次 Twitter 和 Reddit 不可用，但 Exa + Jina 的组合已经覆盖了大部分英文技术内容源。

### 2. 核心三件套优先

- **Exa** → 英文技术文章、代码搜索
- **gh CLI** → GitHub 仓库、Issue、PR、Release
- **Jina Reader** → 全文抓取、RSS

这三个通道覆盖了 80% 的程序员调研场景。

### 3. 社交平台按需启用

- 涉及中文社区讨论 → 配小红书、B站
- 涉及国际社区舆论 → 配 Twitter、Reddit
- 涉及职业调研 → 配 LinkedIn

---

## 技巧总结

### ✅ 好的做法

1. **并行发出搜索请求**——不要等一个搜索结果回来再搜下一个
2. **用精确字段**——`gh search` 用 `--json` 指定字段，避免返回噪音
3. **全文抓取用 Jina**——比自己解析 HTML 靠谱一百倍
4. **交叉验证数字**——同一指标在 GitHub、博客、官方文档中可能不同
5. **数据缺口即时补搜**——汇总阶段发现空白，马上追搜

### ❌ 避免的坑

1. **不要手动浏览网页收集数据**——让 Agent 用 Jina Reader 抓取
2. **不要依赖单一平台**——同一主题在 Exa、gh、WebSearch 中互补
3. **不要跳过 doctor**——通道状态可能在安装后变化

---

## 效果：一次对话 vs 传统方案

| 环节 | 传统做法 | Agent Reach |
|------|---------|-------------|
| 搜索阶段 | 手动 30+ 次 Google 搜索，约 2 小时 | 并行 6 次搜索，约 1 分钟 |
| 阅读阶段 | 打开 20+ 个标签页逐一阅读，约 3 小时 | Jina Reader 批量转 Markdown 后 Agent 自动提取 |
| 数据整理 | 手动复制粘贴到 Excel/笔记，约 2 小时 | Agent 自动汇总分类 |
| 撰写阶段 | 从笔记写报告，约 3 小时 | Agent 一次输出结构化报告 |
| **总计** | **约 10 小时** | **约 15 分钟**（含人工审核） |

---

## 下一步：用 Agent Reach 做什么？

Agent Reach 不止能做技术调研。你可以：

- **竞品分析**：GitHub 搜竞品仓库 + Exa 搜评测博客 + Reddit 看用户吐槽
- **面试准备**：LinkedIn 搜目标公司员工 + GitHub 看开源贡献 + Exa 搜面经
- **热点追踪**：RSS 订阅行业博客 + Twitter 看讨论 + B站看中文解读
- **学术调研**：Exa 搜论文 + Jina 抓全文 + gh 找复现代码

---

## 结语

Agent Reach 解决了一个基础但一直被忽视的问题：**AI Agent 需要一个像人类一样使用互联网的能力**。它不发明新协议、不收取 API 费用、不依赖单一平台——只是把开发者已经在用的 CLI 工具组织成 Agent 可以理解的手册。

配合 Claude Code 的并行搜索和结构化汇总能力，一份 10 小时工作量级别的深度调研报告可以在 15 分钟内完成。

**开源地址**：[github.com/Panniantong/agent-reach](https://github.com/Panniantong/agent-reach)

---

> **本文实验环境**：Claude Code v2.1.204 + Agent Reach v1.5.0，Windows 10，PowerShell 7。
>
> 文中的调研报告输出见同目录 `Claude_Code_Ecosystem_Report_2026.md`。
