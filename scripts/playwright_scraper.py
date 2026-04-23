#!/usr/bin/env python3
"""
使用Playwright爬取小红书搜索结果

优势：
1. 让JavaScript完整渲染
2. 可以直接从window对象获取数据
3. 不需要登录就能获取搜索结果
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


async def scrape_search_results(keyword, headless=True):
    """爬取搜索结果"""
    print(f"🔍 搜索关键词: {keyword}")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        try:
            # 访问搜索页面
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=51"
            print(f"📄 访问: {url}")

            await page.goto(url, wait_until='networkidle', timeout=30000)
            print("✅ 页面加载完成")

            # 等���JavaScript渲染
            await page.wait_for_timeout(3000)

            # 尝试从window对象获取数据
            data = await page.evaluate('''
                () => {
                    // 尝试多种可能的数据位置
                    if (window.__INITIAL_STATE__) {
                        return {
                            source: '__INITIAL_STATE__',
                            data: window.__INITIAL_STATE__
                        };
                    }

                    // 尝试其他可能的全局变量
                    const keys = Object.keys(window).filter(key =>
                        key.includes('INITIAL') ||
                        key.includes('STATE') ||
                        key.includes('DATA')
                    );

                    if (keys.length > 0) {
                        return {
                            source: keys[0],
                            data: window[keys[0]]
                        };
                    }

                    return null;
                }
            ''')

            if data:
                print(f"✅ 找到数据源: {data['source']}")
                notes = extract_notes_from_state(data['data'])
            else:
                print("⚠️  无法从window对象获取数据")
                # 尝试从DOM中提取
                notes = await extract_from_dom(page)

            # 保存HTML用于调试
            if not headless or len(notes) == 0:
                html_content = await page.content()
                output_dir = Path(__file__).parent.parent / "data" / "playwright_pages"
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = output_dir / f"{keyword}_{datetime.now().strftime('%H%M%S')}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"💾 保存HTML: {filename}")

            await browser.close()
            return notes

        except Exception as e:
            print(f"❌ 错误: {e}")
            await browser.close()
            return []


def extract_notes_from_state(state_data):
    """从state数据中提取笔记"""
    notes = []

    # 递归搜索笔记数据
    def find_notes(obj, path="", depth=0):
        if depth > 10:  # 限制递归深度
            return

        if isinstance(obj, dict):
            # 检查是否是笔记对象
            if any(key in obj for key in ['noteId', 'note_card', 'model', 'title']):
                if 'noteId' in obj or 'id' in obj:
                    note = extract_note_info(obj)
                    if note:
                        notes.append(note)

            # 递归搜索
            for key, value in obj.items():
                # 跳过一些明显不是笔记的字段
                if key not in ['global', 'user', 'appSettings', 'signConfig']:
                    find_notes(value, f"{path}.{key}", depth + 1)

        elif isinstance(obj, list) and len(obj) > 0:
            # 如果是数组，检查第一个元素
            first_item = obj[0]
            if isinstance(first_item, dict):
                # 检查是否看起来像笔记数组
                if any(key in first_item for key in ['noteId', 'note_card', 'title', 'desc']):
                    for item in obj[:50]:  # 最多取50个
                        note = extract_note_info(item)
                        if note:
                            notes.append(note)
                else:
                    # 继续递归
                    for item in obj[:10]:  # 只检查前10个
                        find_notes(item, path, depth + 1)

    find_notes(state_data)
    return notes


def extract_note_info(obj):
    """提取笔记信息"""
    if not isinstance(obj, dict):
        return None

    note = {}

    # 基本信息
    note['id'] = obj.get('id') or obj.get('noteId') or obj.get('note_id')
    note['title'] = obj.get('title')
    note['desc'] = obj.get('desc') or obj.get('description')

    # 用户信息
    user = obj.get('user', {})
    note['author_id'] = user.get('user_id') or user.get('userId')
    note['author_name'] = user.get('nickname') or user.get('name')

    # 互动信息
    interact = obj.get('interact_info', {}) or obj.get('interactInfo', {})
    note['liked_count'] = interact.get('liked_count') or interact.get('likedCount')
    note['collected_count'] = interact.get('collected_count') or interact.get('collectedCount')
    note['comment_count'] = interact.get('comment_count') or interact.get('commentCount')

    # 封面图
    note['cover'] = obj.get('cover') or obj.get('image')

    # 必须有ID或标题
    if not (note['id'] or note['title']):
        return None

    return note


async def extract_from_dom(page):
    """从DOM中提取数据（备用方案）"""
    print("📝 尝试从DOM提取数据...")

    try:
        notes = await page.evaluate('''
            () => {
                const results = [];

                // 尝试多种选择器
                const selectors = [
                    'section[class*="note"]',
                    'article[class*="note"]',
                    'div[class*="note-item"]',
                    'div[class*="card"]',
                    'a[href*="/explore/"]'
                ];

                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);

                    if (elements.length > 0) {
                        console.log(`找到 ${elements.length} 个元素: ${selector}`);

                        elements.forEach((el, index) => {
                            if (index < 20) {  // 限制数量
                                const titleEl = el.querySelector('[class*="title"], h1, h2, h3');
                                const textEl = el.querySelector('[class*="desc"], [class*="content"], p');
                                const linkEl = el.querySelector('a[href*="/explore/"], a[href*="/user/"]');

                                const title = titleEl?.textContent?.trim();
                                const text = textEl?.textContent?.trim().substring(0, 200);
                                const link = linkEl?.href;

                                if (title || text || link) {
                                    results.push({
                                        title: title || '',
                                        text: text || '',
                                        link: link || '',
                                        selector: selector
                                    });
                                }
                            }
                        });

                        if (results.length > 0) {
                            break;
                        }
                    }
                }

                return results;
            }
        ''')

        if notes:
            print(f"✅ 从DOM提取了 {len(notes)} 条笔记")
            return notes
        else:
            print("❌ DOM中没有找到笔记")
            return []

    except Exception as e:
        print(f"❌ DOM提取失败: {e}")
        return []


async def main():
    """主函数"""
    print("🚀 Playwright爬虫测试")
    print("="*60)

    keywords = ["深圳找对象"]

    for keyword in keywords:
        print(f"\n{'='*60}")
        notes = await scrape_search_results(keyword, headless=False)  # 用非无头模式测试

        if notes:
            print(f"\n✅ 成功提取 {len(notes)} 条笔记")
            print(f"{'='*60}")

            # 显示前5条
            for i, note in enumerate(notes[:5], 1):
                print(f"\n笔记 {i}:")
                print(f"  ID: {note.get('id')}")
                print(f"  标题: {note.get('title')}")
                print(f"  作者: {note.get('author_name')}")
                print(f"  点赞: {note.get('liked_count')}")

            # 保存结果
            output_file = Path(__file__).parent.parent / "data" / "scraped_notes.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
            print(f"\n💾 保存到: {output_file}")
        else:
            print("❌ 没有提取到笔记")


if __name__ == "__main__":
    asyncio.run(main())
