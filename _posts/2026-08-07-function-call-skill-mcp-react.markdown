---
layout: post
title: "Function-Call / Skill / MCP-Server / ReAct 范式深度辨析"
subtitle: "面向 Agent 开发工程师，厘清四层容易混淆的概念，附带公司类比、完整调用链路与工程选型建议"
date: 2026-08-07
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - AI
  - Agent
  - MCP
  - LLM
---

## 前言

现在做Agent开发，几乎一定会碰到四个高频名词：`Function-Call`、`Skill`、`MCP-Server`、`ReAct`。
很多人会把它们放在同一维度对比，实际上它们分属完全不同层级：

- Function-Call：**模型输出工具调用的指令规范（工单制度）**
- Skill：**业务能力封装（内部员工/业务SOP手册）**
- MCP-Server：**独立进程的工具服务（外包团队）**
- ReAct：**Agent整体执行循环范式（思考-行动-观察循环）**

> 它们不是二选一，而是经常组合在一起工作。本文结合之前的公司类比，把边界、职责、协作链路讲清楚。

## 一、逐个概念拆解（附带公司类比）

### 1. Function-Call（Tool-Use）：派工单制度

**定位：模型侧输出工具调用指令的标准契约，不是干活实体，不执行任何IO、命令、数据库操作。**

- 大模型经过微调，原生具备输出结构化JSON工具调用的能力；
- 模型只输出：工具名称 + 参数；**真正执行全部交给宿主Agent程序**；
- 工具Schema由宿主传入API的`tools`参数，**不是模型权重内置**；
- 即使没有MCP、没有Skill，也可以独立使用Function-Call。

> 公司类比：**公司成立之初就定下来的标准化派工单制度**。老板（LLM）只填写工单：干什么、参数是什么；干活交给下面员工或者外包。制度本身不干活，所有执行者统一使用这套工单。

> 注意：Function-Call不等于工具，它只是"下达任务的格式"。同一个工单，既可以派给内部Skill，也可以派给MCP外包。

### 2. Skill：内部业务能力单元

**定位：宿主Agent内部的能力封装，运行在宿主环境，一次性执行，分为两种形态。**

1. **代码型Skill**：一段脚本/函数，宿主fork子进程或者内存直接执行；比如Dify自定义代码工具。
2. **Prompt型Skill（Claude Code Skill）：markdown SOP手册**，自身不做IO，负责编排流程，指挥底层原子工具完成复杂业务。

特点：
- 和宿主强绑定，新增Skill需要在Agent侧配置/安装；
- 生命周期跟随宿主；宿主重启，Skill全部重置；
- Skill可以编排多次Function-Call，既可以调用内置工具，也可以调用MCP提供的外包工具。

> 公司类比：**公司内部员工、内部业务SOP手册**。在公司内部办公，受公司管控，可以组合基础能力完成复杂业务。

### 3. MCP-Server（Model Context Protocol）：外包服务

**定位：独立常驻进程，提供工具能力；MCP是通信协议，MCP-Server是干活的服务端进程。**

- 独立进程，可以本机stdio子进程，也可以部署远端SSE/HTTP服务；
- 通过`tools/list`对外暴露工具Schema，宿主MCP-Client拿到schema，转换成Function-Call工具定义传给大模型；
- 宿主发出Function-Call工单 → MCP-Client翻译成MCP JSON-RPC → MCP-Server真正执行；
- 可以被多个Agent宿主同时调用，能力与Agent宿主解耦，可以独立迭代、独立重启。

> 公司类比：**外包团队**。不在公司内部办公，可以在别的机房，只认标准化RPC协议；公司通过对接专员(MCP-Client)下发工单，外包负责实际干活。

> 关键点区分：
> - MCP-Client：宿主内部组件，外包对接专员，协议翻译转发，不做业务；
> - MCP-Server：真正干活的外包进程。

### 4. ReAct范式（Reasoning + Acting）：Agent的运行循环框架

**定位：Agent的执行架构范式，`思考→行动→观察→再思考`循环，**不是工具，不是协议，不是模型内置能力，是一套提示词/程序循环模式。

> ReAct 不关心底层工具是Skill还是MCP，它只关心循环：
1. **Thought（思考）**：显式输出推理过程，分析现状，决定下一步干什么；
2. **Action（行动）**：发起工具调用（早期ReAct靠提示词输出文本格式Action；现代ReAct可以直接使用Function-Call输出结构化Action）；
3. **Observation（观察）**：接收工具返回结果；
4. 回到Thought，基于结果继续推理，循环直到任务完成。

