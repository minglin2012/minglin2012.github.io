---
layout: post
title: "Claude Code 最近一年生态发展调研报告"
subtitle: "覆盖 MCP、Skills、Agent Teams、Plugins、Agent Reach 五大维度，30+ 数据源"
date: 2026-08-05
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Claude Code
  - AI
  - MCP
  - Agent
---

> 调研周期：2025 年 8 月 — 2026 年 8 月
> 调研工具链：Agent Reach（Exa 搜索 + GitHub gh CLI + Jina Reader）+ 内置 WebSearch/WebFetch
> 数据来源：30+ 数据源，包括 GitHub、Claude 官方博客、Dev.to、Arize、Tembo、Skillselion、JetBrains 等

---

## 总体概览

Claude Code 在过去一年经历了从「终端聊天机器人」到「可扩展 AI 开发平台」的根本性转变。截至 2026 年 8 月：

| 指标 | 数据 |
|------|------|
| GitHub Stars | **140,000+** |
| 企业采用率 | **63%**（Black Duck 2026） |
| 周均 Agent PR | **622,000** |
| 占 GitHub 全部公开 PR 比例 | **13.9%** |
| 年化收入 | **$25 亿+** |
| 用户满意度 | **91% CSAT，NPS 54** |

---

## 一、六大扩展机制时间线

Claude Code 的扩展体系在过去一年逐层构建，形成了六个互补的扩展原语：

| 组件 | 发布时间 | 一句话定义 | 上下文成本 |
|------|---------|-----------|-----------|
| **MCP** | 2024.11 | 开放协议，将 Claude 接入数据库、API 和外部工具 | 可达 50k+ tokens；Tool Search 降低约 85% |
| **Subagents** | 2025.07 | 隔离的子任务执行器，拥有独立上下文窗口 | 隔离于主会话 |
| **Hooks** | 2025.09 | 事件驱动的确定性自动化（PreToolUse、PostToolUse、SessionStart 等） | 极低（Shell 级别执行） |
| **Skills** | 2025.10 | Markdown 文件定义的可复用工作流，支持 / 斜杠命令调用和自动触发 | 约 30-50 tokens（仅元数据） |
| **Plugins** | 2025.10 | Skills + MCP + Hooks + Subagents + Slash Commands 的打包安装单元 | 包含内容之和 |
| **Agent Teams** | 2026.02 | 多个独立 Claude Code 会话的并行协作，共享任务列表 | 每成员独立上下文窗口 |

### 心智模型

```
Skill   → 教会 Claude 「怎么做」
MCP     → 给 Claude 连接「外部世界」
Hook    → 让事情「自动发生」
Plugin  → 把以上打包为「可安装单元」
Team    → 让多个 Claude 「同时工作」
```

---

## 二、MCP 协议发展

### 2.1 数据指标

| 指标 | 数据 |
|------|------|
| 月 SDK 下载量（Python + TypeScript） | **9,700 万**（2026 年中），较 2024.11 发布时增长约 4,750% |
| 活跃公开 MCP 服务器 | **13,000+**（npm + GitHub），年增长率 400% |
| 官方参考仓库 Stars | **87,500+** |
| 官方一手集成 | **50+** |
| 企业生产环境采用率 | **41%** 的软件组织 |
| 社区 Awesome-MCP 列表 Stars | **89,000+** |

### 2.2 关键里程碑

#### 2025.12 — 治理移交 Linux Foundation

Anthropic 将 MCP 捐赠给 **Linux Foundation 下的 Agentic AI Foundation (AAIF)**，与 Block、OpenAI 共同创立。白金成员包括 **AWS、Google、Microsoft、Cloudflare、Bloomberg**。

**意义**：MCP 从单一厂商协议转变为厂商中立、社区治理的开放标准，通过正式的 **SEP（Spec Enhancement Proposal）** 流程推进。

#### 2026.07.28 — MCP 第五版规范（无状态核心）

这是 MCP 最具颠覆性的修订，核心变更：

