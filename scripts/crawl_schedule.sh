#!/bin/bash
# 智能爬虫调度脚本 - 根据时间自动安排爬虫任务

cd "$(dirname "$0")"
cd ..

# 检查参数
MODE=${1:-auto}
MAX_NOTES=${2:-10}
MAX_COMMENTS=${3:-5}

echo "🤖 FindIt 智能爬虫调度系统"
echo "========================================"

if [ "$MODE" = "auto" ]; then
    echo "📅 模式: 自动调度"
    echo "⏰ 当前时间: $(date '+%Y-%m-%d %H:%M:%S (%A)')"
    echo ""

    # 运行智能调度
    python3 scripts/smart_crawler.py \
        --mode auto \
        --max-notes $MAX_NOTES \
        --max-comments $MAX_COMMENTS

elif [ "$MODE" = "test" ]; then
    echo "🧪 模式: 快速测试"
    echo "⏰ 当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 运行测试
    python3 scripts/smart_crawler.py \
        --mode test \
        --max-notes 5 \
        --max-comments 2

elif [ "$MODE" = "manual" ]; then
    echo "📝 模式: 手动指定"
    echo "用法: $0 manual \"城市1 城市2\" \"关键词1 关键词2\""
    echo ""
    echo "示例:"
    echo "  $0 manual \"北京 上海\" \"找对象 相亲\""
    echo "  $0 manual \"深圳\" \"CPDD 脱单\""
    exit 1

elif [ "$MODE" = "schedule" ]; then
    echo "📅 模式: 查看调度计划"
    echo ""

    python3 << 'EOF'
from datetime import datetime
import sys
sys.path.insert(0, '.')

from scripts.smart_crawler import CRAWL_SCHEDULE

print("📅 每日爬取计划:")
print("-" * 40)
for day, (cities, keywords) in CRAWL_SCHEDULE["daily"].items():
    print(f"{day}: {', '.join(cities)} - {', '.join(keywords)}")

print("\n📅 每周深度爬取:")
print("-" * 40)
for day, config in CRAWL_SCHEDULE["weekly"].items():
    if "tier_1_full" in config:
        print(f"{day}: 一线城市全面爬取")
    elif "tier_1_5_full" in config:
        print(f"{day}: 新一线城市全面爬取")
EOF

elif [ "$MODE" = "dry-run" ]; then
    echo "🔍 模式: 预览任务 (不实际执行)"
    echo "⏰ 当前时间: $(date '+%Y-%m-%d %H:%M:%S (%A)')"
    echo ""

    # 预览当前应该执行的任务
    python3 scripts/smart_crawler.py --mode auto --dry-run

else
    echo "❌ 未知模式: $MODE"
    echo ""
    echo "可用模式:"
    echo "  auto    - 自动调度 (根据时间和预设计划)"
    echo "  test    - 快速测试 (单个关键词验证)"
    echo "  manual  - 手动指定 (需要提供城市和关键词)"
    echo "  schedule - 查看完整调度计划"
    echo "  dry-run - 预览当前任务"
    echo ""
    echo "用法:"
    echo "  $0 auto          # 自动调度"
    echo "  $0 test          # 快速测试"
    echo "  $0 schedule      # 查看调度计划"
    echo "  $0 dry-run       # 预览任务"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ 调度完成"
echo "⏰ 结束时间: $(date '+%Y-%m-%d %H:%M:%S')"