> 公司类比：**公司的整体工作流程制度**。规定老板不能一步直接出答案，必须：先思考方案 → 下发工单给员工/外包干活 → 拿到结果再重新思考，循环直到业务完成。

> 重要历史：早期ReAct没有Function-Call，全部靠提示词输出文本格式Action；现代工程大量采用 **ReAct循环 + Function-Call结构化工单** 的组合模式。

## 二、完整调用链路示例（ReAct + Function-Call + Skill + MCP）

需求：帮我评审项目代码，读取本地文件，同时查询数据库获取业务配置。

```
用户：帮我评审项目代码并核对数据库业务配置

【ReAct循环开始】
Thought：我需要两步：读取源码文件，再查询数据库配置，然后做比对评审。
→ 输出Function-Call工单1：调用read_file（内置Skill内部员工）

宿主Agent拿到工单：交给内部Skill执行读取文件
Observation：文件源码内容返回

Thought：文件已经拿到，下一步需要查询数据库，数据库能力来自MCP-Server外包。
→ 输出Function-Call工单2：调用db_query工具

宿主Agent拿到工单：交给MCP-Client，翻译成MCP JSON-RPC请求，发给MCP-Server进程执行
Observation：数据库配置返回

Thought：两份信息齐全，可以输出评审报告。
→ 输出最终回答，ReAct循环结束
```

> 可见：
> - ReAct负责整体循环调度；
> - Function-Call是统一工单格式；
> - read_file由内部Skill完成；
> - db_query由MCP-Server外包完成。

## 三、横向对比总表

| 概念 | 层级 | 本质 | 生命周期 | 执行位置 | 类比 |
|---|---|---|---|---|---|
| Function-Call | 模型指令层 | 工具调用的结构化工单契约 | 单次请求，无状态 | 模型输出，不执行 | 派工单制度 |
| Skill | 宿主业务层 | 业务能力封装（代码/SOP手册） | 跟随宿主，一次性执行 | 宿主进程内 | 内部员工/SOP手册 |
| MCP-Server | 外部服务层 | 独立常驻工具服务进程 | 独立常驻，可跨宿主复用 | 独立进程（本机/远端服务器） | 外包团队 |
| ReAct | Agent架构范式 | 思考-行动-观察迭代循环 | 多轮循环直到任务结束 | Agent宿主控制循环 | 整体工作流程制度 |

## 四、容易踩坑的认知误区

1. ❌ MCP和Skill是竞争二选一
✅ 互补。MCP提供底层手脚（外部能力）；Skill编排业务流程，指挥手脚干活。

2. ❌ ReAct必须使用提示词文本输出Action
✅ 现代工程：ReAct循环可以直接使用Function-Call结构化输出Action，不再依赖文本解析，稳定性更高。

3. ❌ Function-Call会执行工具
✅ 不会。模型只输出请求，**全部执行逻辑在宿主侧**。

4. ❌ MCP是大模型原生能力
✅ MCP是宿主侧通信标准；大模型完全不知道MCP协议，只看到转换后的工具Schema。

5. ❌ ReAct是大模型内置能力
✅ ReAct是一套执行范式，依靠提示词+宿主循环逻辑；任何大模型都可以跑ReAct。

## 五、工程选型建议

1. **简单内部业务工具**：优先Skill，直接写代码/脚本，轻量快速。
2. **需要复用、跨Agent、独立部署的工具**：使用MCP-Server。
3. **工具调用下达方式**：优先Function-Call；弱模型才用纯提示词模拟工具调用。
4. **复杂多步骤任务**：采用ReAct范式做循环；简单单步任务可以不需要完整ReAct循环。

> 典型组合：
> - Claude Code：ReAct循环 + Function-Call + 内置Skill + MCP-Server
> - Dify：ReAct循环 + Function-Call + Skill（自定义工具） + MCP SSE接入

## 六、一句话总结

> **ReAct规定"怎么思考、怎么循环干活"；
> Function-Call规定"任务工单长什么样"；
> Skill代表公司内部员工；
> MCP-Server代表外包团队；
> 一套完整Agent，往往四者同时存在。**
