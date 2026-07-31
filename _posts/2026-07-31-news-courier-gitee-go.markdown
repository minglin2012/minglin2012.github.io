---
layout: post
title: "白嫖 Gitee Go：每天 8 点自动把 AI/科技新闻推送到微信群，零服务器零费用"
subtitle: "一个跑在 Gitee Go 上的自动化新闻抓取 + 推送管道"
date: 2026-07-31
author: "Minglin"
header-img: "img/post-bg.jpg"
tags:
  - Python
  - DevOps
  - 自动化
  - RSS
---

## 一、这东西是干嘛的

每天早上 8:00，微信群里收到一条这样的消息：

```
2026-07-31 周四 · 科技早报

🤖 AI/LLM
> Kuna: Decompiler Development in the Age of Coding Agents
  AI 驱动的反编译器，将二进制逆向效率提升一个数量级
> LLM Honeypot
  用大模型做蜜罐，诱捕攻击者的新思路

📦 DevOps
> Docker 26.0 发布，内置 Compose v3
  原生支持 GPU 设备映射和增量构建缓存

📊 共 21 条
```

覆盖 AI/LLM、开源工具、DevOps、安全、低代码/IoT、教育信息化六大方向，来源包括 GitHub Trending、Hacker News、掘金热榜、少数派、嘶吼、安全客、芥末堆。

**关键点：这东西不需要服务器，不需要域名，不需要花钱。** 唯一需要的是你有一个 Gitee 账号和一个企业微信群机器人。

---

## 二、为什么不用现成的 RSS 阅读器

市面上的 RSS 阅读器（Feedly、Inoreader、Reeder）有几个痛点：

1. **不能推送到微信**。微信是国内团队协作的事实标准，每天早上打开微信群看早报比打开一个单独的 App 方便得多。
2. **分类靠手动**。加一个源要手动设置分类、标签，加十个源就是十次操作。
3. **去重靠运气**。同一个新闻被多个源报道是常事，手动阅读的时候靠人眼去重。
4. **不免费**。好用的 RSS 服务都是订阅制，一年几百块。

所以我写了 News Courier —— 一个跑在 Gitee Go 上的自动化新闻抓取 + 推送管道。

---

## 三、架构设计

整体架构分三层，清晰到一眼看完：

```
Gitee Go Cron (每天 8:00)
        │
        ▼
   ┌──────────┐
   │  抓取层   │  GitHub Trending 爬虫 + HN API + 掘金 API + 通用 RSS 引擎
   └────┬─────┘
        ▼
   ┌──────────┐
   │  清洗层   │  去垃圾 → 同次去重 → 跨天去重 → 频道限流（每频道 5 条）
   └────┬─────┘
        ▼
   ┌──────────┐
   │  推送层   │  组装企业微信 Markdown → Webhook 推送（失败重试 2 次）
   └──────────┘
```

### 3.1 抓取层

四个 Fetcher，每个职责单一：

| Fetcher | 来源 | 技术 |
|---------|------|------|
| GitHub Trending | github.com/trending | requests + BeautifulSoup4 爬虫 |
| Hacker News | Firebase API | httpx 异步请求 |
| 掘金热榜 | 掘金推荐 API | requests POST |
| 通用 RSS | subscriptions.json 配置 | feedparser 解析 |

通用 RSS Fetcher 是整个抓取层最巧妙的部分。所有 RSS 源的定义不在代码里，而在一个 JSON 文件中：

```json
{
  "rss": [
    { "name": "少数派", "url": "https://sspai.com/feed", "channel": "低代码/IoT", "enabled": true },
    { "name": "嘶吼", "url": "https://www.4hou.com/feed", "channel": "安全/密码", "enabled": true },
    { "name": "安全客", "url": "https://api.anquanke.com/data/v1/rss", "channel": "安全/密码", "enabled": true },
    { "name": "芥末堆", "url": "https://www.jiemodui.com/feed", "channel": "教育信息化", "enabled": true }
  ]
}
```

加一个新源只需加一行 JSON，Push 到仓库，下次运行自动生效。删源只需把 `enabled` 改成 `false`。不需要改一行 Python 代码。

### 3.2 清洗层

清洗层分四刀砍：

1. **去垃圾**：过滤空标题、无效 URL（掘金 API 有时候返回 `juejin.cn/post/` 这种占位链接）
2. **同次去重**：一次抓取中同一个 URL 只保留第一条（多个源可能报道同一新闻）
3. **跨天去重**：查 `state.json` 缓存，昨天推送过的今天不再推送
4. **频道限流**：每个频道最多保留 N 条（默认 5），防止某个频道霸屏

最终输出量约在 20 条左右，覆盖 4-5 个频道，阅读时间约 6 分钟。

### 3.3 推送层

企业微信群机器人只支持有限的 Markdown 语法：**粗体**、[链接]()、`>` 引用、`<font color="info">` 彩色文字。

