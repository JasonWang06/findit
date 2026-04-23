#!/usr/bin/env python3
"""
灵活的爬��策略 - 支持本地和服务器部署

策略优先级：
1. API调用（最快，适合生产）
2. Playwright渲染（开发调试）
3. MediaCrawler（备选方案）
"""

import os
import json
import asyncio
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


class CrawlerMode(Enum):
    """爬虫模式"""
    API = "api"  # 纯API调用，适合服务器
    BROWSER = "browser"  # 浏览器渲染，适合开发
    MEDIA_CRAWLER = "media_crawler"  # MediaCrawler，需要登录


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    mode: CrawlerMode
    headless: bool = True  # 浏览器是否无头模式
    timeout: int = 30000  # 超时时间(ms)
    max_retries: int = 3  # 最大重试次数

    @classmethod
    def auto_detect(cls) -> 'CrawlerConfig':
        """自动检测最佳配置"""
        # 检测环境
        is_server = os.environ.get('SSH_CONNECTION') or not os.environ.get('DISPLAY')
        has_playwright = True  # TODO: 实际检测

        if is_server:
            print("🖥️  检测到服务器环境，使用API模式")
            return cls(mode=CrawlerMode.API)
        else:
            print("💻 检测到本地环境，使用浏览器模式")
            return cls(mode=CrawlerMode.BROWSER, headless=False)


class FlexibleCrawler:
    """灵活爬虫"""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.results = []

    async def search(self, keyword: str) -> List[Dict]:
        """搜索笔记"""
        if self.config.mode == CrawlerMode.API:
            return await self._search_by_api(keyword)
        elif self.config.mode == CrawlerMode.BROWSER:
            return await self._search_by_browser(keyword)
        else:
            return await self._search_by_media_crawler(keyword)

    async def _search_by_api(self, keyword: str) -> List[Dict]:
        """使用API搜索（服务器推荐）"""
        print(f"📡 API模式: {keyword}")

        # TODO: 实现API调用
        # 1. 获取Cookie（从环境变量或文件）
        # 2. 生成请求签名
        # 3. 调用搜索API
        # 4. 解析返回的JSON

        # 临时模拟返回
        return []

    async def _search_by_browser(self, keyword: str) -> List[Dict]:
        """使用浏览器搜索（本地开发）"""
        print(f"🌐 浏览器模式: {keyword}")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.config.headless,
                    args=['--no-sandbox', '--disable-setuid-sandbox'] if self.config.headless else []
                )

                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )

                page = await context.new_page()

                # 访问搜索页面
                url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=51"
                await page.goto(url, wait_until='networkidle', timeout=self.config.timeout)

                # 等待内容加载
                await page.wait_for_timeout(3000)  # 额外等待JS执行

                # 提取数据
                notes = await self._extract_data_from_browser(page)

                await browser.close()
                return notes

        except ImportError:
            print("❌ 需要安装 playwright: pip install playwright")
            return []
        except Exception as e:
            print(f"❌ 浏览器模式失败: {e}")
            # 降级到API模式
            print("🔄 降级到API模式...")
            return await self._search_by_api(keyword)

    async def _extract_data_from_browser(self, page) -> List[Dict]:
        """从浏览器页面提取数据"""
        try:
            # 尝试从window对象获取数据
            data = await page.evaluate('''
                () => {
                    // 小红书通常把数据存在 window.__INITIAL_STATE__ 或类似对象中
                    if (window.__INITIAL_STATE__) {
                        return window.__INITIAL_STATE__;
                    }

                    // 如果没有，尝试提取页面中的文本信息
                    const notes = [];
                    document.querySelectorAll('section, article, [class*="note"], [class*="card"]').forEach(el => {
                        const title = el.querySelector('[class*="title"]')?.textContent?.trim();
                        const text = el.textContent?.trim().substring(0, 200);
                        if (title || text) {
                            notes.push({ title, text });
                        }
                    });
                    return { items: notes.slice(0, 20) };  // 限制数量
                }

                return null;
            ''')

            if data:
                return self._parse_response_data(data)

        except Exception as e:
            print(f"⚠️  数据提取失败: {e}")

        return []

    async def _search_by_media_crawler(self, keyword: str) -> List[Dict]:
        """使用MediaCrawler"""
        print(f"🤖 MediaCrawler模式: {keyword}")

        # TODO: 调用MediaCrawler
        # 这需要MediaCrawler支持作为库调用，或者通过subprocess调用

        return []

    def _parse_response_data(self, data: Dict) -> List[Dict]:
        """解析响应数据"""
        notes = []

        # TODO: 根据实际的数据结构解析
        # 这里需要先运行一次，看看实际的数据格式

        return notes


class ServerCrawler(FlexibleCrawler):
    """服务器专用爬虫 - 优化的轻量级版本"""

    def __init__(self):
        # 服务器配置优化
        config = CrawlerConfig(
            mode=CrawlerMode.API,
            timeout=15000,  # 更短超时
            max_retries=2
        )
        super().__init__(config)

    async def search_batch(self, keywords: List[str]) -> Dict[str, List[Dict]]:
        """批量搜索（服务器优化）"""
        results = {}

        # 限制并发数，避免被封
        semaphore = asyncio.Semaphore(3)

        async def search_with_limit(keyword):
            async with semaphore:
                return keyword, await self.search(keyword)

        tasks = [search_with_limit(kw) for kw in keywords]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                print(f"❌ 搜索失败: {item}")
                continue
            keyword, notes = item
            results[keyword] = notes

        return results


# 便捷函数
async def quick_search(keyword: str, mode: Optional[str] = None) -> List[Dict]:
    """快速搜索"""
    if mode:
        config = CrawlerConfig(mode=CrawlerMode(mode))
    else:
        config = CrawlerConfig.auto_detect()

    crawler = FlexibleCrawler(config)
    return await crawler.search(keyword)


async def main():
    """测试"""
    print("🚀 灵活爬虫测试")
    print("="*60)

    # 自动检测模式
    config = CrawlerConfig.auto_detect()
    print(f"模式: {config.mode.value}")
    print(f"无头: {config.headless}")

    # 测试搜索
    crawler = FlexibleCrawler(config)
    results = await crawler.search("深圳找对象")

    print(f"\n✅ 找到 {len(results)} 条笔记")

    # 保存结果
    if results:
        output = Path(__file__).parent.parent.parent / "data" / "crawler_test_results.json"
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 保存到: {output}")


if __name__ == "__main__":
    asyncio.run(main())
