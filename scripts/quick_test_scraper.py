#!/usr/bin/env python3
"""
快速测试爬虫 - 提取真实数据
"""

import json
import re
from pathlib import Path
from datetime import datetime


def extract_notes_from_html(html_file):
    """从HTML文件中提取笔记数据"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 提取 __INITIAL_STATE__
    pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>'
    matches = re.findall(pattern, html_content, re.DOTALL)

    if not matches:
        print("❌ 没有找到 __INITIAL_STATE__")
        return []

    try:
        data = json.loads(matches[0])
        print("✅ 成功解析 JSON")

        # 导航到笔记数据 - 路径可能不同，需要探索
        # 常见路径: search -> notes 或类似
        print(f"📂 顶层keys: {list(data.keys())[:20]}")

        # 尝试不同路径
        possible_paths = [
            ['search', 'notes'],
            ['web', 'search', 'notes'],
            ['web', 'note', 'search', 'notes'],
            ['web', 'note', 'search', 'data'],
        ]

        notes_data = None
        for path in possible_paths:
            current = data
            path_str = " -> ".join(path)
            try:
                for key in path:
                    current = current[key]
                print(f"✅ 找到数据路径: {path_str}")
                notes_data = current
                break
            except (KeyError, TypeError):
                print(f"❌ 路径不存在: {path_str}")
                continue

        if notes_data:
            return parse_notes(notes_data)

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")

    return []


def parse_notes(notes_data):
    """解析笔记数据"""
    results = []

    # notes_data 可能是不同的结构
    if isinstance(notes_data, dict):
        # 可能包含 data, items 等字段
        for key in ['data', 'items', 'notes', 'list']:
            if key in notes_data:
                notes_data = notes_data[key]
                break

    if isinstance(notes_data, list) and len(notes_data) > 0:
        print(f"✅ 找到 {len(notes_data)} 条笔记")

        for idx, note in enumerate(notes_data[:5], 1):  # 只显示前5条
            print(f"\n{'='*60}")
            print(f"笔记 {idx}")
            print(f"{'='*60}")

            # 尝试提取字段
            note_id = note.get('id') or note.get('noteId') or note.get('note_id')
            title = note.get('title') or note.get('noteCard', {}).get('title')
            desc = note.get('desc') or note.get('description')

            # 用户信息
            user = note.get('user', {})
            author = user.get('nickname') or user.get('name')

            # 互动数据
            interact = note.get('interactInfo') or note.get('interact_info', {})
            liked = interact.get('likedCount') or interact.get('liked_count')
            collected = interact.get('collectedCount') or interact.get('collected_count')

            print(f"ID: {note_id}")
            print(f"标题: {title}")
            print(f"描述: {desc[:100] if desc else 'N/A'}...")
            print(f"作者: {author}")
            print(f"点赞: {liked}")
            print(f"收藏: {collected}")

            results.append({
                'id': note_id,
                'title': title,
                'description': desc,
                'author': author,
                'liked_count': liked,
                'collected_count': collected,
            })

    return results


def main():
    print("🚀 快速测试爬虫")
    print("="*60)

    # 查找最新的HTML文件
    raw_pages_dir = Path(__file__).parent.parent / "data" / "raw_pages"
    html_files = sorted(raw_pages_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not html_files:
        print("❌ 没有找到HTML文件")
        return

    latest_file = html_files[0]
    print(f"📄 分析文件: {latest_file.name}")
    print(f"📅 修改时间: {datetime.fromtimestamp(latest_file.stat().st_mtime)}")
    print()

    notes = extract_notes_from_html(latest_file)

    if notes:
        print(f"\n✅ 成功提取 {len(notes)} 条笔记")
        print(f"{'='*60}")

        # 保存结果
        output_file = Path(__file__).parent.parent / "data" / "extracted_notes.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

        print(f"💾 保存到: {output_file}")
    else:
        print("❌ 没有提取到笔记数据")


if __name__ == "__main__":
    main()
