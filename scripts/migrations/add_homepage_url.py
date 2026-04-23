#!/usr/bin/env python3
"""添加用户主页链接字段到authors表"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from findit.db import Database

def migrate():
    """执行数据库迁移"""
    print("🔄 开始数据库迁移：添加用户主页链接字段")

    db = Database()

    with db._conn() as conn:
        # 检查字段是否已存在
        result = conn.execute("PRAGMA table_info(authors)").fetchall()
        existing_columns = [row['name'] for row in result]

        if 'homepage_url' in existing_columns:
            print("✅ homepage_url 字段已存在，无需迁移")
            return

        # 添加字段
        print("📝 添加 homepage_url 字段到 authors 表")
        conn.execute("ALTER TABLE authors ADD COLUMN homepage_url TEXT")

        # 尝试从现有数据中提取用户主页链接
        print("🔍 尝试从现有数据中提取用户主页链接")

        # 小红书用户主页格式：https://www.xiaohongshu.com/user/profile/{user_id}
        authors = conn.execute('''
            SELECT id, nickname
            FROM authors
            WHERE homepage_url IS NULL OR homepage_url = ''
        ''').fetchall()

        print(f"📊 找到 {len(authors)} 个需要更新的作者")

        updated_count = 0
        for author in authors:
            author_id = author['id']
            # 生成用户主页链接
            homepage_url = f"https://www.xiaohongshu.com/user/profile/{author_id}"
            conn.execute('''
                UPDATE authors
                SET homepage_url = ?
                WHERE id = ?
            ''', (homepage_url, author_id))
            updated_count += 1

        print(f"✅ 成功更新 {updated_count} 个作者的主页链接")

    print("🎉 数据库迁移完成！")

if __name__ == "__main__":
    migrate()
