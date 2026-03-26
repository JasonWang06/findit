"""Main pipeline orchestrator.

Runs the full data pipeline in two phases:
1. Crawler service: crawl + shared filtering (user-independent)
2. Matching service: per-user scoring + match generation

Can be run as a one-shot CLI command or scheduled via cron.
For continuous crawling, use `findit-crawler-service` instead.
"""

from __future__ import annotations

import asyncio
import logging

from findit.config import settings
from findit.db import Database
from findit.services.crawler_service import CrawlerService
from findit.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


async def run_pipeline() -> dict:
    """Execute the full pipeline: crawl → filter → match."""
    db = Database(settings.db_path)

    # Phase 1: Crawl + shared filtering
    logger.info("=== Phase 1: Crawling + Shared Filtering ===")
    crawler_service = CrawlerService(db=db)
    crawl_result = await crawler_service.run_once()
    logger.info("Crawl + filter results: %s", crawl_result)

    # Phase 2: Per-user matching
    logger.info("=== Phase 2: Per-User Matching ===")
    matching_service = MatchingService(db=db)
    match_results = matching_service.process_all_users()
    logger.info("Match results: %s", match_results)

    return {
        "crawl": crawl_result,
        "matches": match_results,
    }


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
