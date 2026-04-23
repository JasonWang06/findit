# ⚡ 爬虫性能优化指南

## 🔍 问题分析

您说得对！之前的爬取确实花了很长时间。主要原因是：

### 时间消耗分解
```
总耗时 ≈ 搜索时间 + 详情抓取 + 评论抓取

搜索一个关键词:     ~10-20秒
抓取帖子详情:       每个~5-10秒  × 20个帖子 = 100-200秒
抓取帖子评论:       每个~15-30秒 × 20个帖子 = 300-600秒

总耗时: 10-40分钟 (取决于评论数量)
```

## ⚡ 优化方案

### 方案1: 快速模式 (仅搜索，无评论)
```bash
# 本地快速爬虫
bash scripts/quick_crawl.sh

# 耗时: ~2-5分钟
# 数据: 帖子基本信息 + 帖子链接
# 适用: 快速获取新用户，评论通过链接查看
```

### 方案2: 平衡模式 (少量评论)
```bash
cd ~/Desktop/MediaCrawler
source venv/bin/activate

python main.py \
    --platform xhs \
    --lt cookie \
    --type search \
    --keywords "深圳找对象,深圳相亲,深圳搭子" \
    --max_comments_count_single_no 5  # 每个帖子只抓5条评论

# 耗时: ~5-10分钟
# 数据: 帖子信息 + 少量高赞评论
# 适用: 平衡速度和数据完整性
```

### 方案3: 完整模式 (所有评论 - 仅针对重要帖子)
```bash
# 先快速筛选，再深度抓取
# 第一步：快速搜索
python main.py --platform xhs --lt cookie --type search \
    --keywords "深圳找对象" --max_comments_count_single_no 0

# 第二步：对感兴趣的帖子深度抓取
python main.py --platform xhs --lt cookie --type detail \
    --note_ids "帖子ID1,帖子ID2,帖子ID3"
```

## 📊 性能对比

| 模式 | 每个关键词耗时 | 数据完整性 | 适用场景 |
|------|--------------|-----------|----------|
| 快速模式 | 2-3分钟 | ⭐⭐⭐ | 日常更新，快速扩量 |
| 平衡模式 | 5-10分钟 | ⭐⭐⭐⭐ | 生产环境推荐 |
| 完整模式 | 15-30分钟 | ⭐⭐⭐⭐⭐ | 深度分析，特定研究 |

## 🚀 服务器自动化优化配置

### 快速部署配置
```bash
# 编辑服务器爬虫脚本
nano ~/mediacrawler/run_crawler.sh

# 修改参数:
MAX_COMMENTS=5           # 从10改为5，减少50%时间
MAX_NOTES=10             # 从20改为10，减少50%时间
```

### 定时任务优化
```bash
# 原配置: 每天2次，每次完整爬取
0 8,20 * * * /bin/bash ~/mediacrawler/run_crawler.sh

# 优化配置: 每天4次，每次快速爬取
0 */6 * * * /bin/bash ~/mediacrawler/run_crawler.sh
# 每6小时一次，数据更新更频繁，单次更快
```

## 💡 实战建议

### 1. 分层爬取策略
```bash
# 每天早上: 快速模式 (获取新帖子)
0 8 * * * bash ~/mediacrawler/quick_crawl.sh

# 每天晚上: 平衡模式 (获取评论数据)
0 20 * * * bash ~/mediacrawler/balanced_crawl.sh
```

### 2. 关键词分组
```bash
# 高频关键词 (每天爬)
KEYWORDS="深圳找对象,深圳相亲,深圳搭子"

# 中频关键词 (每3天爬)
KEYWORDS="北京找对象,上海相亲,广州交友"

# 低频关键词 (每周爬)
KEYWORDS="杭州交友,成都脱单,武汉相亲"
```

### 3. 增量爬取
```bash
# 只爬取最新的帖子，避免重复
python main.py \
    --platform xhs \
    --lt cookie \
    --type search \
    --keywords "深圳找对象" \
    --start_page 1 \        # 只爬第1页
    --max_comments_count_single_no 3  # 少量评论
```

## 🔧 性能监控

### 创建性能监控脚本
```bash
#!/bin/bash
# monitor_crawler_performance.sh

LOG_FILE="~/mediacrawler/logs/performance.log"

echo "[$(date)] 开始监控爬虫性能..." >> "$LOG_FILE"

# 记录开始时间
START=$(date +%s)

# 运行爬虫
bash ~/mediacrawler/run_crawler.sh

# 记录结束时间
END=$(date +%s)
DURATION=$((END - START))

# 计算效率
FILE_COUNT=$(ls -1 ~/mediacrawler/output/*.jsonl 2>/dev/null | wc -l)
EFFICIENCY=$(echo "scale=2; $FILE_COUNT / $DURATION * 60" | bc)

echo "[$(date)] 性能统计:" >> "$LOG_FILE"
echo "  耗时: ${DURATION}秒" >> "$LOG_FILE"
echo "  文件数: $FILE_COUNT" >> "$LOG_FILE"
echo "  效率: $EFFICIENCY 文件/分钟" >> "$LOG_FILE"

# 效率阈值告警
if (( $(echo "$EFFICIENCY < 2" | bc -l) )); then
    echo "[$(date)] ⚠️  效率低于阈值，考虑优化" >> "$LOG_FILE"
fi
```

## 📈 预期优化效果

### 优化前
```
每次爬取: 20-40分钟
每天2次: 40-80分钟总耗时
数据量: 每次约80个帖子 + 完整评论
```

### 优化后 (推荐配置)
```
每次爬取: 5-8分钟
每天4次: 20-32分钟总耗时
数据量: 每次约40个帖子 + 重点评论
总体效率提升: 60%+
```

## 🎯 立即使用

### 快速测试优化效果
```bash
# 1. 备份当前配置
cp config/base_config.py config/base_config.py.backup

# 2. 修改配置
nano config/base_config.py
# 设置: CRAWLER_MAX_NOTES_COUNT = 10
# 设置: (默认评论数量会减少)

# 3. 测试爬取
bash scripts/quick_crawl.sh

# 4. 查看耗时对比
```

### 服务器部署优化版本
```bash
# 1. 上传优化脚本到服务器
scp deploy/server_optimized_crawler.sh user@server:~/mediacrawler/

# 2. SSH 到服务器
ssh user@server

# 3. 替换现有脚本
mv ~/mediacrawler/server_optimized_crawler.sh ~/mediacrawler/run_crawler.sh

# 4. 手动测试
bash ~/mediacrawler/run_crawler.sh

# 5. 更新定时任务
crontab -e
# 修改为更频繁但更短的间隔
```

---

**总结**: 通过减少评论数量和帖子数量，可以将单次爬取时间从20-40分钟降低到5-8分钟，同时通过增加频率来保证数据的及时性。这是时间效率的最优平衡点。