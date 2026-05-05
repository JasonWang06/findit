"""Rule-based filters for author profiles.

Implements the rules in `docs/DATA_SPEC.md`:

- SharedFilter: user-independent matchmaker checks
    - Rule A: "红娘" appears in nickname / bio / post.content / notes_summary
    - Rule B: post.content matches a 代发-style proxy-post phrase
  Optionally enforces §2 minimum-data bar (only after Step 3 / when `final=True`).
- UserFilter: per-user location filtering for the matching service.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Rule A: matchmaker keyword ──────────────────────────────────────────

MATCHMAKER_KEYWORD = "红娘"

# ── Rule B: proxy-post (代发) signals ────────────────────────────────────

PROXY_POST_KEYWORDS = [
    # 显式代发
    "代发", "代友发", "帮朋友发", "帮闺蜜发", "代闺蜜发",
    "替朋友发", "朋友委托", "本人委托",
    # 撇清"非本人"
    "非本人", "不是本人", "不是我本人",
    # 本人不在
    "本人不在小红书", "本人没小红书", "本人不刷小红书",
]
# 注：早期版本曾把"已获本人同意/经本人同意/本人同意"也当代发关键词，
# 实际数据中误伤法律披露语境（如"其本人同意公开"用于诉讼证据）。
# 真代发帖几乎都会同时出现"代发/代闺蜜发/帮朋友发"等显式信号，删除单独
# "本人同意"判定后召回率影响极小，且消除假阳性。

PROXY_POST_PATTERNS = [
    re.compile(r"代[一-龥]{1,3}发"),   # 代闺蜜发 / 代表妹发
    re.compile(r"帮[一-龥]{1,3}发"),   # 帮朋友发 / 帮表姐发
    re.compile(r"替[一-龥]{1,3}发"),   # 替哥哥发
]


def _parse_notes(author: dict) -> list[dict]:
    """Extract notes_summary as a list, handling JSON string or list."""
    notes = author.get("notes_summary")
    if isinstance(notes, str):
        try:
            notes = json.loads(notes)
        except (json.JSONDecodeError, TypeError):
            return []
    return notes if isinstance(notes, list) else []


# ── Shared Filter (user-independent) ───────────────────────────────────


class SharedFilter:
    """User-independent matchmaker filter (§3 of DATA_SPEC.md).

    Two rules, both meaning permanent exclusion:
      - matchmaker_keyword:    "红娘" anywhere
      - matchmaker_proxy_post: 代发 / 已获本人同意 / 本人不在小红书 / etc.
    """

    def evaluate(
        self,
        author: dict,
        posts: list[dict] | None = None,
        final: bool = False,
    ) -> tuple[bool, str | None]:
        """Evaluate an author profile.

        Args:
            author: row from `authors` (dict).
            posts: posts/comments by this author (rows from `posts`).
            final: True after Step 3 (profile crawled). Enables the §2
                minimum-data bar — without it, authors lacking
                ip_location/content stay un-filtered awaiting Step 3.

        Returns (should_keep, filter_reason).
        """
        posts = posts or []

        keep, reason = self._check_matchmaker_keyword(author, posts)
        if not keep:
            return False, reason

        keep, reason = self._check_proxy_post(posts)
        if not keep:
            return False, reason

        if final:
            keep, reason = self._check_min_quality(author, posts)
            if not keep:
                return False, reason

        return True, None

    # — Rule A —
    def _check_matchmaker_keyword(
        self, author: dict, posts: list[dict]
    ) -> tuple[bool, str | None]:
        haystacks = [
            author.get("nickname") or "",
            author.get("bio") or "",
        ]
        haystacks.extend((p.get("content") or "") for p in posts)
        for note in _parse_notes(author):
            haystacks.append(note.get("title") or "")
            haystacks.append(note.get("content") or "")

        for text in haystacks:
            if MATCHMAKER_KEYWORD in text:
                return False, "matchmaker_keyword"
        return True, None

    # — Rule B —
    def _check_proxy_post(self, posts: list[dict]) -> tuple[bool, str | None]:
        for p in posts:
            content = p.get("content") or ""
            if not content:
                continue
            if any(kw in content for kw in PROXY_POST_KEYWORDS):
                return False, "matchmaker_proxy_post"
            if any(pat.search(content) for pat in PROXY_POST_PATTERNS):
                return False, "matchmaker_proxy_post"
        return True, None

    # — §2 minimum-data bar (final=True only) —
    def _check_min_quality(
        self, author: dict, posts: list[dict]
    ) -> tuple[bool, str | None]:
        if not (author.get("ip_location") or "").strip():
            return False, "low_quality_content"
        bio = (author.get("bio") or "").strip()
        substantial_post = any(
            len((p.get("content") or "").strip()) >= 12 for p in posts
        )
        if not bio and not substantial_post:
            return False, "low_quality_content"
        return True, None


# ── User Filter (per-user) ─────────────────────────────────────────────


class UserFilter:
    """Per-user filters applied when generating matches.

    Currently only geographic location.
    """

    def __init__(
        self,
        user_city: str = "",
        allow_remote: bool = False,
        age_min: int | None = None,
        age_max: int | None = None,
    ):
        self.user_city = user_city
        self.allow_remote = allow_remote
        self.age_min = age_min
        self.age_max = age_max

    def evaluate(self, author: dict) -> tuple[bool, str | None]:
        return self._check_location(author)

    def _check_location(self, author: dict) -> tuple[bool, str | None]:
        if self.allow_remote or not self.user_city:
            return True, None

        location = author.get("ip_location") or ""
        if not location:
            return True, None  # Unknown location, keep for now

        if self.user_city not in location:
            return False, f"location_mismatch:{location}"

        return True, None


# ── Backward compatibility alias ────────────────────────────────────────


class RuleFilter:
    """Legacy wrapper combining SharedFilter + UserFilter."""

    def __init__(self, user_city: str = "深圳", allow_remote: bool = False):
        self.shared = SharedFilter()
        self.user = UserFilter(user_city=user_city, allow_remote=allow_remote)

    def evaluate(self, author: dict) -> tuple[bool, str | None]:
        keep, reason = self.shared.evaluate(author)
        if not keep:
            return False, reason
        return self.user.evaluate(author)
