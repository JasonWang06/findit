#!/usr/bin/env python3
"""
查询和展示用户画像
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from findit.db.database import Database
import json


def display_profile(profile: dict):
    """美化显示单个用户画像"""
    print(f"\n{'='*60}")
    print(f"👤 用户ID: {profile['author_id']}")
    print(f"📊 可信度: {profile['confidence_score']:.0%}")

    # 基本信息
    if profile.get('age'):
        gender_emoji = "👩" if profile.get('gender') == 'female' else "👨" if profile.get('gender') == 'male' else "❓"
        print(f"{gender_emoji} {profile['age']}岁  {profile.get('gender') or '性别未知'}")

    if profile.get('locations'):
        locations = json.loads(profile['locations']) if isinstance(profile['locations'], str) else profile['locations']
        if locations:
            print(f"📍 地点: {', '.join(locations)}")

    if profile.get('occupations'):
        occupations = json.loads(profile['occupations']) if isinstance(profile['occupations'], str) else profile['occupations']
        if occupations:
            print(f"💼 职业: {', '.join(occupations)}")

    if profile.get('height'):
        print(f"📏 身高: {profile['height']}cm")

    if profile.get('education'):
        education = json.loads(profile['education']) if isinstance(profile['education'], str) else profile['education']
        if education:
            print(f"🎓 学历: {', '.join(education)}")

    if profile.get('status'):
        status_map = {
            'single': '单身',
            'looking': '寻找中',
            'taken': '有对象',
            'dating': '恋爱中'
        }
        print(f"💕 状态: {status_map.get(profile['status'], profile['status'])}")

    if profile.get('personality'):
        personality = json.loads(profile['personality']) if isinstance(profile['personality'], str) else profile['personality']
        if personality:
            print(f"🌟 性格: {', '.join(personality)}")

    if profile.get('interests'):
        interests = json.loads(profile['interests']) if isinstance(profile['interests'], str) else profile['interests']
        if interests:
            print(f"❤️ 兴趣: {', '.join(interests)}")

    if profile.get('requirements'):
        requirements = json.loads(profile['requirements']) if isinstance(profile['requirements'], str) else profile['requirements']
        if requirements:
            print(f"🎯 要求: {json.dumps(requirements, ensure_ascii=False)}")

    if profile.get('raw_text_summary'):
        print(f"📝 原文: {profile['raw_text_summary'][:100]}...")

    print(f"{'='*60}")


def search_interactive():
    """交互式搜索"""
    db = Database()

    print("🔍 FindIt 用户画像搜索")
    print("="*60)

    filters = {}

    # 性别筛选
    gender_input = input("性别 (male/female/回车跳过): ").strip()
    if gender_input in ['male', 'female']:
        filters['gender'] = gender_input

    # 年龄筛选
    age_input = input("年龄范围 (如: 25-30/回车跳过): ").strip()
    if age_input:
        try:
            if '-' in age_input:
                min_age, max_age = age_input.split('-')
                filters['min_age'] = int(min_age)
                filters['max_age'] = int(max_age)
            else:
                filters['min_age'] = int(age_input)
                filters['max_age'] = int(age_input) + 5
        except:
            print("⚠️ 年龄格式错误，已忽略")

    # 地点筛选
    location_input = input("地点 (如: 深圳/回车跳过): ").strip()
    if location_input:
        filters['location'] = location_input

    # 最低可信度
    confidence_input = input("最低可信度 (如: 0.7/回车跳过): ").strip()
    if confidence_input:
        try:
            filters['min_confidence'] = float(confidence_input)
        except:
            print("⚠️ 可信度格式错误，已忽略")

    print(f"\n🔍 搜索条件: {json.dumps(filters, ensure_ascii=False)}")
    print("="*60)

    results = db.search_profiles(**filters)

    print(f"\n找到 {len(results)} 个匹配用户\n")

    for i, profile in enumerate(results, 1):
        display_profile(profile)
        if i < len(results):
            input("\n按回车查看下一个...")

    if len(results) == 0:
        print("❌ 没有找到匹配的用户")
        print("💡 建议：")
        print("  1. 降低可信度要求")
        print("  2. 扩大年龄范围")
        print("  3. 尝试其他城市")


def show_statistics():
    """显示统计信息"""
    db = Database()

    print("📊 FindIt 用户画像统计")
    print("="*60)

    stats = db.print_profile_statistics()

    print(f"\n🔍 热门查询示例:")
    print(f"  - 深圳女生: {len(db.search_profiles(location='深圳', gender='female'))} 人")
    print(f" - 28-32岁: {len(db.search_profiles(min_age=28, max_age=32))} 人")
    print(f"  - 高可信度单身: {len(db.search_profiles(min_confidence=0.7, status='single'))} 人")


def show_high_quality_profiles(limit=10):
    """显示高质量用户画像"""
    db = Database()

    print(f"🌟 高质量用户画像 (Top {limit})")
    print("="*60)

    profiles = db.search_profiles(min_confidence=0.7)

    for i, profile in enumerate(profiles[:limit], 1):
        display_profile(profile)
        if i < len(profiles[:limit]):
            input("\n按回车查看下一个...")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='查询用户画像')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 交互式搜索
    subparsers.add_parser('search', help='交互式搜索')

    # 统计信息
    subparsers.add_parser('stats', help='显示统计信息')

    # 高质量用户
    high_parser = subparsers.add_parser('high-quality', help='显示高质量用户')
    high_parser.add_argument('--limit', type=int, default=10, help='显示数量')

    args = parser.parse_args()

    if args.command == 'search':
        search_interactive()
    elif args.command == 'stats':
        show_statistics()
    elif args.command == 'high-quality':
        show_high_quality_profiles(args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
