"""Per-user matching service.

Draws from the shared data pool (populated by the crawler service)
to generate personalized matches for each registered user.

Pipeline per user:
  1. Get candidates from screened pool (passed shared filter)
  2. Apply per-user filters (city, age preferences)
  3. AI scoring (compatibility + opener generation)
  4. Select daily match mix (3 high + 2 medium)
"""

from __future__ import annotations

import json
import logging

from findit.ai.filter_rules import UserFilter
from findit.ai.opener import OpenerGenerator
from findit.ai.scorer import AIScorer
from findit.config import settings
from findit.db import Database

logger = logging.getLogger(__name__)


class MatchingService:
    """Generates personalized matches for users from the shared pool."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(settings.db_path)
        self.scorer = AIScorer()
        self.opener_gen = OpenerGenerator()

    def generate_matches(self, user: dict) -> list[dict]:
        """Full matching pipeline for a single user.

        Returns the daily match list ready for pushing.
        """
        prefs = user.get("preferences", "{}")
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except (json.JSONDecodeError, TypeError):
                prefs = {}

        # Step 1: Get candidates from shared pool
        candidates = self.db.get_screened_candidates(
            city=user.get("city"),
            limit=200,
        )

        # Step 2: Per-user filtering
        user_filter = UserFilter(
            user_city=user.get("city", ""),
            allow_remote=prefs.get("allow_remote", False),
            age_min=prefs.get("age_min"),
            age_max=prefs.get("age_max"),
        )

        # Exclude already-matched authors
        already_matched = self.db.get_already_matched_author_ids(user["id"])

        filtered_candidates = []
        for c in candidates:
            author_id = c.get("author_id") or c.get("id")
            if author_id in already_matched:
                continue
            # Build a mini author dict for the user filter
            author_dict = {
                "ip_location": c.get("ip_location"),
                "age_tag": c.get("age_tag"),
            }
            keep, _ = user_filter.evaluate(author_dict)
            if keep:
                filtered_candidates.append(c)

        # Step 3: AI scoring (compatibility + openers) for unscored candidates
        scored = 0
        for post in filtered_candidates[:30]:  # Cap at 30 to control API costs
            author = self.db.get_author(post.get("author_id", ""))
            if not author:
                continue

            # Check if this post is already matched for this user
            existing = self._has_existing_match(user["id"], post["id"])
            if existing:
                continue

            result = self.scorer.score(post, author, user)
            if not result:
                continue

            # Update author's authenticity if not yet properly scored
            if author.get("is_real_person") == 0.5:  # Placeholder from shared filter
                self.db.update_author_scores(
                    author["id"],
                    is_real_person=result.authenticity_score / 100.0,
                )

            # Generate openers
            scoring_dict = {
                "her_requirements": result.her_requirements,
                "common_topics": result.common_topics,
                "communication_style": result.communication_style,
                "opener_hooks": result.opener_hooks,
            }
            opener_1, opener_2, _ = self.opener_gen.generate(
                post, author, user, scoring_dict
            )

            self.db.create_match({
                "user_id": user["id"],
                "post_id": post["id"],
                "author_id": post.get("author_id", ""),
                "authenticity_score": result.authenticity_score,
                "seriousness_score": result.seriousness_score,
                "match_score": result.match_score,
                "match_analysis": result.match_analysis,
                "generated_opener": opener_1,
                "alt_opener": opener_2,
            })
            scored += 1

        logger.info(
            "Scored %d new candidates for user %s", scored, user.get("telegram_id")
        )

        # Step 4: Select daily matches (3 high + 2 medium)
        return self._select_daily_matches(user["id"])

    def _has_existing_match(self, user_id: int, post_id: str) -> bool:
        with self.db._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM matches WHERE user_id=? AND post_id=?",
                (user_id, post_id),
            ).fetchone()
            return row is not None

    def _select_daily_matches(
        self, user_id: int, count: int | None = None
    ) -> list[dict]:
        """Select daily match mix: 3 high + 2 medium."""
        total = count or settings.daily_match_count
        high_count = settings.high_match_count
        medium_count = total - high_count

        with self.db._conn() as conn:
            high_rows = conn.execute(
                """SELECT m.*, p.content as post_content, p.post_url, p.image_urls,
                   a.nickname, a.ip_location, a.bio, a.age_tag, a.avatar_url
                   FROM matches m
                   JOIN posts p ON m.post_id = p.id
                   JOIN authors a ON m.author_id = a.id
                   WHERE m.user_id = ? AND m.pushed_at IS NULL
                   AND m.match_score > 70
                   ORDER BY m.match_score DESC, p.crawled_at DESC
                   LIMIT ?""",
                (user_id, high_count),
            ).fetchall()

            medium_rows = conn.execute(
                """SELECT m.*, p.content as post_content, p.post_url, p.image_urls,
                   a.nickname, a.ip_location, a.bio, a.age_tag, a.avatar_url
                   FROM matches m
                   JOIN posts p ON m.post_id = p.id
                   JOIN authors a ON m.author_id = a.id
                   WHERE m.user_id = ? AND m.pushed_at IS NULL
                   AND m.match_score BETWEEN 40 AND 70
                   ORDER BY m.match_score DESC, p.crawled_at DESC
                   LIMIT ?""",
                (user_id, medium_count),
            ).fetchall()

        matches = [dict(r) for r in high_rows] + [dict(r) for r in medium_rows]

        # Fill if not enough
        if len(matches) < total:
            matched_ids = {m["id"] for m in matches}
            with self.db._conn() as conn:
                fill_rows = conn.execute(
                    """SELECT m.*, p.content as post_content, p.post_url, p.image_urls,
                       a.nickname, a.ip_location, a.bio, a.age_tag, a.avatar_url
                       FROM matches m
                       JOIN posts p ON m.post_id = p.id
                       JOIN authors a ON m.author_id = a.id
                       WHERE m.user_id = ? AND m.pushed_at IS NULL
                       AND m.id NOT IN ({})
                       ORDER BY m.match_score DESC
                       LIMIT ?""".format(
                        ",".join(str(mid) for mid in matched_ids) or "0"
                    ),
                    (user_id, total - len(matches)),
                ).fetchall()
                matches.extend(dict(r) for r in fill_rows)

        return matches[:total]

    def process_all_users(self) -> dict[str, int]:
        """Generate matches for all registered users.

        Returns dict of telegram_id → match count.
        """
        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE setup_complete = 1"
            ).fetchall()

        results = {}
        for row in rows:
            user = dict(row)
            try:
                matches = self.generate_matches(user)
                results[user["telegram_id"]] = len(matches)
                logger.info(
                    "Generated %d matches for user %s",
                    len(matches),
                    user["telegram_id"],
                )
            except Exception:
                logger.exception(
                    "Failed to generate matches for user %s", user["telegram_id"]
                )
                results[user["telegram_id"]] = 0

        return results
