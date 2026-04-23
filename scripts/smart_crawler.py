#!/usr/bin/env python3
"""智能爬虫调度系统 - 根据策略自动安排爬虫任务"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ===== 市场和关键词配置 =====

CITIES_TIER_1 = {
    "北京": ["找对象", "相亲", "脱单", "交友", "CPDD"],
    "上海": ["找对象", "相亲", "脱单", "交友", "CPDD"],
    "深圳": ["找对象", "相亲", "脱单", "交友", "CPDD"],
    "广州": ["找对象", "相亲", "脱单", "交友", "CPDD"],
}

CITIES_TIER_1_5 = {
    "杭州": ["找对象", "相亲", "脱单"],
    "成都": ["找对象", "相亲", "脱单"],
    "南京": ["找对象", "相亲", "交友"],
    "武汉": ["找对象", "相亲", "脱单"],
    "西安": ["找对象", "相亲", "交友"],
    "苏州": ["找对象", "相亲", "CPDD"],
    "天津": ["找对象", "相亲", "脱单"],
    "重庆": ["找对象", "相亲", "交友"],
    "长沙": ["找对象", "相亲", "CPDD"],
    "青岛": ["找对象", "相亲", "交友"],
}

CITIES_INTERNATIONAL = {
    "香港": ["找对象", "相亲", "脱单"],
    "新加坡": ["找对象", "相亲", "交友"],
    "东京": ["找对象", "相亲", "脱单"],
}

KEYWORD_DIRECT = ["找对象", "相亲", "交友", "脱单", "征婚"]
KEYWORD_VARIATIONS = ["找男友", "找女友", "蹲男友", "蹲女友", "CPDD"]
KEYWORD_STATUS = ["单身", "单身交友", "母胎单身"]
KEYWORD_PROFESSION = ["程序员找对象", "金融女脱单", "教师相亲", "医生交友"]

# ===== 爬虫策略配置 =====

CRAWL_SCHEDULE = {
    "daily": {
        "周一": (["北京", "上海"], ["找对象", "相亲"]),
        "周二": (["深圳", "广州"], ["找对象", "相亲"]),
        "周三": (["杭州", "成都"], ["找对象", "相亲"]),
        "周四": (["南京", "武汉"], ["找对象", "相亲"]),
        "周五": (["香港", "新加坡"], ["找对象", "相亲"]),
        "周六": (["深圳", "上海"], ["CPDD", "脱单"]),  # 周末年轻用户活跃
        "周日": (["北京", "广州"], ["CPDD", "脱单"]),
    },
    "weekly": {
        "周日": {
            "tier_1_full": list(CITIES_TIER_1.keys()),
            "keywords": ["找对象", "相亲"]
        },
        "周三": {
            "tier_1_5_full": list(CITIES_TIER_1_5.keys()),
            "keywords": ["找对象", "相亲"]
        }
    }
}


def get_current_schedule():
    """根据当前时间获取应该爬取的城市和关键词"""
    now = datetime.now()
    weekday = now.strftime("%A")  # 英文星期名

    # 日常爬取 - 使用英文字段名
    weekday_map = {
        "Monday": "周一",
        "Tuesday": "周二",
        "Wednesday": "周三",
        "Thursday": "周四",
        "Friday": "周五",
        "Saturday": "周六",
        "Sunday": "周日"
    }

    chinese_weekday = weekday_map.get(weekday, "")

    # 日常爬取
    if chinese_weekday in CRAWL_SCHEDULE["daily"]:
        cities, keywords = CRAWL_SCHEDULE["daily"][chinese_weekday]
        return cities, keywords, "daily"

    # 每周深度爬取
    if chinese_weekday in CRAWL_SCHEDULE["weekly"]:
        schedule = CRAWL_SCHEDULE["weekly"][chinese_weekday]
        return schedule.get("tier_1_full", schedule.get("tier_1_5_full", [])), \
               schedule["keywords"], "weekly"

    return [], [], "none"


def generate_keywords_combinations(cities, keywords):
    """生成城市+关键词组合"""
    combinations = []
    for city in cities:
        for keyword in keywords:
            combinations.append(f"{city}{keyword}")
    return combinations


def run_crawler(keywords, max_notes=10, max_comments=5):
    """执行爬虫任务"""
    print(f"🚀 开始爬取: {keywords}")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    keywords_str = ",".join(keywords) if isinstance(keywords, list) else keywords

    cmd = [
        "python", "main.py",
        "--platform", "xhs",
        "--lt", "cookie",
        "--type", "search",
        "--keywords", keywords_str,
    ]

    # 添加评论限制（如果需要）
    if max_comments > 0:
        cmd.extend(["--max_comments_count_single_no", str(max_comments)])

    try:
        result = subprocess.run(
            cmd,
            cwd="~/Desktop/MediaCrawler",
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )

        if result.returncode == 0:
            print(f"✅ 爬取成功: {keywords}")
            return True
        else:
            print(f"❌ 爬取失败: {keywords}")
            print(f"错误: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ 爬取超时: {keywords}")
        return False
    except Exception as e:
        print(f"❌ 爬取异常: {keywords}, 错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="智能爬虫调度系统")
    parser.add_argument("--mode", choices=["auto", "manual", "test"], default="auto",
                       help="运行模式: auto(自动调度), manual(手动指定), test(测试)")
    parser.add_argument("--cities", nargs="+", help="手动指定城市")
    parser.add_argument("--keywords", nargs="+", help="手动指定关键词")
    parser.add_argument("--max-notes", type=int, default=10, help="每个关键词最大帖子数")
    parser.add_argument("--max-comments", type=int, default=5, help="每个帖子最大评论数")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要执行的任务，不实际运行")

    args = parser.parse_args()

    print("🤖 FindIt 智能爬虫调度系统")
    print("=" * 50)

    if args.mode == "auto":
        # 自动调度模式
        cities, keywords, schedule_type = get_current_schedule()

        if not cities:
            print("⚠️  当前时间没有安排爬取任务")
            return

        combinations = generate_keywords_combinations(cities, keywords)
        print(f"📋 调度模式: {schedule_type}")
        print(f"🏙️  城市: {', '.join(cities)}")
        print(f"🔑 关键词: {', '.join(keywords)}")
        print(f"📝 组合数量: {len(combinations)}")

        if args.dry_run:
            print("\n🔍 将要执行的任务:")
            for i, combo in enumerate(combinations, 1):
                print(f"  {i}. {combo}")
            return

        # 执行爬取
        success_count = 0
        for combo in combinations:
            if run_crawler([combo], args.max_notes, args.max_comments):
                success_count += 1

        print(f"\n📊 执行结果: {success_count}/{len(combinations)} 成功")

    elif args.mode == "manual":
        # 手动模式
        if not args.cities or not args.keywords:
            print("❌ 手动模式需要指定 --cities 和 --keywords")
            return

        combinations = generate_keywords_combinations(args.cities, args.keywords)
        print(f"📝 手动模式")
        print(f"🏙️  城市: {', '.join(args.cities)}")
        print(f"🔑 关键词: {', '.join(args.keywords)}")
        print(f"📝 组合数量: {len(combinations)}")

        if args.dry_run:
            print("\n🔍 将要执行的任务:")
            for i, combo in enumerate(combinations, 1):
                print(f"  {i}. {combo}")
            return

        # 执行爬取
        success_count = 0
        for combo in combinations:
            if run_crawler([combo], args.max_notes, args.max_comments):
                success_count += 1

        print(f"\n📊 执行结果: {success_count}/{len(combinations)} 成功")

    elif args.mode == "test":
        # 测试模式 - 快速验证
        print("🧪 测试模式 - 单个关键词快速测试")
        test_keywords = ["深圳找对象"]

        if args.dry_run:
            print(f"🔍 测试关键词: {test_keywords}")
        else:
            run_crawler(test_keywords, max_notes=5, max_comments=2)


if __name__ == "__main__":
    main()