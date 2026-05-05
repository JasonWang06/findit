"""Open the persistent profile context briefly, list key cookies, exit."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE = Path(__file__).resolve().parent.parent / "data/chromium_profile"

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=True,
        )
        try:
            cookies = await ctx.cookies("https://www.xiaohongshu.com")
            print(f"total cookies: {len(cookies)}")
            interesting = ["web_session", "a1", "webId", "xsecappid", "gid",
                           "customer-sso-sid", "customerClientId"]
            for c in cookies:
                if c["name"] in interesting:
                    v = c["value"]
                    print(f"  {c['name']:24} len={len(v):3}  {v[:32]}{'…' if len(v) > 32 else ''}")
        finally:
            await ctx.close()

asyncio.run(main())
