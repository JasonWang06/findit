#!/bin/bash
# 服务器版快速爬虫脚本 - 优化的自动化爬取

LOG_DIR="~/mediacrawler/logs"
DATA_DIR="~/mediacrawler/output"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建目录
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# 配置参数 (可根据需要调整)
KEYWORDS="深圳找对象,深圳相亲,深圳搭子,北京找对象,上海相亲"
MAX_NOTES=15              # 每个关键词最多抓取15个帖子
MAX_COMMENTS=5            # 每个帖子最多抓取5条评论 (适度)
CRAWLER_TYPE="search"

echo "[$(date)] 🚀 开始优化爬取..." | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"
echo "[$(date)] 配置: 关键词=$KEYWORDS, 帖子数=$MAX_NOTES, 评论数=$MAX_COMMENTS" | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"

# 记录开始时间
START_TIME=$(date +%s)

# 进入项目目录
cd ~/MediaCrawler
source venv/bin/activate

# 运行爬虫
python main.py \
    --platform xhs \
    --lt cookie \
    --type $CRAWLER_TYPE \
    --keywords "$KEYWORDS" \
    --max_comments_count_single_no $MAX_COMMENTS \
    >> "$LOG_DIR/crawler_$TIMESTAMP.log" 2>&1

# 检查结果
if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo "[$(date)] ✅ 爬取成功! 耗时: ${DURATION}秒" | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"

    # 复制数据到输出目录
    cp -r data/xhs/jsonl/* "$DATA_DIR/" 2>/dev/null || true

    # 统计结果
    TOTAL_FILES=$(ls -1 "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
    TOTAL_LINES=$(cat "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')

    echo "[$(date)] 📊 数据统计: 文件=$TOTAL_FILES, 总行数=$TOTAL_LINES" | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"
else
    echo "[$(date)] ❌ 爬取失败" | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"
fi

echo "[$(date)] 📝 脚本执行完毕" | tee -a "$LOG_DIR/crawler_$TIMESTAMP.log"