| 变更 | 详情 |
|------|------|
| **无状态传输** | 从双向有状态协议转为请求/响应模型；消除粘性会话和共享会话存储 |
| **Serverless 兼容** | 任意请求可到达任意实例，支持水平扩展和标准负载均衡 |
| **路由标头** | `Mcp-Method`、`Mcp-Name`（SEP-2243），网关无需解析 JSON-RPC body 即可路由 |
| **可缓存工具列表** | `cacheScope` + `ttlMs`，W3C Trace Context 分布式追踪（SEP-414） |
| **12 个月废弃过渡期** | roots、sampling、logging → 迁移至 stderr/OpenTelemetry |
| **Tasks 独立扩展** | SEP-2663，采用轮询模型 |
| **授权加固** | 对齐生产级 OAuth 2.0 / OIDC，原生支持 Entra、Okta 等企业身份系统 |

#### 2026.04 — STDIO RCE 漏洞披露

影响官方 SDK 的 STDIO 远程代码执行漏洞类别被披露，推动 **Remote MCP + OAuth** 成为安全基础设施的一等关注点，催生了 MCP Gateway 品类（Kong AI Gateway 等）。

### 2.3 GitHub 热门 MCP 项目

| 项目 | Stars | 描述 |
|------|-------|------|
| `Context7 MCP` | 57,800+ | 库文档查询，Agent 的实时技术文档 |
| `Microsoft Playwright MCP` | 34,100+ | 浏览器自动化，最多星的厂商 MCP |
| `GitHub Official MCP` | 30,800+ | GitHub 操作官方 MCP 服务器 |
| `n8n-mcp` | 22,500+ | 用自然语言构建 n8n 工作流 |
| `Zilliz Claude Context` | 12,200+ | 代码库语义搜索，将整个代码库作为上下文 |
| `TalkToFigma MCP (Grab)` | 6,900+ | Agent 与 Figma 双向通信 |
| `NotebookLM MCP` | 3,100+ | NotebookLM 集成，引用支持的答案 |
| `jcodemunch-mcp` | 2,500+ | Tree-sitter AST 级别 GitHub 代码检索，省 313B+ tokens |

---

## 三、Skills 生态发展

### 3.1 数据指标

| 指标 | 数据 |
|------|------|
| Claude Code 专属 Skills（2026.07） | **约 4,200**，较 2026.01（约 2,100）增长 100% |
| 跨平台 Agent Skills 总计 | **65,933**（Skillselion 2026.07 索引） |
| 全部扩展（Skills + MCP + 插件 + 市场） | **87,803** 条记录 |
| 累计安装量 | **1.28 亿+** |
| 周安装量（Top 1,998 Skills） | **约 1,920 万** |
| 独立发布者 | **401** |
| Top 8 发布者产出占比 | **约 60%**（幂律分布显著） |

### 3.2 SKILL.md 成为跨工具标准

Anthropic 于 2025 年 10 月推出 Agent Skills，七个月内被以下全部主流编程 Agent 采纳——共识速度超过 MCP：

> Claude Code · OpenAI Codex CLI · Cursor · Gemini CLI · GitHub Copilot · Cline · Roo Code · Antigravity

**渐进式加载**是核心设计创新：

```
运行时上下文消耗：

  Skill 名称 + 描述 ................. 约 50 tokens  （始终在上下文）
  └─ 被触发时加载 SKILL.md ......... 约 500 tokens  （按需加载）
       └─ 引用文件/参考文档 ......... 2,000+ tokens  （显式触发才加载）
```

这使得数百个 Skill 可共存而不耗尽上下文窗口。

### 3.3 三类 Skill 主导生态

| 类型 | 描述 | 示例 |
|------|------|------|
| **基础 Skill** | 文档/表格/演示文稿操作，编码最佳实践 | `caveman`（省 65% tokens）、`ui-ux-pro-max-skill` |
| **合作伙伴 Skill** | 公司构建，让服务变得 Agent 可访问 | K-Dense、Browserbase、Notion、Vercel、Microsoft Azure |
| **企业 Skill** | 专有工作流，编码内部流程、合规和机构知识 | 内部合规审查、私有 API 集成 |

### 3.4 热门 Skills GitHub 仓库

| 项目 | Stars | 描述 |
|------|-------|------|
| `multica-ai/andrej-karpathy-skills` | 199,300 | 基于 Karpathy 对 LLM 编码缺陷观察的 Skill 集 |
| `nextlevelbuilder/ui-ux-pro-max-skill` | 113,200 | 专业 UI/UX 设计智能 |
| `Graphify-Labs/graphify` | 102,000 | 代码库 → 可查询知识图谱 |
| `JuliusBrussee/caveman` | 95,600 | "为什么用多 token 当少 token 行"——省 65% tokens |
| `addyosmani/agent-skills` | 81,500 | 生产级工程 Skills |
| `Egonex-AI/Understand-Anything` | 77,400 | 代码 → 交互式知识图谱 |
| `google-labs-code/stitch-skills` | 7,900 | Google 官方 Skills 库，兼容 Stitch MCP |

