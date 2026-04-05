"""Xiaohongshu API client using the xhs library with Playwright-based signing.

Uses the xhs library (ReaJason/xhs) for API methods, but replaces its
outdated pure-Python signing with real browser-based signing via Playwright.
This calls window._webmsxyw() in a headless Chromium to generate valid
x-s, x-t, x-s-common headers that pass XHS's server-side verification.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from xhs import XhsClient as _XhsClient

from findit.config import settings
from findit.crawler.sign import USER_AGENT, PlaywrightSigner

logger = logging.getLogger(__name__)

# Common search keywords for dating-related content
SEARCH_KEYWORDS = [
    "找对象", "找男友", "找搭子", "蹲boyfriend", "脱单",
    "相亲", "CPDD", "征男友", "找另一半", "单身交友",
]

# Keywords/phrases that signal dating intent in comments.
# Using longer phrases instead of single characters like "找" or "求"
# to reduce false positives from non-dating comments.
COMMENT_DATING_KEYWORDS = [
    # Explicit dating-seeking phrases
    "蹲一个", "蹲男友", "蹲对象", "蹲男朋友", "蹲女友", "蹲女朋友",
    "找对象", "找男友", "找男朋友", "找女友", "找女朋友", "找另一半",
    "求脱单", "求认识", "求交友",
    # Status keywords (still specific enough)
    "单身", "脱单", "交友", "同城",
    # Self-intro style comments
    "坐标", "互相了解",
    # Code words / abbreviations
    "私聊", "dd", "cpdd", "CPDD",
    # Condition-listing comments (people posting their stats)
    "身高1", "本科", "硕士", "研究生",
]


class XHSClient:
    """Async wrapper around the xhs library's XhsClient.

    Uses Playwright-based signing for valid request headers.
    The xhs library is synchronous, so all API calls are wrapped
    with asyncio.to_thread() to avoid blocking the event loop.

    Must call ``await client.setup()`` before use and
    ``await client.close()`` when done.
    """

    WEB_URL = "https://www.xiaohongshu.com"

    def __init__(self, cookie: str | None = None):
        self.cookie = cookie or settings.xhs_cookie
        self._delay_min = settings.crawl_request_delay_min
        self._delay_max = settings.crawl_request_delay_max

        # Extract a1 and webId from the cookie string for the signer.
        # These are device identifiers needed so the browser-generated
        # signature matches the cookies sent in HTTP requests.
        cookie_dict = _cookie_str_to_dict(self.cookie)
        self._signer = PlaywrightSigner(
            a1=cookie_dict.get("a1", ""),
            web_id=cookie_dict.get("webId", ""),
        )
        self._client: _XhsClient | None = None

    async def setup(self) -> None:
        """Start the Playwright browser and initialize the xhs client.

        Must be called once before making any API requests.
        """
        await self._signer.start()
        self._client = _XhsClient(
            cookie=self.cookie,
            sign=self._signer.sign_sync,
            user_agent=USER_AGENT,
        )

    async def close(self) -> None:
        """Shut down the Playwright browser."""
        await self._signer.close()

    def _ensure_client(self) -> _XhsClient:
        if self._client is None:
            raise RuntimeError("XHSClient not initialized — call await client.setup() first")
        return self._client

    async def _sleep(self) -> None:
        """Random delay between requests to avoid rate limits."""
        delay = random.uniform(self._delay_min, self._delay_max)
        await asyncio.sleep(delay)

    # ── Step 1: Search posts by keyword ─────────────────────────────────

    async def search_notes(
        self,
        keyword: str,
        sort: str = "time_descending",
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Xiaohongshu notes by keyword.

        Returns a list of note summary dicts with normalized field names.
        """
        await self._sleep()
        try:
            # xhs library returns the "data" portion of the API response
            data = await asyncio.to_thread(
                self._ensure_client().get_note_by_keyword,
                keyword,
                page=page,
                page_size=page_size,
            )

            items = data.get("items", [])
            results = []
            for item in items:
                note_card = item.get("note_card", {})
                user = note_card.get("user", {})
                results.append({
                    "id": item.get("id", ""),
                    "title": note_card.get("title", ""),
                    "desc": note_card.get("desc", ""),
                    "content": (
                        note_card.get("title", "") + "\n" + note_card.get("desc", "")
                    ),
                    "user_id": user.get("user_id", ""),
                    "user_nickname": user.get("nickname", ""),
                    "user_avatar": user.get("avatar", ""),
                    "likes": note_card.get("interact_info", {}).get("liked_count", "0"),
                    "image_list": [
                        img.get("url_default", "")
                        for img in note_card.get("image_list", [])
                    ],
                    "time": note_card.get("time"),
                    "ip_location": note_card.get("ip_location", ""),
                })
            logger.info(
                "Search '%s' page %d returned %d results", keyword, page, len(results)
            )
            return results
        except Exception:
            logger.exception("Failed to search notes for keyword '%s'", keyword)
            return []

    # ── Step 2: Get comments on a post ──────────────────────────────────

    async def get_note_comments(
        self, note_id: str, cursor: str = "", page_size: int = 20
    ) -> tuple[list[dict[str, Any]], str]:
        """Fetch comments for a note.

        Returns (comments_list, next_cursor). Empty cursor means no more pages.
        """
        await self._sleep()
        try:
            data = await asyncio.to_thread(
                self._ensure_client().get_note_comments, note_id, cursor=cursor
            )

            comments_raw = data.get("comments", [])
            next_cursor = data.get("cursor", "")
            has_more = data.get("has_more", False)

            comments = []
            for c in comments_raw:
                user_info = c.get("user_info", {})
                comments.append({
                    "comment_id": c.get("id", ""),
                    "content": c.get("content", ""),
                    "user_id": user_info.get("user_id", ""),
                    "nickname": user_info.get("nickname", ""),
                    "avatar": user_info.get("image", ""),
                    "ip_location": c.get("ip_location", ""),
                    "like_count": c.get("like_count", 0),
                    "create_time": c.get("create_time"),
                })
            logger.info(
                "Note %s comments: got %d, has_more=%s",
                note_id,
                len(comments),
                has_more,
            )
            return comments, next_cursor if has_more else ""
        except Exception:
            logger.exception("Failed to get comments for note %s", note_id)
            return [], ""

    def filter_dating_comments(self, comments: list[dict]) -> list[dict]:
        """Filter comments that show dating intent based on keywords."""
        matches = []
        for c in comments:
            content_lower = c.get("content", "").lower()
            if any(kw in content_lower for kw in COMMENT_DATING_KEYWORDS):
                matches.append(c)
        return matches

    # ── Step 3: Get user profile ────────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Fetch a user's public profile information."""
        await self._sleep()
        try:
            user_data = await asyncio.to_thread(
                self._ensure_client().get_user_info, user_id
            )
            return {
                "id": user_id,
                "nickname": user_data.get("basic_info", {}).get("nickname", ""),
                "avatar_url": user_data.get("basic_info", {}).get("image", ""),
                "ip_location": user_data.get("basic_info", {}).get("ip_location", ""),
                "bio": user_data.get("basic_info", {}).get("desc", ""),
                "age_tag": user_data.get("basic_info", {}).get("age", ""),
                "followers": _safe_int(
                    user_data.get("interactions", [{}])[0].get("count", "0")
                    if user_data.get("interactions")
                    else 0
                ),
                "following": _safe_int(
                    user_data.get("interactions", [{}])[1].get("count", "0")
                    if len(user_data.get("interactions", [])) > 1
                    else 0
                ),
                "likes_collected": _safe_int(
                    user_data.get("interactions", [{}])[2].get("count", "0")
                    if len(user_data.get("interactions", [])) > 2
                    else 0
                ),
            }
        except Exception:
            logger.exception("Failed to get profile for user %s", user_id)
            return {"id": user_id}

    async def get_user_notes(
        self, user_id: str, cursor: str = "", page_size: int = 15
    ) -> tuple[list[dict[str, Any]], str]:
        """Fetch notes published by a user (for profile analysis)."""
        await self._sleep()
        try:
            data = await asyncio.to_thread(
                self._ensure_client().get_user_notes, user_id, cursor=cursor
            )
            notes = []
            for n in data.get("notes", []):
                notes.append({
                    "note_id": n.get("note_id", ""),
                    "title": n.get("display_title", ""),
                    "cover": n.get("cover", {}).get("url", ""),
                    "likes": n.get("interact_info", {}).get("liked_count", "0"),
                    "type": n.get("type", ""),
                })
            next_cursor = data.get("cursor", "")
            has_more = data.get("has_more", False)
            return notes, next_cursor if has_more else ""
        except Exception:
            logger.exception("Failed to get notes for user %s", user_id)
            return [], ""

    def get_note_url(self, note_id: str) -> str:
        """Build the public URL for a note."""
        return f"{self.WEB_URL}/explore/{note_id}"

    def get_user_url(self, user_id: str) -> str:
        """Build the public URL for a user profile."""
        return f"{self.WEB_URL}/user/profile/{user_id}"


def _safe_int(value: Any) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _cookie_str_to_dict(cookie_str: str) -> dict[str, str]:
    """Parse 'a1=xxx;webId=yyy' into {'a1': 'xxx', 'webId': 'yyy'}."""
    result = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, value = part.split("=", 1)
            result[name.strip()] = value.strip()
    return result