格式化引擎针对这个限制做了优化：
- 频道标题用 `<font color="info">` 蓝色突出
- 每条新闻用 `>` 引用缩进，视觉上层次分明
- 摘要控制在 70 字以内，在中文标点处智能截断
- 每条新闻搭配来源链接，点击直达原文

---

## 四、跨天去重是怎么做的

这是整个项目最巧妙的工程决策。

**问题**：Gitee Go 每次跑流水线是全新容器，结束就销毁。如果不持久化，每天推送的内容会大量重复。

**最初方案**：SQLite 本地存 URL 哈希，但容器一销毁就没了。

**第二方案**：Git Push 把去重记录写回仓库。但 Gitee Go 容器没有 Push 权限，搞个人令牌又太麻烦。

**最终方案**：利用 Gitee Go 的**步骤缓存**（Step Caches）。缓存基于 S3，有效期 30 天，每次成功构建自动续期。把去重数据写到 `~/.news-courier/state.json`，这个路径同时配在步骤缓存中：

```yaml
caches:
  - ~/.cache/pip       # pip 包缓存（加速构建）
  - ~/.news-courier    # 去重数据缓存（跨天持久化）
```

每天早上流水线的执行流程：

```
06:50:28 获取缓存文件 → 恢复 ~/.news-courier/state.json（带着昨天的推送记录）
06:50:29 pip install（秒级，pip 包也从缓存加载）
06:50:35 python -m src.main
         → 读取 state.json → 过滤已推送的 67 个 URL
         → 抓取 68 条新数据 → 去重去除 0 条 → 已推过滤砍掉 45 条
         → 最终推送 21 条全新内容
06:51:15 推送成功 → 写入新的 state.json
         → Gitee Go 自动上传更新后的 ~/.news-courier 到缓存
```

第二天再跑，又能读到前一天的推送记录，形成一个闭环。**不需要数据库，不需要 Redis，不需要 Token，就靠 Gitee Go 原生缓存。**

---

## 五、本地怎么玩

```powershell
# 克隆 + 虚拟环境
git clone https://gitee.com/<你>/news-courier.git
cd news-courier
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 预览模式（抓取→格式化→打印到控制台，不推送）
python -m src.main --dry-run

# 推送模式（需要 webhook URL）
$env:WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
python -m src.main --push

# 遇到代理错误（Windows 系统代理常见问题）
$env:PROXY_BYPASS = "true"
```

本地运行结束后会输出一份详细的执行报告：

```
────────────────────────────────────────
📋 执行报告（推送）
────────────────────────────────────────
  📥 抓取
     github: ✗ Connection timeout
     hackernews: 8 条
     juejin: 20 条
     rss: 40 条
  🧹 清洗
     抓取总计      68 条
     重复去除     -0 条
     已推过滤     -45 条
     最终保留      21 条
  📡 频道分布
     AI/LLM: 5 条
     DevOps: 1 条
     低代码/IoT: 5 条
     安全/密码: 5 条
     教育信息化: 5 条
  ⏱ 耗时 36.7s
────────────────────────────────────────
```

每个源的抓取量、去重砍了多少、每个频道分到几条，一目了然。

---

## 六、踩过的坑

### 6.1 GitHub Actions 格式 ≠ Gitee Go 格式

最初理所当然地用 GitHub Actions 格式（`.gitee/workflows/`），在 Gitee Go 页面完全看不到流水线。Gitee Go 用的是自己的 YAML Schema（`.workflow/` 目录），`stages` 的结构和字段名完全不同。文档不多，大部分靠看别人的公开仓库反推。

### 6.2 Python 3.9 的版本墙

Gitee Go 的 `build@python` 最高只支持到 Python 3.9，而 `lxml` 最新版要求 ≥ 3.10。解决方式是直接用标准库的 `html.parser` 替代 `lxml`，功能完全一致，还省了一个依赖。

### 6.3 缓存路径对齐

Gitee Go 步骤缓存的相对路径解析基准是 `/root/workspace`，而代码的工作目录是 `/root/workspace/<用户名>/<仓库名>/`。用相对路径做缓存会导致读写两个不同目录——缓存白做了。最终用 `~/.news-courier` 统一了本地和 CI 环境。

### 6.4 GitHub 被墙

GitHub Trending 是唯一一个在 Gitee Go 国内服务器上无法访问的源（连接超时）。好在 HN 的 Firebase API 不受影响，AI/LLM 和 DevOps 频道依然有内容。

---

## 七、仓库地址

**Gitee**：[https://gitee.com/](https://gitee.com/)

开源协议：MIT。欢迎 Fork、提 Issue、贡献 RSS 源配置。

---

## 八、下一步

- [ ] 接入 DeepSeek API，把截断式摘要改成 LLM 一句话总结
- [ ] 支持钉钉 / 飞书 / Telegram 推送
- [ ] Web 管理界面，在线管理订阅源
- [ ] GitHub Actions 双平台备份

如果你觉得有用，点个 Star ⭐，或者直接把 `subscriptions.json` 改改自己用起来。
