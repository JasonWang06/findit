"""Single-call diagnostic — bypasses the retry wrapper, prints raw response."""
import asyncio
import logging
from findit.crawler.client import XHSClient
from findit.crawler.sign import USER_AGENT
from findit.config import settings
from xhs import XhsClient as _XhsClient
from findit.crawler.sign import PlaywrightSigner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

async def main():
    cookie = settings.xhs_cookie
    print(f"cookie_len={len(cookie)}")
    cookie_dict = {}
    for part in cookie.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    a1 = cookie_dict.get("a1", "")
    web_id = cookie_dict.get("webId", "")
    print(f"a1={a1[:24]}...  webId={web_id[:24]}...")

    signer = PlaywrightSigner(a1=a1, web_id=web_id)
    await signer.start()
    client = _XhsClient(cookie=cookie, sign=signer.sign_sync, user_agent=USER_AGENT)

    try:
        print("→ search 找对象 page=1")
        data = await asyncio.to_thread(client.get_note_by_keyword, "找对象", page=1, page_size=10)
        items = data.get("items", [])
        print(f"  got {len(items)} items")
        for i in items[:3]:
            n = i.get("note_card", {})
            u = n.get("user", {})
            print(f"   - {i.get('id')} | {u.get('nickname')} | {n.get('title')[:40]}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    finally:
        await signer.close()

if __name__ == "__main__":
    asyncio.run(main())
