# FindIt - 小红书搭子匹配 MVP

帮助用户在小红书上精准找到真实求偶女性，并生成个性化破冰话术。

## 架构

```
┌─────────────┐     ┌─────────┐     ┌──────────┐     ┌──────────────┐
│ CrawlerService │──▶│ SQLite  │──▶│ 关键词筛选 │──▶│ Telegram Bot  │
│  (后台持续跑)  │   │ (共享池) │   │ (共享过滤) │   │  (用户交互)   │
└─────────────┘     └─────────┘     └──────────┘     └──────────────┘
                                         │                    │
                                    [可选] AI评分         [可选] 话术生成
                                    (需要API Key)        (需要API Key)
```

两个独立服务：
- **爬虫服务**：后台持续抓取小红书数据 + 关键词筛选中介/营销号
- **Telegram Bot**：用户注册、每日推送匹配、话术生成

## 模块

| 模块 | 说明 |
|------|------|
| `findit/services/crawler_service.py` | 爬虫后台服务（爬取+共享筛选） |
| `findit/services/matching_service.py` | Per-user 匹配服务 |
| `findit/crawler/` | 小红书API客户端（搜索→评论→主页） |
| `findit/ai/filter_rules.py` | 关键词筛选（中介/营销号/空号/不活跃） |
| `findit/ai/scorer.py` | AI兼容度评分（可选，需API Key） |
| `findit/ai/opener.py` | AI话术生成（可选，需API Key） |
| `findit/bot/` | Telegram Bot 交互界面 |
| `findit/db/` | SQLite 数据层 |

---

## 部署指南（Ubuntu 服务器）

### 第零步：准备工作

在部署之前，你需要准备两样东西：

**1. Telegram Bot Token**
- 打开 Telegram，搜索 `@BotFather`
- 发送 `/newbot`，按提示创建一个 Bot
- 创建完成后会给你一个 Token，格式如 `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

**2. 小红书 Cookie**
- 用 Chrome 登录小红书 (xiaohongshu.com)
- 按 F12 打开开发者工具 → Network 标签
- 刷新页面，点任意一个请求
- 在 Request Headers 里找到 `Cookie` 字段，复制整个值

### 第一步：SSH 连接服务器

```bash
ssh 你的用户名@你的服务器IP
```

### 第二步：下载代码

```bash
# 安装 git（如果没有的话）
sudo apt-get update && sudo apt-get install -y git

# 下载代码
cd ~
git clone https://github.com/jasonwang06/findit.git
cd findit
```

### 第三步：运行部署脚本

```bash
bash deploy/setup.sh
```

这个脚本会自动：安装 Python → 创建虚拟环境 → 安装依赖 → 安装系统服务

### 第四步：填写配置

```bash
nano /opt/findit/.env
```

填入以下内容（把 `xxx` 替换成真实值）：

```
TELEGRAM_BOT_TOKEN=你的Bot Token
XHS_COOKIE=你的小红书Cookie

# 下面这个暂时不填，后面需要AI评分时再加
# ANTHROPIC_API_KEY=
```

按 `Ctrl+O` 保存，`Ctrl+X` 退出。

### 第五步：启动服务

```bash
# 启动爬虫（后台持续抓数据）
sudo systemctl start findit-crawler

# 启动 Telegram Bot
sudo systemctl start findit-bot

# 设置开机自启
sudo systemctl enable findit-crawler
sudo systemctl enable findit-bot
```

### 第六步：验证

```bash
# 查看爬虫日志
sudo journalctl -u findit-crawler -f

# 查看 Bot 日志（另开一个终端）
sudo journalctl -u findit-bot -f
```

然后去 Telegram 找你创建的 Bot，发送 `/start` 试试！

### 常用运维命令

```bash
# 查看服务状态
sudo systemctl status findit-crawler
sudo systemctl status findit-bot

# 重启服务（改了配置后需要重启）
sudo systemctl restart findit-crawler
sudo systemctl restart findit-bot

# 停止服务
sudo systemctl stop findit-crawler
sudo systemctl stop findit-bot

# 查看最近100行日志
sudo journalctl -u findit-crawler -n 100
sudo journalctl -u findit-bot -n 100

# 查看数据库里抓了多少数据
cd /opt/findit
source venv/bin/activate
python3 -c "
from findit.db import Database
db = Database('data/findit.db')
with db._conn() as c:
    posts = c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    authors = c.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    filtered = c.execute('SELECT COUNT(*) FROM authors WHERE is_filtered_out=1').fetchone()[0]
    print(f'帖子: {posts}')
    print(f'作者: {authors} (过滤掉: {filtered})')
"
```

---

## 本地开发

```bash
pip install -e ".[dev]"
cp .env.example .env
# 编辑 .env

# 单次爬取
findit-crawl

# 启动 Bot
findit-bot

# 完整流程（爬取+筛选+匹配）
findit-pipeline

# 测试
pytest tests/ -v
```

## Telegram Bot 命令

| 命令 | 说明 |
|------|------|
| `/start` | 开始使用 |
| `/setup` | 设置个人资料 |
| `/match` | 获取今日匹配 |
| `/preferences` | 设置筛选偏好 |
| `/help` | 查看帮助 |
