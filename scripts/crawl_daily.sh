#!/bin/bash
# FindIt 智能爬虫 - 每天覆盖核心城市

cd "$(dirname "$0")"
cd ..

MODE=${1:-quick}
MAX_NOTES=${2:-10}
MAX_COMMENTS=${3:-5}

echo "🤖 FindIt 智能爬虫系统"
echo "========================================"
echo "⏰ 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

case $MODE in
    "full")
        echo "📋 模式: 完整覆盖"
        echo "🏙️  城市: 10个核心城市 (北京+新一线+国际)"
        echo "🔑 关键词: 11个关键词 (全部)"
        echo "⏱️  预计耗时: 30-40分钟"
        echo ""
        python3 scripts/smart_crawler_fixed.py \
            --mode full \
            --max-notes $MAX_NOTES \
            --max-comments $MAX_COMMENTS \
            --batch-size 4
        ;;

    "quick")
        echo "📋 模式: 快速覆盖 (推荐)"
        echo "🏙️  城市: 6个核心城市 (北京+上海+深圳+广州+香港+新加坡)"
        echo "🔑 关键词: 3个核心关键词 (���对象+相亲+脱单)"
        echo "⏱️  预计耗时: 5-10分钟"
        echo ""
        python3 scripts/smart_crawler_fixed.py \
            --mode quick \
            --max-notes $MAX_NOTES \
            --max-comments $MAX_COMMENTS \
            --batch-size 3
        ;;

    "test")
        echo "🧪 模式: 测试"
        echo "🏙️  城市: 深圳"
        echo "🔑 关键词: 找对象"
        echo "⏱️  预计耗时: 1-2分钟"
        echo ""
        python3 scripts/smart_crawler_fixed.py \
            --mode test \
            --max-notes 5 \
            --max-comments 2
        ;;

    "custom")
        echo "📝 模式: 自定义"
        echo "用法: $0 custom \"城市1 城市2\" \"关键词1 关键词2\""
        echo ""
        echo "示例:"
        echo "  $0 custom \"北京 上海\" \"找对象 相亲\""
        echo "  $0 custom \"深圳 香港\" \"CPDD 脱单\""
        exit 1
        ;;

    "preview")
        echo "🔍 模式: 预览任务"
        echo ""
        python3 scripts/smart_crawler_fixed.py --mode quick --dry-run
        exit 0
        ;;

    *)
        echo "❌ 未知模式: $MODE"
        echo ""
        echo "可用模式:"
        echo "  full   - 完整覆盖 (10城市+11关键词, 30-40分钟)"
        echo "  quick  - 快速覆盖 (6城市+3关键词, 5-10分钟) ⭐推荐"
        echo "  test   - 测试模式 (1城市+1关键词, 1-2分钟)"
        echo "  custom - 自定义模式"
        echo "  preview- 预览任务"
        echo ""
        echo "用法:"
        echo "  $0 [模式] [最大帖子数] [最大评论数]"
        echo ""
        echo "示例:"
        echo "  $0 quick          # 快速模式 (推荐)"
        echo "  $0 full          # 完整覆盖"
        echo "  $0 test          # 快速测试"
        echo "  $0 quick 15 5    # 自定义数量"
        echo "  $0 preview       # 预览任务"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "✅ 爬取完成"
echo "⏰ 时间: $(date '+%Y-%m-%d %H:%M:%S')"