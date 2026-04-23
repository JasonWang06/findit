#!/bin/bash
# 优化后的快速爬虫脚本 - 只搜索帖子，不爬评论，快速获取数据

# 设置工作目录
cd ~/Desktop/MediaCrawler
source venv/bin/activate

# 配置参数
KEYWORDS="深圳找对象,深圳相亲,深圳搭子"
MAX_NOTES=20              # 每个关键词最多抓取20个帖子
MAX_COMMENTS=0            # 不抓评论（设置为0以加快速度）
CRAWLER_TYPE="search"

echo "🚀 开始快速爬取 (仅帖子，不抓评论)"
echo "关键词: $KEYWORDS"
echo "最大帖子数: $MAX_NOTES"
echo "开始时间: $(date)"

# 记录开始时间
START_TIME=$(date +%s)

# ���行爬虫
python main.py \
    --platform xhs \
    --lt cookie \
    --type search \
    --keywords "$KEYWORDS" \
    --max_comments_count_single_no $MAX_COMMENTS

# 计算耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "✅ 爬取完成!"
echo "结束时间: $(date)"
echo "总耗时: ${DURATION}秒 ($(($DURATION / 60))分钟)"

# 显示结果
echo ""
echo "📊 爬取结果:"
ls -lh data/xhs/jsonl/search_contents_*.jsonl | tail -1
wc -l data/xhs/jsonl/search_contents_*.jsonl | tail -1