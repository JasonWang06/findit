"""Main pipeline orchestrator.

Runs the full data pipeline:
1. Crawl new data from Xiaohongshu
2. Apply rule-based filters
3. Run AI scoring for all registered users
4. Generate matches and openers

Can be run as a one-shot CLI command or scheduled via cron/APScheduler.
"""

from __future__ import annotations

import asyncio
import logging

from findit.config import settings
from findit.crawler.runner import CrawlRunner
from findit.db import Database
from findit.recommender import RecommendationEngine

logger = logging.getLogger(__name__)


async def run_pipeline() -> dict:
    """Execute the full pipeline."""
    db = Database(settings.db_path)

    # Step 1: Crawl
    logger.info("=== Step 1: Crawling ===")
    crawler = CrawlRunner(db=db)
    crawl_result = await crawler.run_full_pipeline()
    logger.info("Crawl results: %s", crawl_result)

    # Step 2-3: Filter + Score for each user
    logger.info("=== Step 2-3: Filtering and Scoring ===")
    engine = RecommendationEngine(db=db)

    with db._conn() as conn:
        users = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM users WHERE setup_complete = 1"
            ).fetchall()
        ]

    match_counts = {}
    for user in users:
        logger.info("Processing user: %s", user.get("telegram_id"))
        matches = engine.process_pipeline_for_user(user)
        match_counts[user["telegram_id"]] = len(matches)
        logger.info("Generated %d matches for user %s", len(matches), user["telegram_id"])

    result = {
        "crawl": crawl_result,
        "users_processed": len(users),
        "matches": match_counts,
    }
    logger.info("Pipeline complete: %s", result)
    return result


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
