"""Playwright-based request signing for Xiaohongshu API.

The xhs library's built-in pure-Python sign() function is outdated.
This module launches a headless Chromium browser, loads the XHS web app,
and calls the real JavaScript signing function (window._webmsxyw) to
generate valid x-s, x-t, x-s-common headers.

The browser is started once and reused for all signing requests.
If the browser crashes or signing fails repeatedly, it auto-restarts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from playwright.async_api import Page, async_playwright

from findit.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
}
"""

_MAX_SIGN_RETRIES = 3


class PlaywrightSigner:
    """Manages a persistent headless browser for XHS request signing.

    Auto-restarts if the browser dies or signing fails repeatedly.
    """

    XHS_HOME = "https://www.xiaohongshu.com"

    def __init__(self, a1: str = "", web_id: str = ""):
        self._a1 = a1
        self._web_id = web_id
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self._started = False
        self._async_lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._consecutive_failures = 0

    async def start(self) -> None:
        if self._started:
            return

        self._loop = asyncio.get_running_loop()

        page_timeout = settings.playwright_page_timeout
        sign_timeout = settings.playwright_sign_timeout

        logger.info("Starting Playwright browser for XHS signing...")
        self._playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]
        proxy_cfg = None
        if settings.crawl_proxy:
            proxy_cfg = {"server": settings.crawl_proxy}

        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=launch_args,
            proxy=proxy_cfg,
        )
        self._context = await self._browser.new_context(user_agent=USER_AGENT)
        await self._context.add_init_script(_STEALTH_JS)

        a1 = self._a1
        web_id = self._web_id
        if not a1 or not web_id:
            from xhs.help import get_a1_and_web_id
            a1, web_id = get_a1_and_web_id()
        await self._context.add_cookies([
            {"name": "a1", "value": a1, "domain": ".xiaohongshu.com", "path": "/"},
            {"name": "webId", "value": web_id, "domain": ".xiaohongshu.com", "path": "/"},
        ])

        self._page = await self._context.new_page()
        await self._page.goto(
            self.XHS_HOME,
            wait_until="domcontentloaded",
            timeout=page_timeout,
        )

        await self._page.wait_for_function(
            "() => typeof window._webmsxyw === 'function'",
            timeout=sign_timeout,
        )
        logger.info("Playwright signer ready — window._webmsxyw available")
        self._started = True
        self._consecutive_failures = 0

    async def restart(self) -> None:
        logger.warning("Restarting Playwright signer...")
        await self.close()
        await self.start()

    async def sign(self, uri: str, data: Any = None, a1: str = "", web_session: str = "") -> dict[str, str]:
        if not self._started or not self._page:
            raise RuntimeError("PlaywrightSigner not started — call start() first")

        async with self._async_lock:
            data_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if data else ""

            for attempt in range(_MAX_SIGN_RETRIES):
                try:
                    result = await self._page.evaluate(
                        "([url, data]) => window._webmsxyw(url, data)",
                        [uri, data_str],
                    )
                    self._consecutive_failures = 0
                    break
                except Exception:
                    self._consecutive_failures += 1
                    if attempt < _MAX_SIGN_RETRIES - 1:
                        logger.warning(
                            "Sign attempt %d/%d failed, reloading page...",
                            attempt + 1, _MAX_SIGN_RETRIES,
                        )
                        try:
                            await self._page.reload(
                                wait_until="domcontentloaded",
                                timeout=settings.playwright_page_timeout,
                            )
                            await self._page.wait_for_function(
                                "() => typeof window._webmsxyw === 'function'",
                                timeout=settings.playwright_sign_timeout,
                            )
                        except Exception:
                            logger.warning("Page reload failed, will retry sign anyway")
                    else:
                        logger.error("All %d sign attempts exhausted", _MAX_SIGN_RETRIES)
                        raise

            x_s = result.get("X-s", "")
            x_t = str(result.get("X-t", ""))

            x_s_common = result.get("X-s-common", "")
            if not x_s_common:
                x_s_common = _build_xs_common(x_s, x_t, a1)

            headers = {
                "x-s": x_s,
                "x-t": x_t,
                "x-s-common": x_s_common,
            }
            logger.debug("Signed %s → x-t=%s", uri[:60], headers["x-t"])
            return headers

    def sign_sync(self, uri: str, data: Any = None, a1: str = "", web_session: str = "") -> dict[str, str]:
        if self._loop is None:
            raise RuntimeError("PlaywrightSigner not started — call start() first")

        future = asyncio.run_coroutine_threadsafe(
            self.sign(uri, data, a1, web_session),
            self._loop,
        )
        return future.result(timeout=settings.crawl_request_timeout)

    async def close(self) -> None:
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                logger.debug("Browser close error (ignored)")
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                logger.debug("Playwright stop error (ignored)")
            self._playwright = None
        self._page = None
        self._context = None
        self._started = False
        logger.info("Playwright signer closed")


def _build_xs_common(x_s: str, x_t: str, a1: str) -> str:
    from xhs.help import b64Encode, encodeUtf8, mrc

    common = {
        "s0": 5,
        "s1": "",
        "x0": "1",
        "x1": "3.2.0",
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.0.0",
        "x5": a1,
        "x6": x_t,
        "x7": x_s,
        "x8": "",
        "x9": mrc(x_t + x_s) if x_t and x_s else 0,
        "x10": 1,
    }
    encode_str = encodeUtf8(json.dumps(common, separators=(",", ":")))
    return b64Encode(encode_str)
