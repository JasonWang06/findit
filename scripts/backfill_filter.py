"""Backfill new filter rules over existing authors.

Per `docs/DATA_SPEC.md` §5:
    1. 全量作者跑早期筛查（Rule A + Rule B），命中 → filter_out
    2. 旧的 empty_account / inactive 等被废弃 reason 的作者，重置回 pending_profile，
       等 Step 3（主页爬取）补全后再 final-filter
    3. Step 3 + final filter 不在本脚本范围（爬虫 client 重写中）

幂等。多次运行结果一致。
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter

from findit.ai.filter_rules import SharedFilter
from findit.db import Database

logger = logging.getLogger(__name__)

# These are reasons set by the OLD rule set that no longer exist in DATA_SPEC.md.
# Authors flagged with one of these get reset back to pending_profile so they
# can be re-evaluated under the new rules (after Step 3 fills in their profile).
LEGACY_REASONS = {
    "empty_account",
    "inactive_90days",
    "marketing_high_followers_low_content",
    "low_quality_only_short_comments",
    "suspicious_default_name_dating",
    "suspicious_contact_in_bio",
    "matchmaker_high_dating_ratio",
    "matchmaker_multiple_ages",
    "matchmaker_multiple_heights",
}


def reset_legacy_filtered(db: Database) -> int:
    """Step 1 of backfill: rewind authors whose filter_reason is now obsolete."""
    with db._conn() as c:
        # Match exact legacy reasons; also match prefixed reasons like
        # "matchmaker_keyword:婚介" or "marketing_keyword:pr" where the
        # *prefix* is no longer a valid current reason.
        legacy_prefixes = ("marketing_keyword:",)
        rows = c.execute(
            "SELECT id, filter_reason FROM authors WHERE is_filtered_out=1"
        ).fetchall()

        to_reset = []
        for r in rows:
            reason = (r["filter_reason"] or "").strip()
            if reason in LEGACY_REASONS or any(
                reason.startswith(p) for p in legacy_prefixes
            ):
                to_reset.append(r["id"])
            elif reason.startswith("matchmaker_keyword:") and reason != "matchmaker_keyword":
                # Old code wrote "matchmaker_keyword:婚介" etc. Only "红娘" still
                # qualifies; all others get rewound.
                kw = reason.split(":", 1)[1]
                if "红娘" not in kw:
                    to_reset.append(r["id"])

        if to_reset:
            placeholders = ",".join("?" * len(to_reset))
            c.execute(
                f"""UPDATE authors
                    SET is_filtered_out=0, filter_reason=NULL,
                        crawl_state='pending_profile'
                    WHERE id IN ({placeholders})""",
                to_reset,
            )
        return len(to_reset)


def run_early_filter(db: Database) -> Counter:
    """Step 2 of backfill: apply Rule A + Rule B over the candidate pool."""
    flt = SharedFilter()
    stats: Counter = Counter()

    with db._conn() as c:
        rows = c.execute(
            """SELECT * FROM authors
               WHERE crawl_state='pending_profile' AND is_filtered_out=0"""
        ).fetchall()
        authors = [dict(r) for r in rows]

    for a in authors:
        posts = db.get_author_posts(a["id"])
        keep, reason = flt.evaluate(a, posts=posts, final=False)
        if not keep:
            db.update_author_scores(
                a["id"],
                is_filtered_out=True,
                filter_reason=reason,
                crawl_state="filtered_out",
            )
            stats[reason] += 1
        else:
            stats["kept_pending_profile"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/findit.db")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    db = Database(args.db)

    if args.dry_run:
        # Inspect-only mode: count authors that would change.
        with db._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
            filtered = c.execute(
                "SELECT COUNT(*) FROM authors WHERE is_filtered_out=1"
            ).fetchone()[0]
            states = c.execute(
                "SELECT crawl_state, COUNT(*) c FROM authors GROUP BY crawl_state"
            ).fetchall()
        logger.info("== DRY RUN ==")
        logger.info("Total authors: %d", total)
        logger.info("Currently filtered: %d", filtered)
        for s in states:
            logger.info("  crawl_state=%s : %d", s["crawl_state"], s["c"])
        return

    logger.info("== Step 1: rewind legacy-filtered authors ==")
    n_reset = reset_legacy_filtered(db)
    logger.info("Reset %d authors back to pending_profile", n_reset)

    logger.info("== Step 2: apply new early-filter rules ==")
    stats = run_early_filter(db)
    for reason, count in stats.most_common():
        logger.info("  %-30s : %d", reason, count)

    with db._conn() as c:
        states = c.execute(
            "SELECT crawl_state, COUNT(*) c FROM authors GROUP BY crawl_state"
        ).fetchall()
    logger.info("== Final state distribution ==")
    for s in states:
        logger.info("  crawl_state=%s : %d", s["crawl_state"], s["c"])


if __name__ == "__main__":
    main()