### 3.5 每周安装量 Top Skills

| Skill | 周安装量 | 类型 |
|-------|---------|------|
| `find-skills` | 753,732 | 元 Skill（发现其他 Skill） |
| `systematic-debugging` | 172,160 | 调试方法论 |
| `writing-plans` | 170,580 | 计划编写 |
| `using-superpowers` | 169,910 | Agent 编排框架 |
| `requesting-code-review` | 154,036 | 代码审查请求 |
| `subagent-driven-development` | 134,040 | 子 Agent 驱动开发 |
| `webapp-testing` | 109,599 | Web 应用测试 |

---

## 四、Agent Reach / 联网能力发展

### 4.1 三种方案对比

| 方案 | 类型 | 原理 | 成本 | 适用场景 |
|------|------|------|------|---------|
| **Agent Reach** | 开源 CLI 脚手架 | 封装 curl、yt-dlp、gh、twitter-cli 等成熟 CLI 工具 | 免费 | 快速 CLI 查社交/GitHub/RSS |
| **Web-Access Skill** | 浏览器 CDP 自动化 | 通过 Chrome DevTools Protocol 直接控制浏览器 | 免费（开源） | 复杂 Web 交互、SPA、登录墙后页面 |
| **Claude Code Web** | 官方内置 | 云环境四级网络访问控制 | 随订阅 | 云开发 + 网络安全管控 |

### 4.2 Agent Reach

**覆盖 15 个平台，六大领域：**

```
搜索:     Exa AI 搜索
社交:     小红书、Twitter/X、B站、V2EX、Reddit、Facebook、Instagram
职场:     LinkedIn
开发:     GitHub (gh CLI)
网页:     Jina Reader、RSS
视频:     YouTube、B站、小宇宙
```

**核心理念**：不发明新命令语法，而是通过 `SKILL.md` 教会 Agent「遇到任务类型 X 时使用命令 Y」。Agent 从手册文件学习，不依赖训练数据中的过时命令。

### 4.3 Web-Access Skill

- **三层通道调度**：WebSearch → WebFetch → curl → Jina → CDP Proxy（自动选择）
- **CDP Proxy**：直连本地 Chrome/Edge，继承浏览器登录态，无需 Cookie 管理
- **并行分治**：Tab 级隔离的子 Agent 进行多目标研究
- **站点经验库**：跨会话持久化每个域名的交互模式和坑点
- GitHub Stars: **约 1,700**（2026.04 开源即获得关注）

---

## 五、Agent Teams 与多 Agent 编排

### 5.1 四层编排体系

| 层级 | 通信方式 | Token 成本 | 最佳场景 |
|------|---------|-----------|---------|
| **Subagents** | 仅向主 Agent 汇报结果 | 最低 | 聚焦的子任务，只关心结果 |
| **Agent Teams** | 点对点消息 + 共享任务列表 | 最高（每成员独立上下文） | 需要多视角讨论和互相挑战的协作 |
| **Dynamic Workflows** | 脚本协调，支持 pipeline/parallel/phase | 中等 | 需要多次验证的大规模工作 |
| **外部编排器** | 平台管理（Slack/Linear/GitHub 触发） | 可变 | 跨仓库、跨团队的企业级协调 |

### 5.2 Agent Teams（实验性，2026.02 发布）

**启用方式**：
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

**核心特性**：

| 特性 | 描述 |
|------|------|
| 架构 | 一个 Lead + 多个 Teammate，共享任务列表和邮箱系统 |
| 显示模式 | 进程内模式（Shift+Down 切换队友）/ 分屏模式（tmux / iTerm2） |
| 自动依赖 | 任务列表自动执行依赖排序 |
| Team 级 Hooks | `TeammateIdle`、`TaskCreated`、`TaskCompleted` |
| 计划门控 | Teammate 可被要求先出计划（只读），Lead 批准后才执行 |

**推荐最佳实践**：3–5 个队友最均衡；每人操作不同文件（避免覆盖）；按模型分层（Opus → 编排者，Sonnet → 工作者，Haiku → 格式化）。

