#!/usr/bin/env python3
"""
测试不登录爬取小红书

策略：
1. 直接访问搜索结���页面
2. 查看是否返回内容
3. 分析页面结构
"""

import requests
import re
import json
from pathlib import Path
from datetime import datetime
import time


def test_search_page(keyword):
    """测试搜索页面是否可访问"""
    print(f"🔍 测试搜索: {keyword}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    # 搜索页面URL
    url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=51"

    try:
        print(f"📄 访问: {url}")
        resp = requests.get(url, headers=headers, timeout=15)

        print(f"✅ 状态码: {resp.status_code}")
        print(f"📏 响应大小: {len(resp.text):,} 字符")
        print(f"🍪 Cookie数量: {len(resp.cookies)}")

        # 检查是否被重定向到登录页
        if 'login' in resp.url.lower():
            print("⚠️  被重定向到登录页面")
            return False

        # 检查是否有内容
        if len(resp.text) < 1000:
            print("⚠️  页面内容太少，可能被拦截")
            print(f"内容: {resp.text[:500]}")
            return False

        # 保存HTML
        output_dir = Path(__file__).parent.parent / "data" / "test_pages"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = output_dir / f"test_{keyword}_{datetime.now().strftime('%H%M%S')}.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(resp.text)

        print(f"💾 保存到: {filename}")

        # 快速分析
        analyze_html(resp.text, keyword)

        return True

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def analyze_html(html_content, keyword):
    """快速分析HTML内容"""
    print(f"\n📊 分析HTML内容:")

    # 检查关键词
    if '登录' in html_content and '请先登录' in html_content:
        print("❌ 页面要求登录")
        return

    if '验证' in html_content or 'captcha' in html_content.lower():
        print("❌ 页面有验证码")
        return

    # 查找可能的数据
    patterns = {
        '笔记链接': r'xiaohongshu\.com/explore/([a-zA-Z0-9]+)',
        '用户链接': r'xiaohongshu\.com/user/profile/([a-zA-Z0-9]+)',
        'JSON数据': r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>',
        '标题': r'<title>(.*?)</title>',
    }

    results = {}
    for name, pattern in patterns.items():
        matches = re.findall(pattern, html_content)
        if matches:
            results[name] = len(matches)
            print(f"  ✅ {name}: {len(matches)} 个")

    if not results:
        print("  ⚠️  没有找到明显的数据结构")
        # 检查是否有JavaScript渲染的内容
        if 'script' in html_content.lower():
            print("  💡 页面包含JavaScript，可能需要渲染")
    else:
        print(f"\n  ✅ 找到数据！不登录可以访问")


def test_multiple_keywords():
    """测试多个关键词"""
    keywords = [
        "深圳找对象",
        "相亲",
        "脱单",
        "交友",
    ]

    results = {}
    for keyword in keywords:
        print(f"\n{'='*60}")
        success = test_search_page(keyword)
        results[keyword] = success

        # 避免请求过快
        time.sleep(2)

    # 总结
    print(f"\n{'='*60}")
    print("📊 测试总结:")
    for keyword, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {keyword}: {status}")


def test_specific_page():
    """测试特定笔记页面（如果有的话）"""
    print(f"\n{'='*60}")
    print("🔍 测试笔记详情页面")

    # 这是之前HTML中找到的UUID链接
    test_urls = [
        "https://www.xiaohongshu.com/3ca6607e-d4a5-4cb9-b455-a746713d8283",
        "https://www.xiaohongshu.com/83074709-0d05-4d1c-9d38-24a8e910d914",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    for url in test_urls:
        print(f"\n📄 测试: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"  状态码: {resp.status_code}")
            print(f"  内容大小: {len(resp.text):,} 字符")

            if '登录' in resp.text:
                print("  ⚠️  需要登录")
            elif len(resp.text) > 5000:
                print(f"  ✅ 可以访问")

        except Exception as e:
            print(f"  ❌ 失败: {e}")


def main():
    print("🚀 小红书不登录爬取测试")
    print("="*60)

    # 1. 测试搜索页面
    test_multiple_keywords()

    # 2. 测试详情页面
    test_specific_page()

    print(f"\n{'='*60}")
    print("💡 结论:")
    print("如果上述测试显示需要登录，我们有以下选择：")
    print("1. 使用MediaCrawler的自动登录功能")
    print("2. 手动获取Cookie并配置")
    print("3. 使用Playwright模拟浏览器登录")


if __name__ == "__main__":
    main()
