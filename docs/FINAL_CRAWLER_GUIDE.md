# 🚀 FindIt 爬虫最终使用指南

## 📯 核心策略

**每天都要覆盖的核心城市** (不按星期几分配):
- **一线城市**: 北京、上海、深圳、广州
- **新一线**: 杭州、成都、南京、武汉
- **国际**: 香港、新加坡

**核心关键词** (按优先级):
1. `找对象` - 最直接，意图明确
2. `相亲` - 认真程度高
3. `脱单` - 紧迫感强
4. `交友` - 范围较广
5. `CPDD` - 年轻用户

## ⚡ 三种使用模式

### 1. 快速模式 (⭐推荐)
```bash
# 每天2-4次，每次5-10分钟
bash scripts/crawl_daily.sh quick

# 任务: 6城市 × 3关键词 = 18个组合
# 预计: 5-10分钟
# 适用: 日常数据更新
```

### 2. 完整模式
```bash
# 每天1次，30-40分钟
bash scripts/crawl_daily.sh full

# 任务: 10城市 × 11关键词 = 110个组合
# 预计: 30-40分钟
# 适用: 全面数据覆盖
```

### 3. 测试模式
```bash
# 验证系统是否正常
bash scripts/crawl_daily.sh test

# 任务: 1城市 × 1关键词 = 1个组合
# 预计: 1-2分钟
# 适用: 快速验证
```

## 📅 推荐的自动化设置

### 方案A: 保守型 (每天2次)
```bash
# 早9点，晚9点
crontab -e

# 添加:
0 9,21 * * * cd /Users/json/Desktop/findit && bash scripts/crawl_daily.sh quick >> logs/daily_crawl.log 2>&1
```

### 方案B: 积极型 (每天4次)
```bash
# 每6小时一次
crontab -e

# 添加:
0 */6 * * * cd /Users/json/Desktop/findit && bash scripts/crawl_daily.sh quick >> logs/daily_crawl.log 2>&1
```

### 方案C: 混合型 (推荐)
```bash
# 工作日快速模式，周末完整模式
crontab -e

# 添加:
0 */6 * * * 1-5 cd /Users/json/Desktop/findit && bash scripts/crawl_daily.sh quick >> logs/daily_crawl.log 2>&1
0 10,20 * * 6,0 cd /Users/json/Desktop/findit && bash scripts/crawl_daily.sh full >> logs/weekly_crawl.log 2>&1
```

## 🎯 立即开始

### 第1步: 预览任务
```bash
# 查看将要执行的任务
bash scripts/crawl_daily.sh preview
```

### 第2步: 快速测试
```bash
# 验证系统正常
bash scripts/crawl_daily.sh test
```

### 第3步: 运行第一次爬取
```bash
# 运行快速模式
bash scripts/crawl_daily.sh quick
```

### 第4步: 设置自动化
```bash
# 设置定时任务
crontab -e

# 添加: 每天4次快速模式
0 */6 * * * cd /Users/json/Desktop/findit && bash scripts/crawl_daily.sh quick >> logs/daily_crawl.log 2>&1
```

## 📊 预期效果

### 数据增长
```
快速模式 (每天4次):
├── 每次约 50-100 个新帖子
├── 每天 200-400 个新帖子
└── 每周 1400-2800 个新帖子

完整模式 (每周1次):
├── 每次约 500-1000 个新帖子
└── 每周补充 500-1000 个帖子

总计: 每周 2000-4000 个新用户
```

### 地理分布
```
一线城市 (北京、上海、深圳、广州):     40%
新一线城市 (杭州、成都、南京、武汉):   35%
国际城市 (香港、新加坡):             25%
```

### 用户质量
```
直接找对象:   70% (意向最明确)
相亲类:       20% (认真程度高)
脱单/交友:    10% (年轻用户活跃)
```

## 💡 自定义使用

### 只爬特定城市
```bash
# 修改脚本中的 CORE_CITIES
# 或者使用自定义模式 (待开发)
```

### 只爬特定关键词
```bash
# 修改脚本中的 KEYWORDS_PRIORITY
# 或者使用自定义模式 (待开发)
```

### 调整爬取数量
```bash
# 更保守 (更快)
bash scripts/crawl_daily.sh quick 5 2

# 更激进 (更多数据)
bash scripts/crawl_daily.sh quick 15 10
```

## 🚀 服务器部署

### 日本服务器配置
```bash
# 1. 上传脚本到服务器
scp scripts/crawl_daily.sh server:~/mediacrawler/

# 2. SSH 到服务器
ssh server

# 3. 设置服务器定时任务
crontab -e

# 添加服务器定时任务 (UTC时间调整)
0 */6 * * * cd ~/mediacrawler && bash crawl_daily.sh quick >> logs/cron.log 2>&1
```

---

## 🎉 总结

**新的策略**: 每天覆盖核心城市，不按星期几分配
**核心优势**: 系统化、高效、覆盖全面
**推荐模式**: 快速模式每天4次，完整模式每周1次

**立即开始**: `bash scripts/crawl_daily.sh quick` 🚀