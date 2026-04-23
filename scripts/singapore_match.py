#!/usr/bin/env python3
"""为您的个人背景定制的新加坡爬虫和匹配系统"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from findit.db import Database

# 您的个人资料
YOUR_PROFILE = {
    'age': 31,
    'education': 'NYU本科',
    'job': '币安产品经理',
    'company': 'Binance',
    'interests': ['DOM', '��球'],
    'location_preference': ['新加坡', '香港', '海外'],
    'target_age_range': (25, 35),
    'target_keywords': [
        '新加坡', '留学', '海外', '海归', 'NYU',
        '网球', '运动', '产品经理', '金融',
        '硕士', '本科', '学历'
    ]
}

def crawl_singapore_data():
    """爬取新加坡相关数据"""
    print("🇸🇬 开始爬取新加坡相关数据...")
    print("关键词: 新加坡找对象,新加坡相亲,新加坡留学")
    print("开始时间:", datetime.now().strftime('%H:%M:%S'))

    start_time = datetime.now()

    # 爬取新加坡相关的关键词
    keywords = ["新加坡找对象", "新加坡相亲", "新加坡留学"]

    for keyword in keywords:
        print(f"\n🔍 爬取关键词: {keyword}")
        cmd = [
            "python", "main.py",
            "--platform", "xhs",
            "--lt", "cookie",
            "--type", "search",
            "--keywords", keyword,
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd="~/Desktop/MediaCrawler",
                capture_output=True,
                text=True,
                timeout=180  # 3分钟超时
            )

            if result.returncode == 0:
                print(f"✅ {keyword} 爬取成功")
            else:
                print(f"❌ {keyword} 爬取失败")

        except subprocess.TimeoutExpired:
            print(f"⏰ {keyword} 爬取超时")
        except Exception as e:
            print(f"❌ {keyword} 爬取异常: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n✅ 新加坡数据爬取完成")
    print(f"总耗时: {duration}秒 ({duration/60:.1f}分钟)")
    print(f"结束时间: {end_time.strftime('%H:%M:%S')}")

def find_best_matches():
    """基于您的背景找到最佳匹配"""
    print("\n🎯 基于您的背景寻找最佳匹配...")
    print("=" * 60)
    print("您的背景: 31岁, NYU本科, 币安产品经理")
    print("兴趣爱好: DOM, 网球")
    print("=" * 60)

    db = Database()

    with db._conn() as conn:
        # 查找最匹配的用户
        best_matches = conn.execute('''
            SELECT p.id, p.content, p.post_url, a.nickname, a.ip_location,
                   a.bio, a.followers, a.likes_collected
            FROM posts p
            JOIN authors a ON p.author_id = a.id
            WHERE a.is_filtered_out = 0
            ORDER BY
                CASE
                    WHEN p.content LIKE '%新加坡%' THEN 10
                    WHEN a.ip_location LIKE '%新加坡%' THEN 10
                    WHEN p.content LIKE '%香港%' THEN 8
                    WHEN p.content LIKE '%nyu%' OR p.content LIKE '%NYU%' THEN 9
                    WHEN p.content LIKE '%留学%' OR p.content LIKE '%海归%' THEN 8
                    WHEN p.content LIKE '%网球%' THEN 7
                    WHEN p.content LIKE '%产品经理%' OR p.content LIKE '%互联网%' THEN 6
                    WHEN p.content LIKE '%金融%' OR p.content LIKE '%币%' THEN 5
                    WHEN p.content LIKE '%硕士%' OR p.content LIKE '%本科%' THEN 4
                    WHEN p.content LIKE '%运动%' OR p.content LIKE '%健身%' THEN 3
                    ELSE 0
                END DESC,
                a.followers DESC
            LIMIT 10
        ''').fetchall()

        print(f"\n📊 找到 {len(best_matches)} 个高质量匹配:\n")

        for i, user in enumerate(best_matches, 1):
            content = user['content'][:100] + '...' if len(user['content']) > 100 else user['content']
            bio = user['bio'][:80] + '...' if user['bio'] and len(user['bio']) > 80 else (user['bio'] or '无')

            # 计算匹配分数
            score = 0
            reasons = []

            if '新加坡' in user['content'] or '新加坡' in user['ip_location']:
                score += 25
                reasons.append('🇸🇬新加坡相关')

            if 'nyu' in user['content'].lower() or 'NYU' in user['content']:
                score += 30
                reasons.append('🎓 NYU校友')

            if any(kw in user['content'] for kw in ['留学', '海归', '海外']):
                score += 20
                reasons.append('🌍 海外背景')

            if any(kw in user['content'] for kw in ['网球', '运动']):
                score += 15
                reasons.append('🎾 运动爱好')

            if any(kw in user['content'] for kw in ['产品经理', '互联网', '金融']):
                score += 15
                reasons.append('💼 职业相关')

            if any(kw in user['content'] for kw in ['硕士', '本科']):
                score += 10
                reasons.append('🎓 学历背景')

            if user['followers'] and user['followers'] > 100:
                score += 10
                reasons.append('✨ 账号质量')

            print(f"{i}. {user['nickname']} ({user['ip_location']})")
            if score > 0:
                print(f"   🎯 匹配度: {score}% - {', '.join(reasons)}")

            print(f"   📝 简介: {bio}")
            print(f"   💬 内容: {content}")
            print(f"   👥 粉丝: {user['followers']}, 获赞: {user['likes_collected']}")
            print(f"   🔗 链接: {user['post_url']}")
            print()

def main():
    import argparse

    parser = argparse.ArgumentParser(description="新加坡数据爬取和智能匹配")
    parser.add_argument("--mode", choices=["crawl", "match", "both"], default="both",
                       help="模式: crawl(只爬取), match(只匹配), both(爬取+匹配)")

    args = parser.parse_args()

    print("🤖 FindIt 新加坡智能匹配系统")
    print("=" * 60)

    if args.mode in ["crawl", "both"]:
        crawl_singapore_data()

        # 导入新数据
        print("\n📥 导入新数据到数据库...")
        subprocess.run([
            "python3", "scripts/import_mediacrawler.py",
            "~/Desktop/MediaCrawler/data/xhs/jsonl"
        ], cwd="/Users/json/Desktop/findit")

    if args.mode in ["match", "both"]:
        find_best_matches()

    print("\n" + "=" * 60)
    print("✅ 处理完成!")

if __name__ == "__main__":
    main()