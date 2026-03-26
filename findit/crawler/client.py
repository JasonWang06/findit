"""Low-level HTTP client for Xiaohongshu web/mobile API.

This module wraps the public-facing XHS endpoints used by the web app.
Cookie-based authentication is required (obtained from a logged-in browser session).
All public data only — no private messages or restricted content.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
from typing import Any
from urllib.parse import quote

import httpx

from findit.config import settings

logger = logging.getLogger(__name__)

# Common search keywords for dating-related content
SEARCH_KEYWORDS = [
    "找对象", "找男友", "找搭子", "蹲boyfriend", "脱单",
    "相亲", "CPDD", "征男友", "找另一半", "单身交友",
]

# Keywords that signal dating intent in comments
COMMENT_DATING_KEYWORDS = [
    "蹲", "求", "找", "交友", "同城", "脱单", "单身",
    "求认识", "坐标", "互相了解", "私聊", "dd",
]

_BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
}


def _sign_params(api_path: str, params: dict | None = None) -> dict[str, str]:
    """Generate a basic request signature.

    NOTE: This is a simplified signing mechanism. The real XHS web app uses
    a more complex JS-based signature (X-s, X-t headers). For the MVP,
    we rely on cookie-based auth which often doesn't require full signing.
    If requests get blocked, integrate a proper signing solution
    (e.g., via playwright or a signing service).
    """
    ts = str(int(time.time() * 1000))
    payload = f"{api_path}{ts}{json.dumps(params or {}, separators=(',', ':'))}"
    sign = hashlib.md5(payload.encode()).hexdigest()
    return {"X-t": ts, "X-s": sign}


class XHSClient:
    """Async HTTP client for Xiaohongshu public API."""

    BASE_URL = "https://edith.xiaohongshu.com"
    WEB_URL = "https://www.xiaohongshu.com"

    def __init__(self, cookie: str | None = None):
        self.cookie = cookie or settings.xhs_cookie
        self._delay_min = settings.crawl_request_delay_min
        self._delay_max = settings.crawl_request_delay_max

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h = {**_BASE_HEADERS, "Cookie": self.cookie}
        if extra:
            h.update(extra)
        return h

    async def _sleep(self) -> None:
        """Random delay between requests to avoid rate limits."""
        delay = random.uniform(self._delay_min, self._delay_max)
        await asyncio.sleep(delay)

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        sign_headers = _sign_params(path, params)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers=self._headers(sign_headers),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") is False:
                logger.warning("API error on %s: %s", path, data.get("msg"))
            return data

    async def _post(self, path: str, payload: dict | None = None) -> dict[str, Any]:
        sign_headers = _sign_params(path, payload)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}{path}",
                json=payload,
                headers=self._headers(sign_headers),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") is False:
                logger.warning("API error on %s: %s", path, data.get("msg"))
            return data

    # ── Step 1: Search posts by keyword ─────────────────────────────────

    async def search_notes(
        self,
        keyword: str,
        sort: str = "time_descending",
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Xiaohongshu notes by keyword.

        Returns a list of note summary dicts with fields:
        id, title, desc, user (id, nickname, avatar), likes, image_list, time.
        """
        await self._sleep()
        path = "/api/sns/web/v1/search/notes"
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "note_type": 0,  # 0=all, 1=image, 2=video
        }
        try:
            data = await self._post(path, payload)
            items = data.get("data", {}).get("items", [])
            results = []
            for item in items:
                note_card = item.get("note_card", {})
                user = note_card.get("user", {})
                results.append({
                    "id": item.get("id", ""),
                    "title": note_card.get("title", ""),
                    "desc": note_card.get("desc", ""),
                    "content": note_card.get("title", "") + "\n" + note_card.get("desc", ""),
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
            logger.info("Search '%s' page %d returned %d results", keyword, page, len(results))
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
        path = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp",
        }
        try:
            data = await self._get(path, params)
            comment_data = data.get("data", {})
            comments_raw = comment_data.get("comments", [])
            next_cursor = comment_data.get("cursor", "")
            has_more = comment_data.get("has_more", False)

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
            logger.info("Note %s comments: got %d, has_more=%s", note_id, len(comments), has_more)
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
        path = "/api/sns/web/v1/user/otherinfo"
        params = {"target_user_id": user_id}
        try:
            data = await self._get(path, params)
            user_data = data.get("data", {})
            return {
                "id": user_id,
                "nickname": user_data.get("basic_info", {}).get("nickname", ""),
                "avatar_url": user_data.get("basic_info", {}).get("image", ""),
                "ip_location": user_data.get("basic_info", {}).get("ip_location", ""),
                "bio": user_data.get("basic_info", {}).get("desc", ""),
                "age_tag": user_data.get("basic_info", {}).get("age", ""),
                "followers": int(user_data.get("interactions", [{}])[0].get("count", "0") if user_data.get("interactions") else 0),
                "following": int(user_data.get("interactions", [{}])[1].get("count", "0") if len(user_data.get("interactions", [])) > 1 else 0),
                "likes_collected": int(user_data.get("interactions", [{}])[2].get("count", "0") if len(user_data.get("interactions", [])) > 2 else 0),
            }
        except Exception:
            logger.exception("Failed to get profile for user %s", user_id)
            return {"id": user_id}

    async def get_user_notes(
        self, user_id: str, cursor: str = "", page_size: int = 15
    ) -> tuple[list[dict[str, Any]], str]:
        """Fetch notes published by a user (for profile analysis)."""
        await self._sleep()
        path = "/api/sns/web/v1/user_posted"
        params = {
            "user_id": user_id,
            "cursor": cursor,
            "num": page_size,
            "image_formats": "jpg,webp",
        }
        try:
            data = await self._get(path, params)
            notes_data = data.get("data", {})
            notes = []
            for n in notes_data.get("notes", []):
                notes.append({
                    "note_id": n.get("note_id", ""),
                    "title": n.get("display_title", ""),
                    "cover": n.get("cover", {}).get("url", ""),
                    "likes": n.get("interact_info", {}).get("liked_count", "0"),
                    "type": n.get("type", ""),
                })
            next_cursor = notes_data.get("cursor", "")
            has_more = notes_data.get("has_more", False)
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
