"""DOM-based search experiment.

Hypothesis: XHS risk-control flags `/api/.../search/notes` POST from page.evaluate(fetch),
but allows the same logical query when triggered via UI navigation. We test by
navigating directly to /search_result?keyword=... and reading rendered note cards.

If this works where the API path returns 300011, the right architecture is
"navigate + DOM scrape" rather than "page.evaluate(fetch())".
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

from findit.config import settings
from findit.crawler.client import USER_AGENT, _LOGIN_PROBE_JS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("dom_smoke")

KEYWORD = "深圳找对象"


async def wait_for_login(page, ctx, timeout_sec: int = 300):
    log.info("checking login state...")
    for _ in range(int(timeout_sec)):
        res = await page.evaluate(_LOGIN_PROBE_JS)
        cookies = await ctx.cookies("https://www.xiaohongshu.com")
        has_session = any(c["name"] == "web_session" and len(c["value"]) >= 20 for c in cookies)
        if isinstance(res, dict) and res.get("logged_in") and has_session:
            log.info("✓ logged in (signal=%s, web_session=present)", res.get("why"))
            return
        await asyncio.sleep(1)
    raise RuntimeError("login timeout")


async def main():
    profile = Path(settings.browser_profile_dir).resolve()
    profile.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            user_agent=USER_AGENT,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            await page.goto("https://www.xiaohongshu.com",
                            wait_until="domcontentloaded", timeout=30000)
            await wait_for_login(page, ctx)

            # Navigate to the search results page directly (UI path)
            url = f"https://www.xiaohongshu.com/search_result?keyword={quote(KEYWORD)}&source=web_search_result_notes"
            log.info("navigating to %s", url)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            log.info("waiting 6s for results to render...")
            await asyncio.sleep(6)

            # Try several selectors that XHS uses for search result cards
            selectors = [
                "section.note-item",
                ".feeds-page section",
                "div[data-v-search-result-notes]",
                "section[class*='note-item']",
                "a.cover[href*='/search_result/']",
                "a[href^='/search_result/'][class*='cover']",
                ".note-item",
                ".search-result-container .note-item",
            ]
            counts = {}
            for sel in selectors:
                try:
                    counts[sel] = await page.locator(sel).count()
                except Exception:
                    counts[sel] = -1
            log.info("selector counts: %s", counts)

            # Print the first few cards' textual content using whichever selector hit
            picked = next((s for s, n in counts.items() if n and n > 0 and n != -1), None)
            if picked:
                log.info("using selector %r", picked)
                html_dump = await page.locator(picked).first.evaluate("el => el.outerHTML.slice(0, 600)")
                log.info("first card outerHTML (truncated): %s", html_dump)
                texts = await page.locator(picked).all_inner_texts()
                for i, t in enumerate(texts[:5]):
                    log.info("card[%d]: %s", i, t.replace("\n", " | ")[:160])
            else:
                # save a screenshot + page HTML snippet for diagnosis
                shot = profile.parent / "search_dom_debug.png"
                await page.screenshot(path=str(shot))
                html = (await page.content())[:1500]
                log.info("no card selector matched. screenshot=%s", shot)
                log.info("page html prefix:\n%s", html)

            # ── STEP 3: try navigating into the first note and reading comments ─
            if picked:
                href = await page.locator(picked).first.locator("a.cover").get_attribute("href")
                if href and href.startswith("/"):
                    note_url = "https://www.xiaohongshu.com" + href
                    log.info("\n=== STEP 3: navigate to note %s ===", note_url)
                    await page.goto(note_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(5)

                    # Look for comment containers
                    comment_selectors = [
                        ".comment-item",
                        ".commentList .comment",
                        ".comments-container .item",
                        "div[class*='comment'][class*='item']",
                        ".reds-comment",
                    ]
                    ccounts = {}
                    for sel in comment_selectors:
                        try:
                            ccounts[sel] = await page.locator(sel).count()
                        except Exception:
                            ccounts[sel] = -1
                    log.info("comment selector counts: %s", ccounts)
                    cpicked = next((s for s, n in ccounts.items() if n and n > 0 and n != -1), None)
                    if cpicked:
                        log.info("✓ comments load via DOM with selector %r", cpicked)
                        ctexts = await page.locator(cpicked).all_inner_texts()
                        for i, t in enumerate(ctexts[:5]):
                            log.info("comment[%d]: %s", i, t.replace("\n", " | ")[:160])
                    else:
                        log.warning("✗ no comments found in DOM — check screenshot")
                        shot = profile.parent / "note_dom_debug.png"
                        await page.screenshot(path=str(shot))
                        log.info("note page screenshot: %s", shot)
        finally:
            await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
