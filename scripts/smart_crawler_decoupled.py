#!/usr/bin/env python3
"""
智能爬虫 - 解耦版本，使用独立的cookie管理
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加父目录到path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.setup_cookie_manager import CookieManager

# 核心城市定义
CORE_CITIES = [
    "北京", "上海", "深圳", "广州",
    "杭州", "成都", "南京", "武汉",
    "香港", "新加坡"
]

# 关键词优先级
KEYWORDS_PRIORITY = [
    "找对象",      # 最直接，意图明确
    "相亲",        # 认真程度高
    "脱单",        # 紧迫感强
]

# 扩展关键词
KEYWORDS_EXTENDED = [
    "交友", "CPDD", "找男友", "找女友",
    "蹲男友", "蹲女友", "征婚", "��身交友"
]

ALL_KEYWORDS = KEYWORDS_PRIORITY + KEYWORDS_EXTENDED


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
                # 只组合有意义的组合
                if keyword in ["CPDD", "脱单", "找对象", "相亲", "交友"]:
                    combinations.append(f"{city}{keyword}")
                elif keyword in ["找男友", "蹲男友"]:
                    # 这些词一般不用于城市限定
                    if city in ["北京", "上海", "深圳", "广州"]:
                        combinations.append(f"{city}{keyword}")

    return combinations


def ensure_cookie_updated():
    """确保cookie已更新到MediaCrawler"""
    manager = CookieManager()
    cookie = manager.get_cookie()

    if not cookie:
        print("❌ 未找到有效的cookie")
        print("💡 解决方案：")
        print("   1. 手动更新cookie: python3 scripts/setup_cookie_manager.py save --cookie '你的cookie'")
        print("   2. 或设置环境变量: export XHS_COOKIE='你的cookie'")
        return False

    # 更新MediaCrawler配置
    cookie_str = cookie if isinstance(cookie, str) else cookie.get('cookie')
    manager.update_mediacrawler_config(cookie_str)
    return True


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

    # 注意：不使用--max_comments_count_single_no参数，使用配置默认值

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
            print(f"✅ {keywords_str} 完成")
            return True
        else:
            error_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
            print(f"❌ {keywords_str} 失败")
            print(f"   错误: {error_msg}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {keywords_str} 超时")
        return False
    except Exception as e:
        print(f"❌ {keywords_str} 异常: {e}")
        return False


def run_batch_crawl(combinations, batch_size=4, max_notes=10, max_comments=5):
    """分批执行爬虫任务"""
    total = len(combinations)
    success_count = 0

    print(f"\n📋 总任务数: {total}")
    print(f"🔄 分批执行: 每批 {batch_size} 个")
    print("=" * 50)

    for i in range(0, len(combinations), batch_size):
        batch = combinations[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(combinations) + batch_size - 1) // batch_size

        print(f"\n🔄 第 {batch_num}/{total_batches} 批:")

        for task in batch:
            if run_crawler_task(task, max_notes, max_comments):
                success_count += 1

        print(f"\n📊 进度: {min(i + batch_size, total)}/{total} 成功: {success_count}")

    print(f"\n🎉 完成: {success_count}/{total} 成功")
    return success_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FindIt 智能爬虫 - 解耦版本")
    parser.add_argument("--mode", choices=["full", "quick", "test", "custom"], default="full",
                       help="模式: full(全部城市+关键词), quick(核心城市+核心关键词), test(测试), custom(自定义)")
    parser.add_argument("--cities", nargs="+", help="自定义城市列表")
    parser.add_argument("--keywords", nargs="+", help="自定义关键词列表")
    parser.add_argument("--max-notes", type=int, default=10, help="每个关键词最大帖子数")
    parser.add_argument("--max-comments", type=int, default=5, help="每个帖子最大评论数")
    parser.add_argument("--batch-size", type=int, default=4, help="每批执行的任务数")
    parser.add_argument("--dry-run", action="store_true", help="只显示任务，不执行")
    parser.add_argument("--skip-cookie-check", action="store_true", help="跳过cookie检查（不推荐）")

    args = parser.parse_args()

    print("🤖 FindIt 智能爬虫系统 - 解耦版本")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查cookie（除非跳过）
    if not args.skip_cookie_check:
        print("\n🍪 Cookie状态检查...")
        if not ensure_cookie_updated():
            print("\n❌ Cookie检查失败，爬虫无法运行")
            print("💡 请先更新cookie后再试")
            return 1
    else:
        print("\n⚠️  跳过cookie检查（可能导致爬虫失败）")

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
            return 1
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
        return 0

    print(f"⚙️  配置: 每个关键词{args.max_notes}个帖子, 每个帖子{args.max_comments}条评论")
    print(f"🔄 分批: 每批{args.batch_size}个任务")
    print()

    # 执行爬虫
    if args.mode == "test":
        run_crawler_task(combinations[0], 5, 2)  # 测试模式用更少的限制
    else:
        run_batch_crawl(combinations, args.batch_size, args.max_notes, args.max_comments)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
