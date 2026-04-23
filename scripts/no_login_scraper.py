#!/usr/bin/env python3
"""
小红书无账号爬虫 - 公开页面版本

尝试从公开页面爬取数据，不依赖登录
"""

import requests
import re
import json
from datetime import datetime
from pathlib import Path

# 添加findit到path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def search_xiaohongshu(keyword, page=1):
    """尝试公开搜索"""
    print(f"🔍 搜索关键词: {keyword} (第{page}页)")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    # 方法1: 直接访问搜索页面
    url = f"https://www.xiaohongshu.com/search_result?keyword={requests.utils.quote(keyword)}&type=51"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"📄 状态码: {resp.status_code}")
        print(f"📏 响应大小: {len(resp.text)} 字符")

        # 保存原始页面用于分析
        output_dir = Path(__file__).parent.parent / "data" / "raw_pages"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{keyword}_{page}_{datetime.now().strftime('%H%M%S')}.html"
        with open(output_dir / filename, 'w', encoding='utf-8') as f:
            f.write(resp.text)

        print(f"💾 保存到: {output_dir / filename}")

        return resp.text

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def search_api_public(keyword, page=1):
    """尝试公开搜索API（部分API不需要登录）"""
    print(f"🔍 API搜索: {keyword} (第{page}页)")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.xiaohongshu.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.xiaohongshu.com',
    }

    # 小红书搜索API
    url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"

    params = {
        'keyword': keyword,
        'page': page,
        'page_size': 20,
        'search_id': 'temp_search_id',
        'sort': 'general',
        'note_type': 0,
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"📄 状态码: {resp.status_code}")

        data = resp.json()
        print(f"📊 响应: {json.dumps(data, ensure_ascii=False)[:500]}")

        return data

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def parse_search_page(html_content):
    """解析搜索页面，提取数据"""
    if not html_content:
        return []

    results = []

    # 尝试从页面中提取JSON数据
    # 小红书页面通常包含初始数据的<script>标签

    # 方法1: 提取 __INITIAL_STATE__ 或类似的数据
    patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>',
        r'"notes"\s*:\s*\[(.*?)\]',
        r'"items"\s*:\s*\[(.*?)\]',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            print(f"✅ 找到匹配: {pattern[:50]}...")
            for match in matches[:3]:
                print(f"   片段: {match[:200]}...")
            break

    # 尝试提取用户链接
    user_links = re.findall(r'xiaohongshu\.com/user/profile/([a-zA-Z0-9]+)', html_content)
    if user_links:
        print(f"✅ 找到 {len(user_links)} 个用户链接")

    # 尝试提取笔记ID
    note_ids = re.findall(r'"noteId"\s*:\s*"([^"]+)"', html_content)
    if note_ids:
        print(f"✅ 找到 {len(note_ids)} 个笔记ID")

    # 尝试提取话题
    topics = re.findall(r'topic/([^"\']+)', html_content)
    if topics:
        print(f"✅ 找到 {len(topics)} 个话题")

    return results


def try_alternative_apis(keyword):
    """尝试其他可能的API"""
    print(f"\n🔍 尝试其他API端点...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.xiaohongshu.com/',
    }

    # 尝试不同的API端点
    endpoints = [
        "https://www.xiaohongshu.com/api/sns/web/v1/search/notes",
        "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
        "https://www.xiaohongshu.com/api/sns/web/v1/homefeed",
    ]

    for url in endpoints:
        print(f"\n📡 测试: {url}")
        try:
            params = {
                'keyword': keyword,
                'page': 1,
                'page_size': 10,
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"   状态码: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"   响应类型: {type(data)}")
                    if isinstance(data, dict):
                        print(f"   keys: {list(data.keys())[:10]}")
                        if 'data' in data:
                            print(f"   data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
                except:
                    print(f"   响应: {resp.text[:200]}")

        except Exception as e:
            print(f"   错误: {e}")


def main():
    keyword = "新加坡找对象"

    print("=" * 60)
    print("🔍 小红书无账号爬虫测试")
    print("=" * 60)

    # 1. 直接访问搜索页面
    print("\n📋 方法1: 直接访问搜索页面")
    print("-" * 40)
    html = search_xiaohongshu(keyword)

    if html:
        print("\n📊 解析页面内容...")
        parse_search_page(html)

    # 2. 尝试搜索API
    print("\n\n📋 方法2: 尝试搜索API")
    print("-" * 40)
    search_api_public(keyword)

    # 3. 尝试其他API
    print("\n\n📋 方法3: 尝试其他API端点")
    print("-" * 40)
    try_alternative_apis(keyword)

    print("\n" + "=" * 60)
    print("💡 查看 data/raw_pages/ 目录下的HTML文件了解页面结构")
    print("=" * 60)


if __name__ == "__main__":
    main()
