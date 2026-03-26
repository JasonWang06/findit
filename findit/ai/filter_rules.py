"""Rule-based filters for author profiles.

Two filter classes:
- SharedFilter: user-independent checks run by the crawler service
  (matchmaker, marketing, empty, inactive, suspicious patterns)
- UserFilter: per-user checks run by the matching service
  (location, age preferences)

Architecture note: these are keyword/heuristic-based filters only.
An LLM screening step can be plugged in later for cases that keywords miss.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Keyword lists ───────────────────────────────────────────────────────

# Matchmaker / agency keywords (checked in nickname + bio)
_MATCHMAKER_KEYWORDS = [
    # 直接身份词
    "红娘", "婚介", "婚恋", "相亲平台", "脱单服务", "牵线",
    "介绍对象", "婚姻介绍", "情感咨询", "恋爱顾问",
    # 服务类话术
    "成功案例", "配对成功", "一对一服务", "实名认证会员",
    "嘉宾资源", "优质男生", "优质女生",
    # 引流话术
    "加v", "加微", "私我领取", "进群",
    "免费介绍", "免费匹配", "免费推荐",
]

# Marketing / promotion keywords
_MARKETING_KEYWORDS = [
    "商务合作", "广告", "推广", "品牌合作", "商业", "带货",
    "测评", "种草合作", "pr",
]

# Dating-related title keywords (for note analysis)
_DATING_TITLE_KEYWORDS = [
    "找对象", "征婚", "找男友", "找女友", "相亲", "单身",
    "脱单", "征男友", "征女友", "找另一半", "找男朋友", "找女朋友",
    "蹲对象", "蹲男友", "蹲女友", "求脱单",
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


def _is_dating_title(title: str) -> bool:
    """Check if a note title is dating-related."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in _DATING_TITLE_KEYWORDS)


# ── Shared Filter (user-independent) ───────────────────────────────────


