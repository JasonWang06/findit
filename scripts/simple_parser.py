#!/usr/bin/env python3
"""
简单HTML解析器 - 从已下载的HTML中提取信息
"""

import re
import json
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser


class NoteExtractor(HTMLParser):
    """自定义HTML解析器，提取笔记信息"""

    def __init__(self):
        super().__init__()
        self.notes = []
        self.current_note = {}
        self.in_note = False
        self.in_title = False
        self.in_text = False
        self.current_data = ""
        self.script_data = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # 检测笔记容器
        if tag in ['section', 'article']:
            if any(cls in attrs_dict.get('class', '') for cls in ['note', 'card', 'item']):
                self.in_note = True
                self.current_note = {'element': tag}

        # 检测标题
        if tag in ['h1', 'h2', 'h3'] or 'title' in attrs_dict.get('class', ''):
            self.in_title = True

        # 检测script标签（可能包含数据）
        if tag == 'script':
            self.in_text = True
            self.current_data = ""

    def handle_endtag(self, tag):
        if tag in ['section', 'article'] and self.in_note:
            if self.current_note:
                self.notes.append(self.current_note)
            self.in_note = False
            self.current_note = {}

        if tag in ['h1', 'h2', 'h3']:
            self.in_title = False

        if tag == 'script' and self.in_text:
            if self.current_data:
                self.script_data.append(self.current_data)
            self.in_text = False
            self.current_data = ""

    def handle_data(self, data):
        if self.in_note:
            if self.in_title and not self.current_note.get('title'):
                self.current_note['title'] = data.strip()
            elif not self.current_note.get('text'):
                self.current_note['text'] = data.strip()[:200]

        if self.in_text:
            self.current_data += data


def extract_from_html(html_file):
    """从HTML文件提取笔记"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 方法1: 使用HTML解析器
    parser = NoteExtractor()
    parser.feed(html_content)

    if parser.notes:
        print(f"✅ HTML解析器找到 {len(parser.notes)} 个笔记元素")
        return parser.notes

    # 方法2: 正则表达式提取链接
    print("📝 使用正则表达式提取链接...")

    # 提取笔记链接
    note_links = re.findall(r'https://www\.xiaohongshu\.com/explore/([a-zA-Z0-9]+)', html_content)
    print(f"✅ 找到 {len(note_links)} 个笔记链接")

    # 提取用户链接
    user_links = re.findall(r'https://www\.xiaohongshu\.com/user/profile/([a-zA-Z0-9]+)', html_content)
    print(f"✅ 找到 {len(user_links)} 个用户链接")

    # 方法3: 从script标签中提取JSON数据
    print("📝 从script标签提取数据...")
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)

    notes_data = []
    for script in parser.script_data:
        # 尝试解析JSON
        if 'noteId' in script or 'note_card' in script or 'interact_info' in script:
            try:
                # 尝试提取JSON对象
                json_match = re.search(r'\{[^{}]*"noteId"[^{}]*\}', script)
                if json_match:
                    try:
                        note_obj = json.loads(json_match.group(0))
                        notes_data.append(note_obj)
                    except:
                        pass
            except:
                pass

    if notes_data:
        print(f"✅ 从script提取了 {len(notes_data)} 条笔记数据")

    return {
        'note_links': note_links,
        'user_links': user_links,
        'notes_data': notes_data
    }


def find_json_in_html(html_content):
    """在HTML中查找JSON数据"""
    results = []

    # 查找所有的<script>标签内容
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)

    for idx, script in enumerate(scripts):
        # 查找包含特定关键词的script
        if any(keyword in script for keyword in ['noteId', 'note_card', 'interact_info', 'nickname']):
            print(f"\n📜 Script {idx + 1}:")

            # 尝试提取JSON片段
            # 查找 { "noteId": "..." } 这样的模式
            patterns = [
                r'\{[^{}]*"noteId"[^{}]*\}',
                r'\{[^{}]*"note_card"[^{}]*\}',
                r'\{[^{}]*"interact_info"[^{}]*\}',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, script)
                for match in matches[:5]:  # 只显示前5个
                    try:
                        data = json.loads(match)
                        print(f"  ✅ JSON: {json.dumps(data, ensure_ascii=False)[:200]}")
                        results.append(data)
                    except:
                        pass

    return results


def main():
    print("🚀 简单HTML解析器")
    print("="*60)

    # 查找最新的HTML文件
    raw_pages_dir = Path(__file__).parent.parent / "data" / "raw_pages"
    html_files = sorted(raw_pages_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not html_files:
        print("❌ 没有找到HTML文件")
        return

    latest_file = html_files[0]
    print(f"📄 分析文件: {latest_file.name}")
    print(f"📅 文件大小: {latest_file.stat().st_size:,} 字节")
    print()

    # 提取数据
    result = extract_from_html(latest_file)

    print(f"\n{'='*60}")
    print("📊 提取结果:")
    print(f"{'='*60}")
    print(f"笔记链接: {len(result['note_links'])}")
    print(f"用户链接: {len(result['user_links'])}")
    print(f"笔记数据: {len(result['notes_data'])}")

    # 显示一些示例
    if result['note_links']:
        print(f"\n📝 笔记链接示例:")
        for i, link in enumerate(result['note_links'][:5], 1):
            print(f"  {i}. https://www.xiaohongshu.com/explore/{link}")

    if result['user_links']:
        print(f"\n👤 用户链接示例:")
        for i, link in enumerate(result['user_links'][:5], 1):
            print(f"  {i}. https://www.xiaohongshu.com/user/profile/{link}")

    # 尝试从HTML中查找JSON数据
    with open(latest_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    print(f"\n🔍 查找JSON数据...")
    json_data = find_json_in_html(html_content)

    # 保存结果
    output = {
        'note_links': result['note_links'][:20],  # 只保存前20个
        'user_links': result['user_links'][:20],
        'extracted_json': json_data[:10],
        'extraction_time': datetime.now().isoformat(),
    }

    output_file = Path(__file__).parent.parent / "data" / "parsed_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 保存结果到: {output_file}")
    print(f"✅ 完成!")


if __name__ == "__main__":
    main()
