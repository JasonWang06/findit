"""Crawler background service: crawl + shared filtering.

Runs independently of any user. Populates the shared data pool
that the matching service draws from.

Pipeline per cycle:
  1. CrawlRunner: search → comments → profiles
  2. SharedFilter: keyword/heuristic filtering on new authors

Architecture note: an LLM screening step can be inserted between
step 2 and the matching service later, if keyword filtering proves
insufficient for certain edge cases.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from findit.ai.filter_rules import SharedFilter
from findit.config import settings
from findit.crawler.runner import CrawlRunner
from findit.db import Database

logger = logging.getLogger(__name__)


class CrawlerService:
    """Background service that crawls data and applies shared filters."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(settings.db_path)
        self.crawler = CrawlRunner(db=self.db)
        self.shared_filter = SharedFilter()
        self._shutdown = asyncio.Event()

    async def run_once(self) -> dict:
        """Execute a single crawl + filter cycle.

        Returns summary stats.
        """
        # Step 1: Crawl
        logger.info("=== Crawler Service: Step 1 - Crawling ===")
        crawl_result = await self.crawler.run_full_pipeline()
        logger.info("Crawl results: %s", crawl_result)

        # Step 2: Shared filtering (user-independent)
        logger.info("=== Crawler Service: Step 2 - Shared Filtering ===")
        filtered = self.run_shared_filter()

        # (Future: Step 3 - LLM screening for edge cases)

        result = {
            **crawl_result,
            "filtered_out": filtered,
        }
        logger.info("Crawler service cycle complete: %s", result)
        return result

    def run_shared_filter(self) -> int:
        """Apply shared filters to all unfiltered authors.

        This runs the keyword/heuristic checks that don't depend on
        any user's profile. Filtered authors are marked in the DB
        so the matching service skips them.

        Returns count of authors filtered out.
        """
        authors = self.db.get_unfiltered_authors(limit=500)
        filtered_count = 0

        for author in authors:
            # Get the author's posts for inactive check
            posts = self.db.get_author_posts(author["id"])

            keep, reason = self.shared_filter.evaluate(author, posts=posts)
            if not keep:
                self.db.update_author_scores(
                    author["id"],
                    is_filtered_out=True,
                    filter_reason=reason,
                )
                filtered_count += 1
                logger.debug("Filtered out %s: %s", author.get("nickname"), reason)
            else:
                # Mark as passed shared filter (is_real_person=None → placeholder 0.5)
                # A proper value will be set by AI scoring later, but this marks
                # the author as "shared-filter-passed" so they don't get re-processed.
                self.db.update_author_scores(
                    author["id"],
                    is_real_person=0.5,  # Placeholder: passed rules, not yet AI-scored
                )

        logger.info(
            "Shared filter: %d/%d authors filtered out", filtered_count, len(authors)
        )
        return filtered_count

    async def run_forever(self, interval_hours: int | None = None) -> None:
        """Run the crawl+filter cycle continuously.

        Loops until SIGTERM/SIGINT is received.
        """
        interval = (interval_hours or settings.crawl_interval_hours) * 3600

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown.set)

        logger.info(
            "Crawler service starting (interval: %dh)", interval // 3600
        )

        while not self._shutdown.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("Crawler cycle failed, will retry next interval")

            # Wait for the interval or until shutdown is requested
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(), timeout=interval
                )
            except asyncio.TimeoutError:
                pass  # Normal: timeout means it's time for the next cycle

        logger.info("Crawler service shutting down gracefully")


def main() -> None:
    """CLI entry point for the crawler service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    service = CrawlerService()

    if settings.crawler_continuous:
        logger.info("Starting crawler in continuous mode")
        asyncio.run(service.run_forever())
    else:
        logger.info("Starting single crawl cycle")
        asyncio.run(service.run_once())


if __name__ == "__main__":
    main()
