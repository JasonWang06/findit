"""Recommendation engine: selects and scores candidates for a user.

Strategy per PRD:
- 3 high-match (score > 70) + 2 medium-match (40-70) daily
- Priority: match_score → post freshness → author activity → uniqueness
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from findit.ai.filter_rules import RuleFilter
from findit.ai.opener import OpenerGenerator
from findit.ai.scorer import AIScorer, ScoringResult
from findit.config import settings
from findit.db import Database

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Orchestrates filtering, scoring, and match generation for a user."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(settings.db_path)
        self.scorer = AIScorer()
        self.opener_gen = OpenerGenerator()

    def run_rule_filter(self, user_city: str = "", allow_remote: bool = False) -> int:
        """Apply rule-based filters to all unfiltered authors.

        Returns count of authors filtered out.
        """
        rule_filter = RuleFilter(
            user_city=user_city or settings.crawl_city,
            allow_remote=allow_remote,
        )

        with self.db._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM authors WHERE is_filtered_out = 0 AND is_real_person IS NULL"
            ).fetchall()

        filtered_count = 0
        for row in rows:
            author = dict(row)
            keep, reason = rule_filter.evaluate(author)
            if not keep:
                self.db.update_author_scores(
                    author["id"], is_filtered_out=True, filter_reason=reason
                )
                filtered_count += 1
                logger.debug("Filtered out %s: %s", author.get("nickname"), reason)

        logger.info("Rule filter: %d/%d authors filtered out", filtered_count, len(rows))
        return filtered_count

    def run_ai_scoring(self, user: dict, limit: int = 30) -> int:
        """Run AI scoring on unscored posts for a given user.

        Returns count of posts scored.
        """
        posts = self.db.get_unprocessed_posts(limit=limit)
        scored = 0

        for post in posts:
            author = self.db.get_author(post["author_id"])
            if not author:
                continue

            result = self.scorer.score(post, author, user)
            if not result:
                continue

            # Update author's authenticity score
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
            opener_1, opener_2, strategy = self.opener_gen.generate(
                post, author, user, scoring_dict
            )

            # Create match record
            self.db.create_match({
                "user_id": user["id"],
                "post_id": post["id"],
                "author_id": post["author_id"],
                "authenticity_score": result.authenticity_score,
                "seriousness_score": result.seriousness_score,
                "match_score": result.match_score,
                "match_analysis": result.match_analysis,
                "generated_opener": opener_1,
                "alt_opener": opener_2,
            })
            scored += 1

        logger.info("AI scoring: scored %d posts for user %s", scored, user.get("telegram_id"))
        return scored

    def get_daily_matches(self, user_id: int, count: int | None = None) -> list[dict]:
        """Get the daily batch of matches for a user.

        Selects a mix of high and medium matches per the PRD strategy.
        """
        total = count or settings.daily_match_count
        high_count = settings.high_match_count
        medium_count = total - high_count

        already_matched = self.db.get_already_matched_author_ids(user_id)

        with self.db._conn() as conn:
            # High matches (score > 70)
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

            # Medium matches (40-70)
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

        # If not enough high matches, fill with medium; vice versa
        if len(matches) < total:
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
                        ",".join(str(m["id"]) for m in matches) or "0"
                    ),
                    (user_id, total - len(matches)),
                ).fetchall()
                matches.extend(dict(r) for r in fill_rows)

        return matches[:total]

    def process_pipeline_for_user(self, user: dict) -> list[dict]:
        """Full pipeline: rule filter → AI score → get daily matches."""
        prefs = user.get("preferences", "{}")
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except (json.JSONDecodeError, TypeError):
                prefs = {}

        # Step 1: Rule filter
        self.run_rule_filter(
            user_city=user.get("city", ""),
            allow_remote=prefs.get("allow_remote", False),
        )

        # Step 2: AI scoring
        self.run_ai_scoring(user)

        # Step 3: Get matches
        return self.get_daily_matches(user["id"])
