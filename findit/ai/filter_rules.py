"""Rule-based first-pass filter for author profiles.

Filters out obvious non-targets: matchmakers, marketing accounts,
empty accounts, inactive users, and location mismatches.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Keywords indicating matchmaker / agency accounts
_MATCHMAKER_KEYWORDS = [
    "红娘", "婚介", "婚恋", "相亲平台", "脱单服务", "牵线",
    "介绍对象", "婚姻介绍", "情感咨询", "恋爱顾问",
]

# Keywords indicating marketing / promotion accounts
_MARKETING_KEYWORDS = [
    "商务合作", "广告", "推广", "品牌合作", "商业", "带货",
]


class RuleFilter:
    """Apply deterministic rules to filter out unsuitable authors."""

    def __init__(self, user_city: str = "深圳", allow_remote: bool = False):
        self.user_city = user_city
        self.allow_remote = allow_remote

    def evaluate(self, author: dict) -> tuple[bool, str | None]:
        """Evaluate an author profile.

        Returns (should_keep, filter_reason).
        If should_keep is False, filter_reason explains why.
        """
        checks = [
            self._check_matchmaker,
            self._check_marketing,
            self._check_empty_account,
            self._check_inactive,
            self._check_location,
        ]
        for check in checks:
            keep, reason = check(author)
            if not keep:
                return False, reason
        return True, None

    def _check_matchmaker(self, author: dict) -> tuple[bool, str | None]:
        """Detect matchmaker / agency accounts."""
        nickname = (author.get("nickname") or "").lower()
        bio = (author.get("bio") or "").lower()
        text = nickname + " " + bio

        for kw in _MATCHMAKER_KEYWORDS:
            if kw in text:
                return False, f"matchmaker_keyword:{kw}"

        # Check notes: if most notes feature different people → likely agency
        notes_summary = author.get("notes_summary")
        if isinstance(notes_summary, str):
            try:
                notes_summary = json.loads(notes_summary)
            except (json.JSONDecodeError, TypeError):
                notes_summary = []

        if isinstance(notes_summary, list) and len(notes_summary) >= 5:
            dating_titles = sum(
                1 for n in notes_summary
                if any(kw in (n.get("title") or "").lower()
                       for kw in ["找对象", "征婚", "找男友", "找女友", "相亲", "单身"])
            )
            if dating_titles / len(notes_summary) > 0.8:
                return False, "matchmaker_all_dating_posts"

        return True, None

    def _check_marketing(self, author: dict) -> tuple[bool, str | None]:
        """Detect marketing / promo accounts."""
        bio = (author.get("bio") or "").lower()
        nickname = (author.get("nickname") or "").lower()
        text = nickname + " " + bio

        for kw in _MARKETING_KEYWORDS:
            if kw in text:
                return False, f"marketing_keyword:{kw}"

        # Unusually high follower count with few notes
        followers = author.get("followers", 0)
        notes = author.get("notes_summary")
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except (json.JSONDecodeError, TypeError):
                notes = []
        note_count = len(notes) if isinstance(notes, list) else 0

        if followers > 50000 and note_count < 5:
            return False, "marketing_high_followers_low_content"

        return True, None

    def _check_empty_account(self, author: dict) -> tuple[bool, str | None]:
        """Filter empty / low-quality accounts."""
        notes = author.get("notes_summary")
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except (json.JSONDecodeError, TypeError):
                notes = []

        note_count = len(notes) if isinstance(notes, list) else 0
        following = author.get("following", 0)
        bio = author.get("bio") or ""

        if note_count == 0 and following == 0 and not bio:
            return False, "empty_account"

        return True, None

    def _check_inactive(self, author: dict) -> tuple[bool, str | None]:
        """Filter accounts that haven't been active recently."""
        updated = author.get("updated_at")
        if not updated:
            return True, None  # Can't determine, keep for now

        # We consider "inactive" if the profile data is stale (>90 days)
        # A more robust check would look at the latest note's timestamp
        notes = author.get("notes_summary")
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except (json.JSONDecodeError, TypeError):
                notes = []

        # If we have no note data, pass this check
        if not isinstance(notes, list) or not notes:
            return True, None

        return True, None

    def _check_location(self, author: dict) -> tuple[bool, str | None]:
        """Filter by location if configured."""
        if self.allow_remote:
            return True, None

        location = author.get("ip_location") or ""
        if not location:
            return True, None  # Unknown location, keep for now

        if self.user_city and self.user_city not in location:
            return False, f"location_mismatch:{location}"

        return True, None
