---
layout: post
title: "我写了一个「项目环境切换器」——点一下，整个开发环境自动打开"
subtitle: "告别每天反复开关 VSCode、终端、浏览器，一个 Python 工具搞定项目切换"
date: 2026-08-06
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Python
  - 工具
  - 效率
  - 开源
---

> 每天在 10 个项目之间来回切换，每次都要手动打开 VSCode、终端、浏览器、Obsidian……终于忍不了了，花了两天写了个工具。

---

## 痛点

我电脑里有 40 多个项目目录。典型的日常：

```
打开博客项目：
  → 双击 VSCode → 打开 D:/programming/blog
  → Win+R → wt -d D:/programming/blog → npm run dev
  → 浏览器 → localhost:3000
  → 浏览器 → CSDN 后台

切到 Obsidian 笔记：
  → 关掉 VSCode（提示保存）→ 关终端 → 关浏览器标签
  → 打开 Obsidian → 切换到 mysocial 库
  → 打开资源管理器 → D:/programming/mysocial

切回博客：
  → 重复上面所有步骤……
```

每天重复 N 次，烦死了。市面上找不到现成的工具——启动器只管启动不管关闭，虚拟桌面只能手工排列，AutoHotkey 脚本没有 GUI。

## 解决方案：工作台 (Workbench)

一个 Python 写的 Windows 桌面工具。把每个项目需要的所有软件打包成一个"项目环境"，点一下全部启动，再点另一个自动关闭旧的。

### 核心功能

**一键启动环境**：一个项目可以配置 VSCode + 终端 + 浏览器 + Obsidian + 任意 exe

```yaml
- name: "发博客"
  icon: "📝"
  environment:
    - app: "vscode"
      target: "D:/programming/blog"
    - app: "terminal"
      target: "D:/programming/blog"
      command: "npm run dev"
    - app: "browser"
      browser: "chrome"
      target: "http://localhost:3000"
```

**安全切换**：点"私人秘书" → 旧环境的所有窗口收到 WM_CLOSE（等同于点 ✕）→ VSCode 会提示你保存 → 然后自动打开 Obsidian。不丢失数据。

**进程追踪**：快照差分法获取启动的 PID，关闭时递归查找子进程 → WM_CLOSE → 验证退出。Doubao、Cherry Studio 等 Electron 应用通过窗口标题关键词匹配关闭。

**去重 + 历史**：VSCode 已打开同一文件夹？只聚焦不重复开。每次切换自动记历史，一键恢复上次会话。

**浏览器智能处理**：同项目同浏览器只启一个进程，多 URL 作为标签页。不隔离 Profile，保留 Gmail/GitHub 登录态。关闭时按窗口标题精确匹配，不误关用户其他标签。

**Web UI + 系统托盘**：FastAPI 后端 + 原生 JS 前端，暗色玻璃态主题，实时进程面板显示每个 PID 的名称、窗口标题和存活状态。关闭窗口后托盘常驻，右键菜单可快速切换。

## 技术实现

```text
前端  →  Vanilla HTML/CSS/JS，暗色主题，玻璃态卡片
后端  →  Python 3.10 + FastAPI + uvicorn
进程  →  psutil 快照差分 + win32gui 窗口枚举
关闭  →  WM_CLOSE（非阻塞）+ SendMessageTimeout（兜底）
浏览器 →  --new-window 合并进程 + hostname 标题匹配
打包  →  PyInstaller (onefile 19MB) + Inno Setup (安装包)
CI/CD →  GitHub Actions + winget
```

## 截图

**架构图**
![架构图](https://cdn.junjun.tech/7fdc5a3a-20fb-4c68-83eb-d7fef6af77dc.png)

**进程面板**
![进程面板](https://cdn.junjun.tech/20260806094146.png)

**多软件启动界面**
![多软件启动界面](https://cdn.junjun.tech/20260806085759.png)

## 安装

```powershell
# 源码运行
git clone https://github.com/minglin2012/workbench
cd workbench
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python server.py
# 浏览器打开 http://127.0.0.1:8765

# 或下载 Release 中的 Workbench-Setup-x.x.x.exe 一键安装
```

## 踩过的坑

**1. PyInstaller `console=False` 导致 `sys.stdout` 为 None**

uvicorn 的 `ColourizedFormatter` 内部调用 `sys.stdout.isatty()`，打包后直接崩溃。解决办法很简单——启动前判断并重定向：

```python
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
```

**2. Obsidian 的 URI 切换库**

`obsidian://open?vault=xxx` 中的 vault 参数不是文件夹名，是 `obsidian.json` 里的 hex ID。需要先读取配置文件拿到正确的 ID 才能切换。

**3. Chrome 主进程 PID = 所有窗口**

PID 追踪到 Chrome 主进程后，如果不加标题过滤，关闭时会关掉用户所有的 Chrome 窗口。必须对浏览器 PID 加标题关键词二次验证。

**4. Electron 应用的窗口属于子进程**

Doubao、Cherry Studio 这类 Electron 应用，`subprocess.Popen` 拿到的 PID 是主进程，实际窗口在子进程里。需要用 `psutil.Process(pid).children(recursive=True)` 展开子进程树再关窗。psutil 访问不到时，回退到纯窗口标题匹配。

**5. `localhost` DNS 2 秒延迟**

Windows 的 `localhost` 优先解析 IPv6 `::1` 再回退 IPv4 `127.0.0.1`，每次 HTTP 请求多 2 秒。全部改用 `127.0.0.1` 直接解决。

## 总结

这个工具解决了一个很具体的个人痛点。代码量不大——核心启动器 400 行，进程追踪 400 行，前端 400 行，加起来 2000 多行 Python + 400 行 JS。但踩过的坑不少：Windows 进程管理、窗口消息、浏览器多进程架构、打包兼容性……

如果你也有类似需求，欢迎试用和提 Issue：

**https://github.com/minglin2012/workbench**