### 5.3 Dynamic Workflows

```javascript
// 示例：多阶段审查流水线
export const meta = {
  name: 'review-changes',
  phases: [{ title: 'Review' }, { title: 'Verify' }],
}

const DIMENSIONS = [
  { key: 'bugs', prompt: '...' },
  { key: 'perf', prompt: '...' },
]

const results = await pipeline(
  DIMENSIONS,
  d => agent(d.prompt, { phase: 'Review', schema: FINDINGS }),
  review => parallel(
    review.findings.map(f => () =>
      agent(`Adversarially verify: ${f.title}`, { phase: 'Verify', schema: VERDICT })
    )
  )
)
```

| 能力 | 上限 |
|------|------|
| 并发 Agent | 最多 16 个 |
| 单次运行总 Agent | 最多 1,000 个 |
| Pipeline 单次项目 | 最多 4,096 个 |
| 断点续跑 | 同会话内支持 |

### 5.4 成本参考

| 场景 | 会话数 | 日估算成本 | 月估算（20 天） |
|------|--------|-----------|---------------|
| 个人开发者 | 1 | 约 $13 | 约 $260 |
| 3 并行 Agent | 3 | 约 $30–40 | 约 $600–800 |
| 5–10 并行 Agent | 5–10 | 约 $50–130 | 约 $1,000–2,600 |
| 10 人团队 × 3 Agent | 30 | 约 $300–400 | 约 $6,000–8,000 |

---

## 六、Plugins 市场生态

### 6.1 数据规模

| 指标 | 数据 |
|------|------|
| 官方插件（2026.07.23） | **333** 个，覆盖 28 个分类 |
| 社区插件 | **471+**（TonsOfSkills.com） |
| 社区 Skills | **3,069+** |
| 社区 Agents | **347+** |
| Claude Code 专属插件 | 273 |
| Cowork 专属插件 | 128 |
| 双平台插件 | 68 |

### 6.2 关键插件分类

```
AI 开发与 Agent ........... Agent SDK Dev, AWS Agents, Pydantic AI, Hugging Face, NVIDIA
云基础设施 ................. AWS（6 个）, Azure, Cloudflare, Netlify, Vercel, Firebase, Hostinger
代码智能 (LSP) ............ TypeScript, Python, Rust, Go, Java, C/C++, C#, Kotlin, Lua, PHP, Swift
代码质量 ................... PR Review Toolkit, Security Guidance, OWASP 审计
浏览器自动化 ............... Playwright, Chrome DevTools, Browser Use
行业垂直 (Cowork) .......... 法律（12 个角色插件）, 医疗, 金融, 营销, CRM, HR
```

---

## 七、市场竞争格局

### 7.1 市场份额（2026 年中）

| 工具 | 工作采用率 | 周 Agent PR | 企业采用 | 年化收入 |
|------|-----------|------------|---------|---------|
| **GitHub Copilot** | 29%（停滞） | 17,000（下降） | 40%（5,000+ 人大企业强项） | — |
| **Claude Code** | 18%（6× 增长） | **622,000**（+37% over 4w） | **63%** | $25 亿+ |
| **Cursor** | 18%（放缓） | 49,000（+72% over 4w） | 50,000+ 客户（一半财富 500 强） | $20–40 亿 |
| **OpenAI Codex** | 3%（加速中） | 139,000（135K-155K 区间） | 早期 | — |

> Claude Code 一个工具的周 Agent PR **超过 Copilot + Codex + Cursor 的 Agent PR 总和**。

### 7.2 多工具组合最佳实践

2026 年高级团队的标配是 **同时使用 2–3 个工具**：

```
Cursor ........... 日常行内编辑 + Tab 补全
Claude Code ...... 深度重构 + 复杂多文件工作
Codex CLI ........ 廉价、自治的后台任务
```

---

## 八、生态关键发现与发展趋势

### 8.1 「磨刀」多于「砍柴」

86,047 个扩展中：

```
Agent 工具类（上下文/记忆/编排）..... 37,265（43%）
集成类（Agent 连接 API/服务）....... 12,165（14%）
后端开发 ...........................  6,786（8%）
前端开发 ...........................  5,070（6%）
安全与审查 .........................  2,386（3%）
App Store 优化 .....................    107
生成式引擎优化 .....................     71
```

**37,000 个扩展帮 Agent 写代码，仅 71 个帮产品触达用户。** 社区花在打磨 Agent 上的精力远超用 Agent 构建产品。

