"""Probe /explore/<note_id> DOM to find selectors for comments + author user_id.

Picks a note from a fresh search, navigates to its canonical /explore URL,
dumps relevant DOM info (comment selectors, __INITIAL_STATE__ keys, author link).
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

from findit.config import settings
from findit.crawler.client import USER_AGENT

KEYWORD = "深圳找对象"


async def main():
    profile = Path(settings.browser_profile_dir).resolve()
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile), headless=False,
            user_agent=USER_AGENT,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            print("→ goto search results")
            await page.goto(
                f"https://www.xiaohongshu.com/search_result?keyword={quote(KEYWORD)}&source=web_search_result_notes",
                wait_until="domcontentloaded", timeout=30000,
            )
            await asyncio.sleep(5)

            # extract note_id from first card
            hrefs = await page.locator("section.note-item a.cover").evaluate_all(
                "els => els.map(e => e.getAttribute('href'))"
            )
            print(f"  found {len(hrefs)} card hrefs")
            if not hrefs:
                print("no results — abort")
                return
            first_href = hrefs[0]
            m = re.search(r"/(?:search_result|explore)/([0-9a-f]+)", first_href)
            if not m:
                print(f"can't parse note_id from {first_href!r}")
                return
            note_id = m.group(1)
            xsec = ""
            xm = re.search(r"xsec_token=([^&]+)", first_href)
            if xm:
                xsec = xm.group(1)
            print(f"  note_id={note_id}, xsec_token={xsec[:20]}…")

            # navigate to canonical /explore url
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            if xsec:
                url += f"?xsec_token={xsec}&xsec_source=pc_search"
            print(f"\n→ goto {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print("  waiting 8s for hydration + comments…")
            await asyncio.sleep(8)

            # try scrolling to trigger lazy comments
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)
            except Exception:
                pass

            # discover all elements containing 'comment' in class
            print("\n=== element class scan (anything with 'comment') ===")
            classes = await page.evaluate("""
                () => {
                    const seen = new Map();
                    document.querySelectorAll('*').forEach(el => {
                        const cls = el.className;
                        if (typeof cls !== 'string') return;
                        cls.split(/\\s+/).forEach(c => {
                            if (c && c.toLowerCase().includes('comment')) {
                                seen.set(c, (seen.get(c) || 0) + 1);
                            }
                        });
                    });
                    return [...seen.entries()].sort((a,b) => b[1]-a[1]);
                }
            """)
            for cls, n in classes[:30]:
                print(f"  .{cls}: {n}")

            # author user_id discovery
            print("\n=== author user link scan ===")
            authors = await page.evaluate("""
                () => {
                    const seen = new Set();
                    document.querySelectorAll('a[href*="/user/profile/"]').forEach(a => {
                        seen.add(a.getAttribute('href'));
                    });
                    return [...seen];
                }
            """)
            for h in authors[:10]:
                print(f"  {h}")

            # look for __INITIAL_STATE__
            print("\n=== window.__INITIAL_STATE__ top-level keys ===")
            state_info = await page.evaluate("""
                () => {
                    const s = window.__INITIAL_STATE__;
                    if (!s) return null;
                    function summarize(obj, depth=2) {
                        if (depth === 0 || obj === null || typeof obj !== 'object') return typeof obj;
                        if (Array.isArray(obj)) return `array[${obj.length}]`;
                        const out = {};
                        for (const k of Object.keys(obj).slice(0, 15)) {
                            out[k] = summarize(obj[k], depth - 1);
                        }
                        return out;
                    }
                    return summarize(s, 3);
                }
            """)
            print(json.dumps(state_info, indent=2, ensure_ascii=False) if state_info else "(absent)")

            # candidate comment selectors
            print("\n=== candidate comment selectors ===")
            cands = [
                ".comment-item", ".commentItem", ".commentItem .reds-comment-content",
                ".list-container .parent-comment", ".comments-container .parent-comment",
                ".comments-el .parent-comment", ".comments-el .comment-item",
                ".comments-el", ".reds-comment", "div[class*='parent-comment']",
                "div[class*='Comment']", "div[class*='comment-list'] > div",
                ".note-scroller .comment-item", "div.list-container > div",
            ]
            for sel in cands:
                try:
                    n = await page.locator(sel).count()
                    if n:
                        print(f"  {sel}: {n}")
                except Exception:
                    pass

            # dump first 2000 chars of any element matching most-frequent comment class
            if classes:
                top = classes[0][0]
                print(f"\n=== outerHTML of first .{top} (truncated) ===")
                try:
                    html = await page.locator(f".{top}").first.evaluate("el => el.outerHTML.slice(0, 2000)")
                    print(html)
                except Exception as e:
                    print(f"(failed: {e})")
        finally:
            await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
