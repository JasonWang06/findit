#!/usr/bin/env python3
import json
import re
from pathlib import Path

html_file = Path('/Users/json/Desktop/findit/data/playwright_pages/深圳找对象_084559.html')
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取JSON
match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>', content, re.DOTALL)
if match:
    json_str = match.group(1)

    # 保存原始JSON
    output = Path('/Users/json/Desktop/findit/data/initial_state_raw.json')
    with open(output, 'w', encoding='utf-8') as f:
        f.write(json_str)
    print(f'保存原始JSON: {output}')
    print(f'JSON大小: {len(json_str):,} 字符')

    # 尝试解析
    try:
        data = json.loads(json_str)
        print(f'\n✅ JSON解析成功')
        print(f'Top-level keys: {list(data.keys())[:20]}')

        # 查找笔记相关数据
        print(f'\n🔍 查找笔记数据:')
        for key, value in list(data.items())[:10]:
            if isinstance(value, dict):
                subkeys = list(value.keys())[:5]
                print(f'  {key}: dict with keys {subkeys}')

                # 查找包含"note"的子键
                note_keys = [k for k in value.keys() if 'note' in k.lower()]
                if note_keys:
                    print(f'    -> 找到note相关: {note_keys}')

            elif isinstance(value, list):
                print(f'  {key}: list with {len(value)} items')

    except json.JSONDecodeError as e:
        print(f'\n❌ JSON解析失败: {e}')
        print(f'错误位置: {e.pos if hasattr(e, "pos") else "unknown"}')

        # 尝试查找笔记相关字符串
        print(f'\n🔍 在JSON中搜索笔记相关字段:')
        patterns = [
            r'"noteId":\s*"([^"]+)"',
            r'"title":\s*"([^"]{20,})"',  # 标题至少20字符
            r'"nickname":\s*"([^"]+)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, json_str)
            if matches:
                field_name = pattern.split('"')[1]
                print(f'  {field_name}: 找到 {len(matches)} 个')
                for match in matches[:3]:
                    print(f'    - {match[:100]}')
