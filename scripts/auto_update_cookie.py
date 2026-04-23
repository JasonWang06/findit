#!/usr/bin/env python3
"""
全自动Cookie获取器 - 扫码登录版

使用Playwright打开浏览器，等待用户扫码登录小红书，
然后自动获取包含web_session的cookies。
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime


async def wait_for_login_and_get_cookies():
    """等待用户扫码登录，获取cookies"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("📦 安装Playwright...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "-q"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        from playwright.async_api import async_playwright

    print("🤖 FindIt 全自动Cookie获取器")
    print("=" * 50)
    print("")
    print("📱 即将打开Chrome浏览器...")
    print("   1. 请用小红书APP扫码登录")
    print("   2. 登录成功后，cookies会自动保存")
    print("")
    print("⚠️  请在浏览器中完成扫码登录，等待中...")
    print("")

    async with async_playwright() as p:
        # 启动Chromium
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        # 创建上下文
        context = await browser.new_context()
        page = await context.new_page()

        # 访问小红书
        print("🌐 访问小红书...")
        await page.goto("https://www.xiaohongshu.com", timeout=60000)

        # 等待扫码登录
        # 检测登录成功：URL变化或出现用户信息
        login_timeout = 120  # 2分钟超时
        start_time = time.time()

        while time.time() - start_time < login_timeout:
            try:
                # 检查URL
                url = page.url
                if "login" not in url.lower():
                    # 检查页面内容
                    content = await page.content()
                    if "login" not in content.lower()[:1000]:
                        print("✅ 检测到登录成功！")
                        break
            except:
                pass

            await asyncio.sleep(1)
            elapsed = int(time.time() - start_time)
            if elapsed % 15 == 0:
                print(f"⏳ 等待扫码登录... ({elapsed}秒)")

        # 额外等待确保cookie完全加载
        print("🍪 等待cookies加载...")
        await asyncio.sleep(3)

        # 获取cookies
        cookies = await context.cookies()

        # 检查是否有web_session
        cookie_names = [c['name'] for c in cookies]
        has_web_session = 'web_session' in cookie_names

        if not has_web_session:
            print("⚠️  未检测到web_session cookie")
            print("   尝试刷新页面...")
            await page.reload()
            await asyncio.sleep(5)
            cookies = await context.cookies()
            cookie_names = [c['name'] for c in cookies]

        await browser.close()
        return cookies


def save_cookies(cookies):
    """保存cookies到FindIt"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.setup_cookie_manager import CookieManager

    # 构造cookie字符串
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    manager = CookieManager()
    manager.save_cookie_to_file(cookie_str, "qrcode_login")
    manager.update_mediacrawler_config(cookie_str)

    # 保存详细信息
    detail_file = Path(__file__).parent.parent / "data/xhs_cookies_detail.json"
    with open(detail_file, 'w') as f:
        json.dump({
            'cookies': cookies,
            'cookie_str': cookie_str,
            'extracted_at': datetime.now().isoformat(),
            'source': 'qrcode_login'
        }, f, indent=2)

    return cookie_str


def main():
    print("")
    print("=" * 50)
    print("⚠️  重要：浏览器将打开小红书")
    print("   请用小红书APP扫码登录")
    print("   登录成功后，cookie会自动保存")
    print("=" * 50)
    print("")

    try:
        cookies = asyncio.run(wait_for_login_and_get_cookies())

        if not cookies:
            print("❌ 无法获取cookies")
            return 1

        print(f"\n✅ 获取到 {len(cookies)} 个cookies")

        # 显示关键cookies
        print("\n关键cookies:")
        key_cookies = ['a1', 'webId', 'web_session', 'websectiga']
        for c in cookies:
            if c['name'] in key_cookies:
                val = c['value']
                if len(val) > 40:
                    val = val[:40] + "..."
                print(f"   {'✅' if c['name'] == 'web_session' else '📋'} {c['name']}: {val}")

        # 检查web_session
        cookie_names = [c['name'] for c in cookies]
        if 'web_session' not in cookie_names:
            print("\n⚠️  警告：未找到web_session")
            print("   请确保扫码登录成功后再关闭浏览器")
            return 1

        # 保存
        cookie_str = save_cookies(cookies)

        print("\n" + "=" * 50)
        print("🎉 Cookie保存成功！")
        print(f"📋 共 {len(cookies)} 个cookies")
        print(f"📏 字符串长度: {len(cookie_str)} 字符")
        print("\n✅ 以后运行爬虫将完全自动化！")

        return 0

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
