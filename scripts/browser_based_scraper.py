#!/usr/bin/env python3
"""
基于浏览器��小红书爬虫 - 实时获取搜索结果

使用 Playwright 渲染页面，然后提取搜索结果
"""

import asyncio
import json
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


async def scrape_xiaohongshu_search(keyword):
    """���取小红书搜索结果"""
    print(f"🔍 搜索关键词: {keyword}")

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # 访问搜索页面
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=51"
        print(f"📄 访问: {search_url}")

        try:
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            print("✅ 页面加载完成")

            # 等待笔记列表加载
            await page.wait_for_selector('section, article, .note-item, [class*="note"]', timeout=10000)
            print("✅ 笔记列表已加载")

            # 获取页面内容
            content = await page.content()

            # 尝试从页面中提取数据
            notes = await extract_notes_from_page(page)

            # 保存HTML用于调试
            output_dir = Path(__file__).parent.parent / "data" / "raw_pages"
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(output_dir / filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"💾 保存HTML: {output_dir / filename}")

            return notes

        except Exception as e:
            print(f"❌ 错误: {e}")
            return []
        finally:
            await browser.close()


async def extract_notes_from_page(page):
    """从页面中提取笔记数据"""
    notes = []

    # 方法1: 尝试从window对象中提取数据
    try:
        data = await page.evaluate('''
            () => {
                // 尝试获取 __INITIAL_STATE__
                if (window.__INITIAL_STATE__) {
                    return {
                        type: 'INITIAL_STATE',
                        data: window.__INITIAL_STATE__
                    };
                }

                // 尝试获取其他全局变量
                if (window.__INITIAL_SSR_STATE__) {
                    return {
                        type: 'INITIAL_SSR_STATE',
                        data: window.__INITIAL_SSR_STATE__
                    };
                }

                return null;
            }
        ''')

        if data:
            print(f"✅ 找到 {data['type']}")
            notes = parse_initial_state(data['data'])
            if notes:
                return notes
    except Exception as e:
        print(f"⚠️  无法从window对象提取: {e}")

    # 方法2: 尝试从DOM中提取
    try:
        dom_notes = await page.evaluate('''
            () => {
                const results = [];

                // 尝试选择不同的容器
                const selectors = [
                    'section',
                    'article',
                    '.note-item',
                    '[class*="note"]',
                    '[class*="card"]'
                ];

                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        console.log(`Found ${elements.length} elements with selector: ${selector}`);

                        elements.forEach((el, index) => {
                            if (index < 10) { // 只取前10个
                                const title = el.querySelector('[class*="title"], h1, h2, h3')?.textContent?.trim();
                                const text = el.textContent?.trim().substring(0, 200);
                                const link = el.querySelector('a')?.href;

                                if (title || text) {
                                    results.push({
                                        title: title || 'No title',
                                        text: text || 'No text',
                                        link: link || 'No link',
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

        if dom_notes:
            print(f"✅ 从DOM提取了 {len(dom_notes)} 条笔记")
            for idx, note in enumerate(dom_notes[:5], 1):
                print(f"\n笔记 {idx}:")
                print(f"  标题: {note['title']}")
                print(f"  内容: {note['text'][:100]}...")
                print(f"  链接: {note['link']}")

            notes = dom_notes
    except Exception as e:
        print(f"⚠️  无法从DOM提取: {e}")

    return notes


def parse_initial_state(data):
    """解析INITIAL_STATE数据"""
    notes = []

    # 这是一个递归搜索函数，找到所有可能是笔记的数组
    def find_notes_arrays(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                # 查找包含笔记数据的数组
                if isinstance(value, list) and len(value) > 0:
                    # 检查是否是笔记数组
                    if any(isinstance(item, dict) and ('title' in item or 'noteId' in item or 'note_card' in item) for item in value[:5]):
                        print(f"✅ 可能的笔记数组: {new_path} ({len(value)} 项)")
                        return value
                result = find_notes_arrays(value, new_path)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = find_notes_arrays(item, path)
                if result:
                    return result
        return None

    notes_array = find_notes_arrays(data)

    if notes_array:
        for note in notes_array[:10]:
            # 提取笔记信息
            note_data = {
                'id': note.get('id') or note.get('noteId') or note.get('note_id'),
                'title': note.get('title') or note.get('note_card', {}).get('title'),
                'desc': note.get('desc') or note.get('description'),
                'type': note.get('type'),
            }

            # 用户信息
            user = note.get('user', {})
            note_data['author'] = user.get('nickname') or user.get('name')
            note_data['author_id'] = user.get('user_id') or user.get('userId')

            # 互动信息
            interact = note.get('interact_info') or note.get('interactInfo', {})
            note_data['liked_count'] = interact.get('liked_count') or interact.get('likedCount')
            note_data['collected_count'] = interact.get('collected_count') or interact.get('collectedCount')

            if note_data['id'] or note_data['title']:
                notes.append(note_data)
                print(f"  - {note_data['title'] or note_data['id']}")

    return notes


async def main():
    print("🚀 基于浏览器的小红书爬虫")
    print("="*60)

    keyword = "深圳找对象"
    notes = await scrape_xiaohongshu_search(keyword)

    if notes:
        print(f"\n✅ 成功提取 {len(notes)} 条笔记")

        # 保存结果
        output_file = Path(__file__).parent.parent / "data" / "scraped_notes.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

        print(f"💾 保存到: {output_file}")
    else:
        print("❌ 没有提取到笔记数据")


if __name__ == "__main__":
    asyncio.run(main())
