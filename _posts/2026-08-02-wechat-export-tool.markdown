---
layout: post
title: "微信聊天记录导出工具 v3.0 开源了！支持 6 种格式一键导出"
subtitle: "一个人 + AI 工具开发的实践产物"
date: 2026-08-02
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - 开源
  - 工具
  - Python
  - 微信
---

## 写在前面

你是否有过这样的需求：

- 想把微信聊天记录**备份**下来，但官方只能导出到"文件传输助手"，格式还不可控？
- 想对聊天记录做**数据分析**（比如统计和某人的聊天频率、关键词）？
- 换了工作/手机，想把自己和重要客户的聊天记录**归档留底**？
- 法律纠纷时想导出聊天记录作为**证据材料**？

我一直在找一款"开箱即用"的微信导出工具，但市面上的方案要么需要手动提取数据库密钥、要么依赖各种命令行操作、要么年久失修不支持新版微信。

于是我自己写了一个，今天开源给大家。

**项目地址：** <https://github.com/minglin2012/Wechat-Export>

**Star 一下不迷路 ⭐**

---

## 一、它能做什么？

一句话：**一键导出微信聊天记录，支持 6 种格式。**

| 格式 | 说明 | 适用场景 |
|------|------|---------|
| HTML | 浏览器直接查看，带聊天气泡样式 | 日常阅读、分享 |
| CSV | Excel 可打开 | 数据分析 |
| XLSX | 原生 Excel 格式 | 报表、归档 |
| PDF | 固定排版 | 打印、法律证据 |
| TXT | 纯文本 | 轻量备份 |
| JSON | 结构化数据 | 程序二次处理 |

### 核心特性

- ✅ **图形界面**（GUI），普通用户也能上手
- ✅ 按会话**预览过滤**（白名单/黑名单/关键词）
- ✅ 可选跳过群聊、公众号
- ✅ 支持**导出图片消息**
- ✅ 自动检测微信数据目录
- ✅ 支持命令行模式（适合批量/自动化）
- ✅ 已测试支持 **微信 4.1.1.54（Windows）**

---

## 二、快速开始

### 图形界面（推荐新手）

```bash
python gui.py
```

### 命令行（推荐进阶用户）

```bash
# 1. 获取数据库密钥
python export.py key

# 2. 预览会话列表
python export.py list --data-dir=<微信数据目录>

# 3. 导出全部聊天记录为 Excel
python export.py export -f xlsx --images
```

### 高级过滤（export_config.json）

```json
{
  "blacklist": {
    "names": ["微信团队"],
    "keywords": ["通知", "广告"],
    "skip_groups": true,
    "skip_official": true
  },
  "whitelist": {
    "keywords": ["张三"]
  }
}
```

> 白名单非空时，**只导出**白名单中的会话。

---

## 三、技术架构：一个不得不说的"三层设计"

写这个工具时，我遇到了一个很有意思的技术挑战，这也是我最想和大家分享的部分。

微信的聊天记录存在一个加密数据库（WCDB）里，要读取它需要跨越**三个技术层次**：

```
┌─────────────────────────────────────────────┐
│         Python 编排层（用户界面）               │
│   export.py / gui.py / image_decoder.py      │
├─────────────────────────────────────────────┤
│      Node.js / Electron 桥接层               │
│   get_key.js → 注入微信进程捕获密钥             │
│   wcdb_server.js → HTTP 服务查询数据库        │
│   koffi (FFI) → 调用 C/C++ DLL               │
├─────────────────────────────────────────────┤
│        Windows 原生层（C/C++ DLL）            │
│   wx_key.dll → Hook 微信 SetDBKey 调用        │
│   WCDB.dll → 加密数据库引擎                   │
└─────────────────────────────────────────────┘
```

### 为什么要三层？一个"顽固"的错误码

一开始我想用 Python 的 `ctypes` 直接调用 WCDB 的 C 接口——**结果失败了**。

WCDB 库内部会检查宿主进程环境，在 Python 进程里调用 `wcdb_init()` 始终返回 `INIT_FAIL`（错误码 -1006）。

试了裸 Node.js 也不行。

**最终发现：WCDB 只接受 Electron 的 Chromium 沙箱环境。**

于是有了这个三层架构：

1. **Windows 原生层（C/C++ DLL）**：`wx_key.dll` 注入微信进程，Hook 内存中的 `SetDBKey` 调用，捕获数据库密钥；`WCDB.dll` 是微信自带的加密数据库引擎
2. **Node.js / Electron 桥接层**：用 `koffi`（FFI 库）让 JS 调用 C/C++ 函数；`wcdb_server.js` 启动本地 HTTP 服务供 Python 查询
3. **Python 编排层**：负责用户交互、流程控制、图片解码、多格式输出

> 这个"环境兼容性"问题是最耗时的一关。如果你也遇到过"库能加载但初始化失败"，很可能就是宿主进程环境不对——多试试不同的运行时。

---

## 四、构建与发布

### 本地打包

```bash
pip install pyinstaller openpyxl fpdf2
python setup_deps.py   # 自动下载 Electron/Node.js/ffmpeg
python build.py        # 打包为 exe
```

### GitHub Actions 自动构建

我配置了 CI 流水线，推送 tag 即可自动构建并发布 Release：

```bash
git tag v3.0.0
git push --tags
```

输出在 `dist/WeChatExport/`，双击 `启动.bat` 即可运行。

---

## 五、使用截图

| 获取密钥 | 选择会话 | 导出记录 |
|---------|---------|---------|
| ![](https://cdn.junjun.tech/20260802082156.png) | ![](https://cdn.junjun.tech/20260802082217.png) | ![](https://cdn.junjun.tech/20260802082426.png) |

---

## 六、Roadmap / 未来计划

- [ ] 支持微信 Mac 版本
- [ ] 支持导出语音消息转文字
- [ ] 更丰富的聊天数据分析（词云、聊天频率图）
- [ ] 一键导出全部为 PDF 报告

欢迎提 Issue / PR 一起完善！

---

## 七、写在最后

这个项目是我"一个人 + AI 工具"开发的实践产物。整个过程踩了很多坑，最大的感受是：

> **很多"不可能"其实只是没找对技术路径。** WCDB 只认 Electron 环境，那我就搭一个 Electron 桥接层——方案总比困难多。

如果你觉得这个工具有用，欢迎：

- ⭐ **Star** 支持一下
- 🐛 提 **Issue** 反馈问题
- 💬 在 **Discussion** 里交流想法

**项目地址：** <https://github.com/minglin2012/Wechat-Export>

---

*技术交流欢迎留言，看到都会回。*
