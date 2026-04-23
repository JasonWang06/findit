#!/usr/bin/env python3
"""
导入MediaCrawler爬取的数据到FindIt数据库

MediaCrawler会爬取数据并保存为JSONL格式
这个脚本会将数据导入到FindIt的SQLite数据库
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from findit.db.database import Database


def import_jsonl_to_db(jsonl_file: Path, db: Database, source_type: str = "post"):
    """导入JSONL文件到数据库

    Args:
        jsonl_file: JSONL文件路径
        db: 数据库实例
        source_type: "post" 或 "comment"
    """
    print(f"📄 导入文件: {jsonl_file.name}")
    print(f"📏 文件大小: {jsonl_file.stat().st_size / 1024:.1f} KB")

    imported_count = 0
    skipped_count = 0

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                # 根据类型处理数据
                if source_type == "post":
                    success = import_post(data, db)
                elif source_type == "comment":
                    success = import_comment(data, db)
                else:
                    print(f"⚠️  未知的类型: {source_type}")
                    break

                if success:
                    imported_count += 1
                else:
                    skipped_count += 1

                # 每100条显示进度
                if line_num % 100 == 0:
                    print(f"  进度: {line_num} 行, 导入: {imported_count}, 跳过: {skipped_count}")

            except json.JSONDecodeError as e:
                print(f"❌ 第{line_num}行JSON解析失败: {e}")
                skipped_count += 1
            except Exception as e:
                print(f"❌ 第{line_num}行处理失败: {e}")
                skipped_count += 1

    print(f"✅ 导入完成: {imported_count} 条, 跳过: {skipped_count} 条")
    return imported_count


def import_post(data: dict, db: Database) -> bool:
    """导入单条笔记"""
    try:
        # 先导入/更新作者信息（必须在post之前）
        author_data = {
            'id': data.get('user_id'),
            'nickname': data.get('nickname'),
            'avatar_url': data.get('avatar'),
            'ip_location': data.get('ip_location'),
            'updated_at': datetime.now().isoformat(),
        }
        db.upsert_author(author_data)

        # 然后导入笔记
        post_data = {
            'id': data.get('note_id'),  # 使用xhs的note_id作为主键
            'platform': 'xiaohongshu',
            'author_id': data.get('user_id'),  # xhs的user_id
            'content': data.get('desc') or data.get('title'),
            'image_urls': data.get('image_list') or '[]',
            'likes': parse_count(data.get('liked_count')),
            'comments_count': parse_count(data.get('comment_count')),
            'created_at': datetime.fromtimestamp(data.get('time', 0) / 1000).isoformat() if data.get('time') else None,
            'crawled_at': datetime.now().isoformat(),
            'post_url': data.get('note_url'),
            'source_type': 'post',  # xhs search results are posts
        }

        # 使用upsert方法（会自动处理重复）
        db.upsert_post(post_data)

        return True

    except Exception as e:
        print(f"⚠️  导入笔记失败 {data.get('note_id')}: {e}")
        return False


def import_comment(data: dict, db: Database) -> bool:
    """导入单条评论"""
    try:
        # 先导入/更新作者信息
        author_data = {
            'id': data.get('user_id'),
            'nickname': data.get('nickname'),
            'updated_at': datetime.now().isoformat(),
        }
        db.upsert_author(author_data)

        # 评论也作为post存储，但source_type为comment
        comment_data = {
            'id': data.get('comment_id'),
            'platform': 'xiaohongshu',
            'author_id': data.get('user_id'),
            'content': data.get('comment_content'),
            'image_urls': '[]',
            'likes': parse_count(data.get('sub_comment_count', 0)),
            'comments_count': 0,
            'created_at': datetime.now().isoformat(),
            'crawled_at': datetime.now().isoformat(),
            'post_url': data.get('note_url'),
            'source_type': 'comment',  # 标记为评论
        }

        # 使用upsert方法
        db.upsert_post(comment_data)

        return True

    except Exception as e:
        print(f"⚠️  导入评论失败 {data.get('comment_id')}: {e}")
        return False


def parse_count(count_str: str) -> int:
    """解析数量字符串（如 "7.4万" -> 74000）"""
    if not count_str:
        return 0

    if isinstance(count_str, int):
        return count_str

    if isinstance(count_str, str):
        count_str = count_str.strip()

        if '万' in count_str:
            # 处理 "7.4万" -> 7400
            number = count_str.replace('万', '').strip()
            try:
                return int(float(number) * 10000)
            except ValueError:
                return 0
        else:
            # 直接是数字
            try:
                return int(count_str)
            except ValueError:
                return 0

    return 0


def import_all_mediacrawler_data():
    """导入所有MediaCrawler数据"""
    print("🚀 导入MediaCrawler数据到FindIt")
    print("="*60)

    # 初始化数据库
    db = Database()
    print(f"✅ 数据库已连接")

    # MediaCrawler数据路径
    mediacrawler_data = Path.home() / "Desktop" / "MediaCrawler" / "data" / "xhs" / "jsonl"

    if not mediacrawler_data.exists():
        print(f"❌ MediaCrawler数据目录不存在: {mediacrawler_data}")
        return

    # 获取所有JSONL文件
    jsonl_files = sorted(mediacrawler_data.glob("*.jsonl"), reverse=True)

    if not jsonl_files:
        print(f"❌ 没有找到JSONL文件")
        return

    print(f"📁 找到 {len(jsonl_files)} 个JSONL文件")

    # 分类文件
    post_files = [f for f in jsonl_files if 'search_contents' in f.name]
    comment_files = [f for f in jsonl_files if 'search_comments' in f.name]

    print(f"  📝 笔记文件: {len(post_files)}")
    print(f"  💬 评论文件: {len(comment_files)}")

    total_imported = 0

    # 导入笔记（最新的5个文件）
    print(f"\n{'='*60}")
    print("📝 导入笔记")
    print(f"{'='*60}")

    for post_file in post_files[:5]:  # 只导入最新的5个文件
        count = import_jsonl_to_db(post_file, db, source_type="post")
        total_imported += count

    # 导入评论（最新的5个文件）
    print(f"\n{'='*60}")
    print("💬 导入评论")
    print(f"{'='*60}")

    for comment_file in comment_files[:5]:  # 只导入最新的5个文件
        count = import_jsonl_to_db(comment_file, db, source_type="comment")
        total_imported += count

    # 显示统计
    print(f"\n{'='*60}")
    print("📊 导入完成统计")
    print(f"{'='*60}")

    stats = db.get_stats()
    print(f"总笔记数: {stats.get('total_posts', 0)}")
    print(f"总评论数: {stats.get('total_comments', 0)}")
    print(f"总作者数: {stats.get('total_authors', 0)}")
    print(f"本次导入: {total_imported} 条")

    print(f"\n✅ 数据导入完成！")
    print(f"\n下一步:")
    print(f"1. 查看数据: sqlite3 {Path(__file__).parent.parent / 'data' / 'findit.db'}")
    print(f"2. 开始AI标签提取: python3 scripts/extract_tags.py")


def main():
    import_all_mediacrawler_data()


if __name__ == "__main__":
    main()
