#!/usr/bin/env python3
"""
从数据库帖子中提取用户画像
更新数据库中的用户标签
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from findit.data.profile_extractor import ProfileExtractor
from findit.db.database import Database
from datetime import datetime
import json


def extract_and_update_profiles(limit: int = 100, confidence_threshold: float = 0.3):
    """
    提取并更新用户画像

    Args:
        limit: 处理帖子数量限制
        confidence_threshold: 最低可信度阈值
    """
    db = Database()
    extractor = ProfileExtractor()

    print(f"🚀 开始提取用户画像")
    print(f"📊 处理帖子数量: {limit}")
    print(f"🎯 最低可信度: {confidence_threshold:.0%}")
    print("=" * 60)

    # 获取需要处理的帖子（优先选择交友相关的）
    posts = db.get_posts_for_profile_extraction(limit)

    print(f"📝 找到 {len(posts)} 条待处理帖子\n")

    stats = {
        'total': len(posts),
        'processed': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'failed': 0,
    }

    for i, post in enumerate(posts, 1):
        post_id = post['id']
        content = post['content']
        author_id = post['author_id']

        try:
            # 提取画像
            profile = extractor.extract_profile(
                content,
                post_id=post_id
            )

            # 计算可信度
            confidence = extractor.calculate_confidence(profile)

            # 过滤低质量结果
            if confidence < confidence_threshold:
                stats['low_confidence'] += 1
                print(f"⏭️  [{i}/{len(posts)}] 低可信度 ({confidence:.0%}) - 跳过")
                continue

            # 更新数据库
            success = db.update_user_profile(
                author_id=author_id,
                profile=profile,
                confidence=confidence,
                source_post_id=post_id
            )

            if success:
                stats['processed'] += 1

                if confidence >= 0.7:
                    stats['high_confidence'] += 1
                    print(f"✅ [{i}/{len(posts)}] 高可信度 ({confidence:.0%}) - 年龄:{profile['age']} 性别:{profile['gender']} 地点:{profile['locations']}")
                elif confidence >= 0.5:
                    stats['medium_confidence'] += 1
                    print(f"✅ [{i}/{len(posts)}] 中等可信度 ({confidence:.0%}) - 年龄:{profile['age']} 性别:{profile['gender']}")
                else:
                    print(f"✅ [{i}/{len(posts)}] 低可信度 ({confidence:.0%})")
            else:
                stats['failed'] += 1
                print(f"❌ [{i}/{len(posts)}] 数据库更新失败")

        except Exception as e:
            stats['failed'] += 1
            print(f"❌ [{i}/{len(posts)}] 处理失败: {e}")

    # 输出统计
    print("\n" + "=" * 60)
    print("📊 处理结果统计:")
    print(f"  总计处理: {stats['total']} 条")
    print(f"  成功更新: {stats['processed']} 条")
    print(f"    ├─ 高可信度 (≥70%): {stats['high_confidence']} 条")
    print(f"    ├─ 中等可信度 (50-70%): {stats['medium_confidence']} 条")
    print(f"    └─ 低可信度 (30-50%): {stats['low_confidence']} 条")
    print(f"  失败: {stats['failed']} 条")
    print("=" * 60)

    # 查看数据库状态
    print("\n📈 数据库用户画像状态:")
    db.print_profile_statistics()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='提取用户画像')
    parser.add_argument('--limit', type=int, default=100,
                       help='处理帖子数量 (默认: 100)')
    parser.add_argument('--confidence', type=float, default=0.3,
                       help='最低可信度阈值 (默认: 0.3)')

    args = parser.parse_args()

    extract_and_update_profiles(
        limit=args.limit,
        confidence_threshold=args.confidence
    )


if __name__ == "__main__":
    main()
