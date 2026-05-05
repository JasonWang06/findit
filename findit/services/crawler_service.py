"""Crawler background service: two-stage filter per `docs/DATA_SPEC.md`.

Stage 1 (early): Step 1/2 lands posts + comments → `run_shared_filter(final=False)`
    runs Rule A/B on what's already known; matchmakers/proxy posts get
    crawl_state='filtered_out' early so we don't waste a Step 3 request on them.

Stage 2 (final): once Step 3 has run on a pending_profile author and
    `profile_crawled_at` is set, `run_shared_filter(final=True)` re-evaluates
    with notes_summary visible, and enforces §2 minimum-data bar
    (ip_location + ≥12-char content). Survivors flip to crawl_state='kept'.
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
        """Execute one crawl + two-stage filter cycle.

        Returns summary stats. Step 3 (profile crawl) only runs for authors
        that passed the early filter. The final filter only runs on authors
        that have profile_crawled_at set (i.e. Step 3 has actually completed).
        """
        # Step 1+2: Crawl posts/comments
        logger.info("=== Crawler Service: Step 1+2 — Crawling posts/comments ===")
        crawl_result = await self.crawler.run_full_pipeline(
            include_profiles=settings.crawl_include_profiles,
        )
        logger.info("Crawl results: %s", crawl_result)

        # Stage 1 (early): drop matchmakers before they cost a profile request
        logger.info("=== Crawler Service: Stage 1 — Early filter ===")
        early_filtered = self.run_shared_filter(final=False)

        # Step 3 (profile crawl) is owned by CrawlRunner via include_profiles.
        # When that's wired in (client.py rewrite in flight), it should set
        # profile_crawled_at via db.mark_profile_crawled() per author.

        # Stage 2 (final): re-evaluate authors whose profile is now available
        logger.info("=== Crawler Service: Stage 2 — Final filter ===")
        final_filtered = self.run_shared_filter(final=True)

        result = {
            **crawl_result,
            "filtered_early": early_filtered,
            "filtered_final": final_filtered,
        }
        logger.info("Crawler service cycle complete: %s", result)
        return result

    def run_shared_filter(self, final: bool = False) -> int:
        """Apply Rule A + Rule B (and §2 min-quality if final=True).

        Args:
            final: True after Step 3. Restricts the candidate set to
                authors with `profile_crawled_at` set, and enforces the
                §2 minimum-data bar in addition to the matchmaker rules.

        Returns count of authors newly filtered out in this pass.
        """
        authors = self._candidates_for(final=final)
        filtered_count = 0

        for author in authors:
            posts = self.db.get_author_posts(author["id"])
            keep, reason = self.shared_filter.evaluate(
                author, posts=posts, final=final
            )
            if not keep:
                self.db.update_author_scores(
                    author["id"],
                    is_filtered_out=True,
                    filter_reason=reason,
                    crawl_state="filtered_out",
                )
                filtered_count += 1
                logger.debug("Filtered out %s: %s", author.get("nickname"), reason)
            elif final:
                # Survived final check — promote to 'kept'.
                self.db.update_author_scores(
                    author["id"],
                    is_real_person=0.5,  # placeholder; AI scoring happens later
                    crawl_state="kept",
                )
            # else: passed early filter but stays pending_profile — don't
            # set is_real_person yet (re-evaluated after Step 3).

        stage = "final" if final else "early"
        logger.info(
            "Shared filter (%s): %d/%d authors filtered out",
            stage, filtered_count, len(authors),
        )
        return filtered_count

    def _candidates_for(self, final: bool) -> list[dict]:
        """Pick which authors to evaluate at each stage."""
        with self.db._conn() as c:
            if final:
                # Step 3 已完成且仍处于 pending_profile —— 准备做最终判定
                rows = c.execute(
                    """SELECT * FROM authors
                       WHERE crawl_state='pending_profile'
                         AND profile_crawled_at IS NOT NULL
                       LIMIT 500"""
                ).fetchall()
            else:
                # 还没被早期筛查命中过的 pending_profile 作者
                rows = c.execute(
                    """SELECT * FROM authors
                       WHERE crawl_state='pending_profile'
                         AND is_filtered_out=0
                       LIMIT 500"""
                ).fetchall()
            return [dict(r) for r in rows]

    async def run_forever(self, interval_hours: int | None = None) -> None:
        """Run the crawl+filter cycle continuously.

        Uses exponential backoff on consecutive failures (retry sooner
        instead of waiting the full interval). Resets on success.
        """
        interval = (interval_hours or settings.crawl_interval_hours) * 3600
        consecutive_failures = 0
        max_backoff = interval

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown.set)

        logger.info(
            "Crawler service starting (interval: %dh)", interval // 3600
        )

        while not self._shutdown.is_set():
            try:
                await self.run_once()
                consecutive_failures = 0
            except Exception:
                consecutive_failures += 1
                logger.exception(
                    "Crawler cycle failed (%d consecutive)", consecutive_failures
                )

            if consecutive_failures > 0:
                wait = min(300 * (2 ** (consecutive_failures - 1)), max_backoff)
                logger.info("Retrying in %d seconds (backoff)", wait)
            else:
                wait = interval

            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass

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
