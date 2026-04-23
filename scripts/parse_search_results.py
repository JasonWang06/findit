#!/usr/bin/env python3
"""
解析搜索页面的JSON数据

从HTML中提取 __INITIAL_STATE__ 并解析
"""

import json
import re
from pathlib import Path


def parse_search_html(html_file):
    """解析搜索结果HTML"""
    print(f"📄 解析: {html_file.name}")

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 提取 JSON
    pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>'
    matches = re.findall(pattern, html_content, re.DOTALL)

    if not matches:
        print("❌ 没有找到 __INITIAL_STATE__")
        return None

    try:
        # JSON可能不完整，尝试修复
        json_str = matches[0]

        # 查找完整的JSON对象（匹配花括号）
        # 小红书的JSON可能很长，需要找到完整的对象
        depth = 0
        end_pos = 0
        for i, char in enumerate(json_str):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break

        if end_pos > 0:
            json_str = json_str[:end_pos]

        data = json.loads(json_str)
        print("✅ JSON解析成功")

        # 探索数据结构
        explore_data_structure(data)

        return data

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(f"尝试解析的前1000字符: {json_str[:1000]}")

        # 尝试直接从HTML中搜索笔记相关数据
        search_notes_in_html(html_content)

        return None


def explore_data_structure(data, path="", max_depth=3, current_depth=0):
    """递归探索数据结构"""
    if current_depth >= max_depth:
        return

    if isinstance(data, dict):
        for key, value in list(data.items())[:10]:  # 只看前10个key
            current_path = f"{path}.{key}" if path else key

            # 查找包含笔记的关键字
            if any(keyword in key.lower() for keyword in ['note', 'post', 'item', 'data', 'list', 'result']):
                print(f"  📂 {current_path}")

                if isinstance(value, list):
                    print(f"     类型: list, 长度: {len(value)}")
                    if len(value) > 0:
                        print(f"     第一项类型: {type(value[0])}")
                        if isinstance(value[0], dict):
                            print(f"     第一项keys: {list(value[0].keys())[:10]}")

                            # 如果看起来像笔记，显示一个示例
                            if any(k in value[0] for k in ['id', 'title', 'desc', 'noteId']):
                                print(f"     ✅ 看起来像笔记数据！")
                                print(f"     示例: {json.dumps(value[0], ensure_ascii=False)[:200]}")
                elif isinstance(value, dict):
                    print(f"     类型: dict, keys: {list(value.keys())[:10]}")

            explore_data_structure(value, current_path, max_depth, current_depth + 1)

    elif isinstance(data, list) and len(data) > 0:
        current_path = f"{path}[0]"
        explore_data_structure(data[0], current_path, max_depth, current_depth + 1)


def search_notes_in_html(html_content):
    """在HTML中直接搜索笔记相关数据"""
    print("\n🔍 在HTML中搜索笔记数据...")

    # 搜索可能包含笔记的JSON片段
    patterns = [
        r'"noteId"\s*:\s*"([^"]+)"',
        r'"title"\s*:\s*"([^"]{10,})"',  # 标题至少10个字符
        r'"desc"\s*:\s*"([^"]{20,})"',  # 描述至少20个字符
        r'"nickname"\s*:\s*"([^"]+)"',  # 用户昵称
    ]

    results = {}
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            name = pattern.split('"')[1].split('"')[0]
            results[name] = matches
            print(f"  ✅ 找到 {len(matches)} 个 {name}")

            # 显示前3个
            for i, match in enumerate(matches[:3], 1):
                print(f"     {i}. {match[:100]}")

    return results


def extract_all_test_pages():
    """解析所有测试页面"""
    test_pages_dir = Path(__file__).parent.parent / "data" / "test_pages"
    html_files = sorted(test_pages_dir.glob("test_*.html"))

    print(f"找到 {len(html_files)} 个测试页面")

    for html_file in html_files:
        print(f"\n{'='*60}")
        data = parse_search_html(html_file)

        if data:
            # 尝试提取笔记数据
            notes = extract_notes_from_data(data)
            if notes:
                print(f"\n✅ 成功提取 {len(notes)} 条笔记")
                save_notes(notes, html_file.stem)


def extract_notes_from_data(data):
    """从数据中提取笔记"""
    notes = []

    # 递归搜索可能的笔记数组
    def find_notes(obj, path=""):
        if isinstance(obj, dict):
            # 检查是否看起来像笔记对象
            if any(key in obj for key in ['noteId', 'note_card', 'title', 'desc']):
                if 'noteId' in obj or 'id' in obj:
                    notes.append(obj)

            # 递归搜索
            for key, value in obj.items():
                find_notes(value, f"{path}.{key}")

        elif isinstance(obj, list):
            for item in obj:
                find_notes(item, path)

    find_notes(data)
    return notes


def save_notes(notes, prefix):
    """保存笔记数据"""
    output_file = Path(__file__).parent.parent / "data" / f"extracted_{prefix}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

    print(f"💾 保存到: {output_file}")

    # 显示统计
    print(f"\n📊 笔记统计:")
    print(f"  总数: {len(notes)}")

    if notes:
        # 统计字段
        all_keys = set()
        for note in notes:
            all_keys.update(note.keys())

        print(f"  字段: {list(all_keys)}")

        # 显示示例
        print(f"\n📝 示例笔记:")
        print(f"  {json.dumps(notes[0], ensure_ascii=False, indent=2)[:500]}")


def main():
    print("🚀 解析搜索结果")
    print("="*60)

    extract_all_test_pages()


if __name__ == "__main__":
    main()
