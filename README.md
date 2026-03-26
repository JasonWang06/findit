# FindIt - 小红书搭子匹配 MVP

帮助用户在小红书上精准找到真实求偶女性，并生成个性化破冰话术。

## 架构

```
爬虫模块 → SQLite存储 → 规则筛选 → AI精筛(Claude) → 话术生成 → Telegram Bot推送
```

## 模块

- `findit/crawler/` — 小红书数据采集（搜索帖子→评论区→用户主页）
- `findit/ai/` — 规则过滤 + Claude API 评分 + 话术生成
- `findit/recommender/` — 推荐引擎（每日5个匹配：3高+2中）
- `findit/bot/` — Telegram Bot 交互界面
- `findit/db/` — SQLite 数据层
- `findit/pipeline.py` — 全流程编排

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API keys

# 运行爬虫
findit-crawl

# 启动 Telegram Bot
findit-bot

# 运行完整流程（爬虫+筛选+匹配）
findit-pipeline
```

## Telegram Bot 命令

| 命令 | 说明 |
|------|------|
| `/start` | 开始使用 |
| `/setup` | 设置个人资料 |
| `/match` | 获取今日匹配 |
| `/preferences` | 设置筛选偏好 |
| `/help` | 查看帮助 |

## 测试

```bash
pytest tests/ -v
```