### 8.2 MCP vs Skills：定位已清晰

Arize 受控实验（2026.05，Claude Opus 4.6）的关键发现：

| 维度 | MCP | CLI Skills | 裸 Claude |
|------|-----|-----------|-----------|
| **正确率** | 0.834 | 0.833 / 0.826 | **0.845**（gh CLI 在训练数据中） |
| **复杂分析成本** | 6×（基准） | 1× | — |
| **工具遵循率** | 33%（67% 逃逸到 bash） | **99%+** | — |

**结论**：正确的问题是 **MCP + CLI，而非 MCP vs CLI**。

### 8.3 发现是最大瓶颈

`find-skills`（752,732 周安装）超过所有领域 Skill 排名第一。66,000 个 Skill 的记忆和发现是人类无法独立完成的任务。

### 8.4 企业治理模式固化

生产部署的标准配置：RBAC、审计日志、Allowed-tools 沙箱、OAuth 同意、MCP Gateway。

### 8.5 Token 经济学驱动架构选择

```
MCP Schema（12 个服务器）..................... 50,000+ tokens
Skill 渐进式加载（数百个 Skill 共存）........... 约 50 tokens（元数据）
CLI 组合管道（grep | sort | uniq）............. 内置于训练数据
```

**成本效率**正在推动渐进式加载和 CLI 优先架构的胜出。

---

## 九、总结：三大趋势

### 趋势 1：MCP 正在「去 Anthropic 化」

从实验协议到 Linux Foundation 治理的无状态行业标准。9,700 万月下载量、13,000+ 服务器、41% 企业采用率——MCP 已成为 Agent 连接外部世界的默认基础设施。

### 趋势 2：Skills 正在成为新的「npm」

65,933 个 Skills、1.28 亿安装量、跨 7+ 个 Agent 平台的 `SKILL.md` 标准。增速超过 MCP，但**发现和治理基础设施远未成熟**。

### 趋势 3：Agent Reach 代表第三条路

不发明新协议，而是教会 Agent 使用现有 CLI 工具。当 MCP 方案需要 6× 成本时，CLI 路线是更务实的选择。**两者互补，非替代。**

---

> **Sources**
>
> - [Claude Code Extensions Explained: Skills, MCP, Hooks, Subagents, Agent Teams & Plugins](https://pub.towardsai.net/claude-code-extensions-explained-skills-mcp-hooks-subagents-agent-teams-plugins-9294907e84ff) — Towards AI, 2026.03
> - [Bringing MCP 2026-07-28 to Claude](https://claude.com/blog/bringing-mcp-2026-07-28-to-claude) — Claude Blog, 2026.07
> - [MCP vs. CLI Skills for Agents: What Our Eval Found](https://arize.com/blog/mcp-vs-cli-skills-for-agents-what-our-eval-found-and-which-you-should-use/) — Arize, 2026.05
> - [We Indexed 86,000 Claude Code, Codex and Cursor Extensions](https://dev.to/skillselion/we-indexed-86000-claude-code-codex-and-cursor-extensions-heres-what-the-data-shows-about-the-553e) — Dev.to / Skillselion, 2026.07
> - [The State of AI Skills: Mid-2026](https://aiskill.market/blog/the-state-of-ai-skills-mid-2026) — AISkill.Market
> - [Claude Code Multi-Agent Orchestration: 2026 Guide](https://www.tembo.io/blog/claude-code-multi-agent-orchestration) — Tembo, 2026.06
> - [State of the Coding Agent Market, July 2026](https://amplifying.ai/research/state-of-coding-agents) — Amplifying.ai
> - [Agent Reach: The Free, Open-Source Scaffold That Finally Gives Your AI Agent Internet Access](https://www.xugj520.cn/en/archives/agent-reach-internet-access-tool.html) — Efficient Coder
> - [Claude Code Skills vs MCP: 2026 Selection Guide](https://skywork.ai/blog/claude-code-skills-vs-mcp-comparison/) — Skywork.ai
> - [Claude Code Agents In 2026](https://www.cloudzero.com/blog/claude-code-agents/) — CloudZero
> - [MCP 2026: From Anthropic Proposal to Industry Standard](https://dev.to/chunxiaoxx/mcp-2026-from-anthropic-proposal-to-industry-standard-1kfa) — Dev.to
