"""Playwright-based request signing for Xiaohongshu API.

The xhs library's built-in pure-Python sign() function is outdated.
This module launches a headless Chromium browser, loads the XHS web app,
and calls the real JavaScript signing function (window._webmsxyw) to
generate valid x-s, x-t, x-s-common headers.

The browser is started once and reused for all signing requests.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from playwright.async_api import Page, async_playwright

logger = logging.getLogger(__name__)

# Stealth evasions to prevent Playwright detection.
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


class PlaywrightSigner:
    """Manages a persistent headless browser for XHS request signing.

    Usage::

        signer = PlaywrightSigner(cookie="a1=xxx;web_session=yyy;...")
        await signer.start()   # launches browser, loads XHS page

        # Called by XhsClient as external_sign callback (sync)
        headers = signer.sign_sync("/api/sns/web/v1/search/notes", data, a1, web_session)

        await signer.close()   # cleanup
    """

    XHS_HOME = "https://www.xiaohongshu.com"

    def __init__(self, cookie: str = ""):
        self._cookie = cookie
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self._started = False
        self._async_lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """Launch browser, inject stealth, navigate to XHS, set cookies."""
        if self._started:
            return

        # Save a reference to the running event loop so sign_sync()
        # can dispatch calls back from worker threads.
        self._loop = asyncio.get_running_loop()

        logger.info("Starting Playwright browser for XHS signing...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Inject stealth before any page loads
        await self._context.add_init_script(_STEALTH_JS)

        # Set cookies from the cookie string
        if self._cookie:
            cookies = _parse_cookie_string(self._cookie, ".xiaohongshu.com")
            await self._context.add_cookies(cookies)

        self._page = await self._context.new_page()
        await self._page.goto(
            self.XHS_HOME,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        # Wait for the signing function to be available
        await self._page.wait_for_function(
            "() => typeof window._webmsxyw === 'function'",
            timeout=15000,
        )
        logger.info("Playwright signer ready — window._webmsxyw available")
        self._started = True

    async def sign(self, uri: str, data: Any = None, a1: str = "", web_session: str = "") -> dict[str, str]:
        """Generate x-s, x-t, x-s-common headers via browser JS."""
        if not self._started or not self._page:
            raise RuntimeError("PlaywrightSigner not started — call start() first")

        async with self._async_lock:
            data_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if data else ""

            try:
                result = await self._page.evaluate(
                    "([url, data]) => window._webmsxyw(url, data)",
                    [uri, data_str],
                )
            except Exception:
                logger.exception("window._webmsxyw call failed, reloading page...")
                await self._page.reload(wait_until="domcontentloaded", timeout=30000)
                await self._page.wait_for_function(
                    "() => typeof window._webmsxyw === 'function'",
                    timeout=15000,
                )
                result = await self._page.evaluate(
                    "([url, data]) => window._webmsxyw(url, data)",
                    [uri, data_str],
                )

            x_s = result.get("X-s", "")
            x_t = str(result.get("X-t", ""))

            # x-s-common may be returned by _webmsxyw or needs to be
            # generated from the Python helper as a fallback.
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
        """Synchronous wrapper for the xhs library's external_sign callback.

        The xhs library calls this synchronously from its requests-based
        HTTP methods. Since client.py wraps xhs calls with asyncio.to_thread(),
        this runs in a worker thread. We use run_coroutine_threadsafe() to
        dispatch the async sign() call back to the main event loop where
        Playwright lives.
        """
        if self._loop is None:
            raise RuntimeError("PlaywrightSigner not started — call start() first")

        future = asyncio.run_coroutine_threadsafe(
            self.sign(uri, data, a1, web_session),
            self._loop,
        )
        return future.result(timeout=30)

    async def close(self) -> None:
        """Shut down browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._started = False
        logger.info("Playwright signer closed")


def _build_xs_common(x_s: str, x_t: str, a1: str) -> str:
    """Build x-s-common header using the xhs library's encoding utilities.

    This is needed when window._webmsxyw doesn't return X-s-common directly.
    Uses the same encoding as xhs.help.sign() but with the browser-generated
    x-s and x-t values.
    """
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


def _parse_cookie_string(cookie_str: str, domain: str) -> list[dict]:
    """Convert 'a1=xxx;b=yyy' into Playwright cookie dicts."""
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
        })
    return cookies
