#!/usr/bin/env python3
"""简化的智能爬虫系统 - 每天覆盖核心城市"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ===== 核心城市配置 (每天都要爬) =====

CORE_CITIES = [
    # 一线城市
    "北京", "上海", "深���", "广州",
    # 新一线城市
    "杭州", "成都", "南京", "武汉",
    # 国际城市
    "香港", "新加坡"
]

# 关键词配置 (按优先级排序)
KEYWORDS_PRIORITY = [
    # 第一优先级：直接交友类 (最明确的意图)
    ["找对象", "相亲", "脱单"],
    # 第二优先级：年轻化表达
    ["CPDD", "交友"],
    # 第三优先级：特定表达
    ["找男友", "找女友", "蹲男友"],
]

# 关键词的完整组合
ALL_KEYWORDS = [
    "找对象", "相亲", "脱单", "交友", "CPDD",
    "找男友", "找女友", "蹲男友", "蹲女友",
    "征婚", "单身交友"
]


def generate_city_keyword_combinations(cities=None, keywords=None):
    """生成城市+关键词的所有组合"""
    cities = cities or CORE_CITIES
    keywords = keywords or ALL_KEYWORDS

    combinations = []

    # 检查关键词是否已经包含城市前缀
    has_city_prefix = any(any(kw.startswith(city) for city in CORE_CITIES) for kw in keywords)

    if has_city_prefix:
        # 如果关键词已经包含城市前缀，直接使用
        combinations = keywords
    else:
        # 否则，组合城市和关键词
        for city in cities:
            for keyword in keywords:
                # 只组合有意义的组合 (避免"香港蹲男友"这种奇怪的)
                if keyword in ["CPDD", "脱单", "找对象", "相亲", "交友"]:
                    combinations.append(f"{city}{keyword}")
                elif keyword in ["找男友", "蹲男友"]:
                    # 这些词一般不用于城市限定
                    if city in ["北京", "上海", "深圳", "广州"]:
                        combinations.append(f"{city}{keyword}")

    return combinations


def run_crawler_task(keywords, max_notes=10, max_comments=5):
    """执行单个爬虫任务"""
    if isinstance(keywords, list):
        keywords_str = ",".join(keywords)
    else:
        keywords_str = keywords

    print(f"🚀 爬取: {keywords_str}")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

    cmd = [
        "python", "main.py",
        "--platform", "xhs",
        "--lt", "cookie",
        "--type", "search",
        "--keywords", keywords_str,
    ]

    if max_comments > 0:
        cmd.extend(["--max_comments_count_single_no", str(max_comments)])

    try:
        import os
        media_crawler_path = os.path.expanduser("~/Desktop/MediaCrawler")
        result = subprocess.run(
            cmd,
            cwd=media_crawler_path,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0:
            print(f"✅ 成功: {keywords_str}")
            return True
        else:
            print(f"❌ 失败: {keywords_str}")
            if result.stderr:
                print(f"   错误: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {keywords_str}")
        return False
    except Exception as e:
        print(f"❌ 异常: {keywords_str}, {e}")
        return False


def run_batch_crawl(combinations, batch_size=4, max_notes=10, max_comments=5):
    """批量运行爬虫，分批执行"""
    total = len(combinations)
    success_count = 0

    print(f"📋 总任务数: {total}")
    print(f"🔄 分批执行: 每批 {batch_size} 个")
    print("=" * 50)

    for i in range(0, total, batch_size):
        batch = combinations[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n🔄 第 {batch_num}/{total_batches} 批:")
        for combo in batch:
            if run_crawler_task(combo, max_notes, max_comments):
                success_count += 1

        print(f"📊 进度: {min(i + batch_size, total)}/{total} 成功: {success_count}")

    print(f"\n{'=' * 50}")
    print(f"🎉 完成: {success_count}/{total} 成功")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="FindIt 智能爬虫 - 每天覆盖核心城市")
    parser.add_argument("--mode", choices=["full", "quick", "test", "custom"], default="full",
                       help="模式: full(全部城市+关键词), quick(核心城市+核心关键词), test(测试), custom(自定义)")
    parser.add_argument("--cities", nargs="+", help="自定义城市列表")
    parser.add_argument("--keywords", nargs="+", help="自定义关键词列表")
    parser.add_argument("--max-notes", type=int, default=10, help="每个关键词最大帖子数")
    parser.add_argument("--max-comments", type=int, default=5, help="每个帖子最大评论数")
    parser.add_argument("--batch-size", type=int, default=4, help="每批执行的任务数")
    parser.add_argument("--dry-run", action="store_true", help="只显示任务，不执行")

    args = parser.parse_args()

    print("🤖 FindIt 智能爬虫系统")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 根据模式生成任务
    if args.mode == "full":
        print("📋 模式: 完整覆盖 (全部城市+全部关键词)")
        cities = CORE_CITIES
        keywords = ALL_KEYWORDS

    elif args.mode == "quick":
        print("📋 模式: 快速覆盖 (核心城市+核心关键词)")
        cities = ["北京", "上海", "深圳", "广州", "香港", "新加坡"]
        keywords = ["找对象", "相亲", "脱单"]

    elif args.mode == "test":
        print("🧪 模式: 测试 (单个关键词)")
        cities = ["深圳"]
        keywords = ["找对象"]

    elif args.mode == "custom":
        if not args.cities or not args.keywords:
            print("❌ 自定义模式需要 --cities 和 --keywords")
            return
        print("📋 模式: 自定义")
        cities = args.cities
        keywords = args.keywords

    # 生成任务组合
    combinations = generate_city_keyword_combinations(cities, keywords)

    print(f"🏙️  城市: {', '.join(cities)} ({len(cities)}个)")
    print(f"🔑 关键词: {', '.join(keywords)} ({len(keywords)}个)")
    print(f"📝 任务数: {len(combinations)}个组合")

    if args.dry_run:
        print("\n🔍 任务列表:")
        for i, combo in enumerate(combinations, 1):
            print(f"  {i:2d}. {combo}")
        return

    print(f"⚙️  配置: 每个关键词{args.max_notes}个帖子, 每个帖子{args.max_comments}条评论")
    print(f"🔄 分批: 每批{args.batch_size}个任务")
    print()

    # 执行爬虫
    if args.mode == "test":
        run_crawler_task(combinations[0], 5, 2)  # 测试模式用更少的限制
    else:
        run_batch_crawl(combinations, args.batch_size, args.max_notes, args.max_comments)


if __name__ == "__main__":
    main()