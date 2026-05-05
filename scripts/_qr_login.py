"""QR-login → write XHS_COOKIE into findit/.env.

Opens a headed Chromium pointed at xiaohongshu.com. The user scans the QR with
their phone XHS app and confirms on phone. The script auto-detects login by
watching the QR-login modal disappear AND a logged-in user avatar appearing.
Once detected (and cookies stable for 4s), it harvests cookies, writes them
into .env, and closes the browser itself.

Why this approach: the previous "wait for web_session cookie" heuristic
fired too early because XHS sets a placeholder web_session for guests.
DOM-based detection of the post-login state is more robust.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
HARD_TIMEOUT_SEC = 300


def write_env(cookie_str: str) -> None:
    lines: list[str] = []
    found = False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("XHS_COOKIE="):
                lines.append(f"XHS_COOKIE={cookie_str}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"XHS_COOKIE={cookie_str}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    print(f"✅ wrote XHS_COOKIE ({len(cookie_str)} chars) to {ENV_PATH}")


async def is_logged_in(page) -> bool:
    """Return True only when DOM looks like a logged-in user.

    XHS shows the login QR modal in `.login-container` (or similar) on
    guest sessions. Once login completes, that container is removed and
    the side bar shows the user's avatar + a 'side-bar-component .user'
    element. We require: no login modal AND a user avatar present.
    """
    try:
        return await page.evaluate("""
            () => {
                // login modal markers (any of these means NOT logged in)
                const loginSelectors = [
                    '.login-container',
                    '.login-mask',
                    '.qrcode-img',
                    '.login-pannel',
                    '.login-panel',
                    'div[class*="login"][class*="modal"]',
                    'div[class*="qrcode"]',
                ];
                for (const sel of loginSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) return false;
                }
                // logged-in markers (any one is enough)
                const okSelectors = [
                    '.side-bar-component .user',
                    '.user .name',
                    'a[href*="/user/profile/"]',
                    '.avatar-wrapper img',
                    '.user-avatar img',
                ];
                for (const sel of okSelectors) {
                    if (document.querySelector(sel)) return true;
                }
                return false;
            }
        """)
    except Exception:
        return False


async def run() -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()
        print("🌐 opening xiaohongshu.com — scan QR, confirm on phone, this script auto-detects login")
        await page.goto("https://www.xiaohongshu.com", timeout=60000)
        try:
            await page.evaluate("""
                const b = document.createElement('div');
                b.id = '__findit_banner';
                b.textContent = '🔄 等你扫码…登录后会自动抓 cookie 并关闭，无需手动操作';
                b.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#e60023;color:#fff;font:bold 16px/36px sans-serif;text-align:center;padding:6px;box-shadow:0 2px 6px rgba(0,0,0,0.3)';
                document.body.appendChild(b);
            """)
        except Exception:
            pass

        elapsed = 0
        stable_count = 0
        last_snapshot: list[dict] = []
        while browser.is_connected() and elapsed < HARD_TIMEOUT_SEC:
            try:
                last_snapshot = await ctx.cookies()
            except Exception:
                break
            logged_in = await is_logged_in(page)
            if logged_in:
                stable_count += 1
                if stable_count == 1:
                    print(f"🟢 login detected (t={elapsed}s) — confirming cookies are settled…")
            else:
                stable_count = 0
            if stable_count >= 4:  # 4 consecutive checks @ 1s = 4s stable
                print("✅ login confirmed and cookies stable")
                break
            if elapsed and elapsed % 10 == 0 and stable_count == 0:
                names = {c["name"] for c in last_snapshot}
                print(f"⏳ waiting for QR scan… {elapsed}s | cookies={len(last_snapshot)} "
                      f"| web_session={'✓' if 'web_session' in names else '✗'}")
            await asyncio.sleep(1)
            elapsed += 1

        try:
            last_snapshot = await ctx.cookies()
        except Exception:
            pass
        await browser.close()

    if not last_snapshot:
        print("❌ no cookies captured — login likely did not complete")
        return 1

    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in last_snapshot)
    write_env(cookie_str)
    important = ["a1", "webId", "web_session", "customer-sso-sid", "customerClientId",
                 "xsecappid", "gid"]
    for c in last_snapshot:
        if c["name"] in important:
            v = c["value"]
            print(f"   {c['name']}={v[:32]}{'...' if len(v) > 32 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
