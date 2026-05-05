"""Smoke test for the browser-driven crawler.

Walks through:
  1. launch persistent Chromium (will prompt QR if no saved login)
  2. search_notes("深圳找对象") — POST /api/sns/web/v1/search/notes
  3. for the first result, fetch comments + dating-intent filter
"""
import asyncio
import logging
import sys

from findit.crawler.client import XHSClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

KEYWORD = "深圳找对象"

async def main():
    client = XHSClient()
    await client.setup()
    try:
        print(f"\n=== STEP 1: search_notes(keyword={KEYWORD!r}, page=1) ===")
        results = await client.search_notes(KEYWORD, page=1, page_size=10)
        print(f"→ {len(results)} results")
        for r in results[:5]:
            print(f"   id={r['id']} | by={r['user_nickname']!r} | "
                  f"loc={r['ip_location']!r} | likes={r['likes']}")
            print(f"     title: {r['title'][:60]}")

        if not results:
            print("\nno results — likely account-level risk control (code 300011)")
            return 1

        first = results[0]
        print(f"\n=== STEP 2: get_note_comments(note_id={first['id']}) ===")
        comments, _ = await client.get_note_comments(first["id"])
        print(f"→ {len(comments)} comments")
        for c in comments[:3]:
            print(f"   {c['nickname']!r} ({c['ip_location']!r}): {c['content'][:50]}")

        dating = client.filter_dating_comments(comments)
        print(f"→ {len(dating)} dating-intent comments")
        return 0
    finally:
        await client.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