class SharedFilter:
    """User-independent filters run by the crawler service.

    These checks don't depend on any user's profile or preferences.
    They identify accounts that are unsuitable for ALL users:
    matchmakers, marketing accounts, empty/inactive accounts, etc.
    """

    def evaluate(self, author: dict, posts: list[dict] | None = None) -> tuple[bool, str | None]:
        """Evaluate an author profile.

        Args:
            author: Author profile dict from the database.
            posts: Optional list of the author's posts (for inactive check).

        Returns (should_keep, filter_reason).
        """
        checks = [
            lambda a: self._check_matchmaker(a),
            lambda a: self._check_marketing(a),
            lambda a: self._check_empty_account(a),
            lambda a: self._check_inactive(a, posts),
            lambda a: self._check_suspicious_pattern(a),
        ]
        for check in checks:
            keep, reason = check(author)
            if not keep:
                return False, reason
        return True, None

    def _check_matchmaker(self, author: dict) -> tuple[bool, str | None]:
        """Detect matchmaker / agency accounts via keywords + note patterns."""
        nickname = (author.get("nickname") or "").lower()
        bio = (author.get("bio") or "").lower()
        text = nickname + " " + bio

        # 1. Keyword check on nickname + bio
        for kw in _MATCHMAKER_KEYWORDS:
            if kw in text:
                return False, f"matchmaker_keyword:{kw}"

        # 2. Note content analysis
        notes = _parse_notes(author)
        if len(notes) >= 3:
            keep, reason = self._check_matchmaker_notes(notes)
            if not keep:
                return False, reason

        return True, None

    def _check_matchmaker_notes(self, notes: list[dict]) -> tuple[bool, str | None]:
        """Analyze notes for matchmaker patterns."""
        # 2a. High ratio of dating posts (>60% with 5+ notes)
        dating_count = sum(1 for n in notes if _is_dating_title(n.get("title", "")))

        if len(notes) >= 5:
            ratio = dating_count / len(notes)
            if ratio > 0.6:
                return False, "matchmaker_high_dating_ratio"

        # 2b. Multiple different birth years in titles → posting for multiple people
        # e.g., "95年找对象", "98年征男友", "00年单身" → agency
        ages_found: set[str] = set()
        for n in notes:
            title = n.get("title") or ""
            years = re.findall(r"(\d{2})年", title)
            ages_found.update(years)
        if len(ages_found) >= 3:
            return False, "matchmaker_multiple_ages"

        # 2c. Multiple different heights in titles → posting for multiple people
        heights_found: set[str] = set()
        for n in notes:
            title = n.get("title") or ""
            heights = re.findall(r"(\d{3})\s*cm", title)
            heights_found.update(heights)
        if len(heights_found) >= 3:
            return False, "matchmaker_multiple_heights"

        return True, None

    def _check_marketing(self, author: dict) -> tuple[bool, str | None]:
        """Detect marketing / promo accounts."""
        nickname = (author.get("nickname") or "").lower()
        bio = (author.get("bio") or "").lower()
        text = nickname + " " + bio

        for kw in _MARKETING_KEYWORDS:
            if kw in text:
                return False, f"marketing_keyword:{kw}"

        # High follower count with very few notes → likely bought followers or spam
        followers = author.get("followers", 0)
        notes = _parse_notes(author)

        if followers > 50000 and len(notes) < 5:
            return False, "marketing_high_followers_low_content"

        return True, None

    def _check_empty_account(self, author: dict) -> tuple[bool, str | None]:
        """Filter accounts with no meaningful content."""
        notes = _parse_notes(author)
        following = author.get("following", 0)
        bio = author.get("bio") or ""

        if len(notes) == 0 and following == 0 and not bio.strip():
            return False, "empty_account"

        return True, None

    def _check_inactive(
        self, author: dict, posts: list[dict] | None = None
    ) -> tuple[bool, str | None]:
        """Filter authors whose latest activity is over 90 days ago."""
        # Try to use post timestamps if available
        if posts:
            timestamps = [p.get("created_at") or "" for p in posts]
            latest = max(timestamps, default="")
            if latest:
                try:
                    dt = datetime.fromisoformat(latest)
                    if datetime.now() - dt > timedelta(days=90):
                        return False, "inactive_90days"
                    return True, None
                except ValueError:
                    pass

        # Fallback: check the author's updated_at timestamp
        updated = author.get("updated_at")
        if not updated:
            return True, None

        return True, None

    def _check_suspicious_pattern(self, author: dict) -> tuple[bool, str | None]:
        """Detect suspicious account behavior patterns."""
        nickname = author.get("nickname") or ""
        bio = author.get("bio") or ""

        # Default XHS username + dating posts → likely agency throwaway
        if re.match(r"^小红书用户\w+$", nickname):
            notes = _parse_notes(author)
            if len(notes) >= 3:
                dating_count = sum(1 for n in notes if _is_dating_title(n.get("title", "")))
                if dating_count >= 2:
                    return False, "suspicious_default_name_dating"

        # Contact info in bio (WeChat/phone number) → often agency or scam
        if re.search(r"v\s*[:：]\s*\w+|微信\s*[:：]?\s*\w+|\d{11}", bio):
            return False, "suspicious_contact_in_bio"

        return True, None


# ── User Filter (per-user) ─────────────────────────────────────────────


class UserFilter:
    """Per-user filters applied when generating matches.

    These checks depend on a specific user's preferences:
    location, age range, etc.
    """

    def __init__(self, user_city: str = "", allow_remote: bool = False,
                 age_min: int | None = None, age_max: int | None = None):
        self.user_city = user_city
        self.allow_remote = allow_remote
        self.age_min = age_min
        self.age_max = age_max

    def evaluate(self, author: dict) -> tuple[bool, str | None]:
        """Evaluate whether an author matches user preferences."""
        checks = [
            self._check_location,
        ]
        for check in checks:
            keep, reason = check(author)
            if not keep:
                return False, reason
        return True, None

    def _check_location(self, author: dict) -> tuple[bool, str | None]:
        """Filter by geographic location."""
        if self.allow_remote or not self.user_city:
            return True, None

        location = author.get("ip_location") or ""
        if not location:
            return True, None  # Unknown location, keep for now

        if self.user_city not in location:
            return False, f"location_mismatch:{location}"

        return True, None


# ── Backward compatibility alias ────────────────────────────────────────

# Keep RuleFilter as an alias for code that still references it.
# It combines shared + user filtering like the old implementation.
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
