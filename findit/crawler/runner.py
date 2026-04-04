"""Three-step crawl pipeline: search → comments → profiles.

Orchestrates the full crawl cycle:
  Step 1: Search keywords → collect posts
  Step 2: Scrape comments on those posts → find dating-intent commenters
  Step 3: Scrape profiles for all candidate authors
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from findit.config import settings
from findit.crawler.client import SEARCH_KEYWORDS, XHSClient
from findit.db import Database

logger = logging.getLogger(__name__)


class CrawlRunner:
    """Runs the three-step crawl pipeline."""

    def __init__(self, db: Database | None = None, client: XHSClient | None = None):
        self.db = db or Database(settings.db_path)
        self.client = client or XHSClient()

    async def step1_search_posts(
        self,
        keywords: list[str] | None = None,
        pages_per_keyword: int = 3,
    ) -> int:
        """Search for dating-related posts and save to DB.

        Returns the number of new posts saved.
        """
        keywords = keywords or SEARCH_KEYWORDS
        saved = 0

        for kw in keywords:
            for page in range(1, pages_per_keyword + 1):
                results = await self.client.search_notes(kw, page=page)
                if not results:
                    break

                for note in results:
                    # Ensure author exists before upserting post
                    author = self.db.get_author(note["user_id"])
                    if not author:
                        self.db.upsert_author({
                            "id": note["user_id"],
                            "nickname": note.get("user_nickname"),
                            "avatar_url": note.get("user_avatar"),
                            "ip_location": note.get("ip_location"),
                        })

                    self.db.upsert_post({
                        "id": note["id"],
                        "author_id": note["user_id"],
                        "content": note.get("content", ""),
                        "image_urls": note.get("image_list", []),
                        "likes": _parse_int(note.get("likes", "0")),
                        "comments_count": 0,
                        "created_at": note.get("time"),
                        "crawled_at": datetime.now().isoformat(),
                        "post_url": self.client.get_note_url(note["id"]),
                        "source_type": "post",
                    })
                    saved += 1

                logger.info("Keyword '%s' page %d: saved %d posts", kw, page, len(results))

        logger.info("Step 1 complete: saved %d posts total", saved)
        return saved

    async def step2_scrape_comments(self, max_posts: int = 50) -> int:
        """Scrape comments on recent posts and find dating-intent commenters.

        Returns count of dating-intent comments found.
        """
        # Get recent posts to scrape comments from
        posts = self.db.get_scored_posts(limit=max_posts)
        if not posts:
            # Fallback: get any posts
            with self.db._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM posts WHERE source_type='post' ORDER BY crawled_at DESC LIMIT ?",
                    (max_posts,),
                ).fetchall()
                posts = [dict(r) for r in rows]

        found = 0
        for post in posts:
            comments, _ = await self.client.get_note_comments(post["id"])
            dating_comments = self.client.filter_dating_comments(comments)

            for c in dating_comments:
                user_id = c["user_id"]
                if not user_id:
                    continue

                # Create author stub if not exists
                author = self.db.get_author(user_id)
                if not author:
                    self.db.upsert_author({
                        "id": user_id,
                        "nickname": c.get("nickname"),
                        "avatar_url": c.get("avatar"),
                        "ip_location": c.get("ip_location"),
                    })

                # Save the comment as a pseudo-post (source_type='comment')
                comment_id = f"comment_{c['comment_id']}"
                self.db.upsert_post({
                    "id": comment_id,
                    "author_id": user_id,
                    "content": c.get("content", ""),
                    "image_urls": [],
                    "likes": c.get("like_count", 0),
                    "comments_count": 0,
                    "created_at": c.get("create_time"),
                    "crawled_at": datetime.now().isoformat(),
                    "post_url": self.client.get_note_url(post["id"]),
                    "source_type": "comment",
                })
                found += 1

        logger.info("Step 2 complete: found %d dating-intent comments", found)
        return found

    async def step3_scrape_profiles(self, limit: int = 50) -> int:
        """Scrape full profiles for authors that haven't been fetched yet.

        Returns count of profiles scraped.
        """
        author_ids = self.db.get_unscraped_author_ids(limit=limit)
        # Also get authors with minimal data
        with self.db._conn() as conn:
            rows = conn.execute(
                """SELECT id FROM authors
                   WHERE bio IS NULL AND is_filtered_out = 0
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            for r in rows:
                if r["id"] not in author_ids:
                    author_ids.append(r["id"])

        scraped = 0
        for uid in author_ids[:limit]:
            profile = await self.client.get_user_profile(uid)
            if not profile.get("nickname"):
                continue

            # Also fetch their recent notes for analysis
            notes, _ = await self.client.get_user_notes(uid)
            profile["notes_summary"] = notes[:10]  # Keep top 10

            self.db.upsert_author(profile)
            scraped += 1

        logger.info("Step 3 complete: scraped %d profiles", scraped)
        return scraped

    async def run_full_pipeline(self) -> dict[str, int]:
        """Run all three steps in sequence."""
        logger.info("Starting full crawl pipeline")
        await self.client.setup()
        try:
            posts = await self.step1_search_posts()
            comments = await self.step2_scrape_comments()
            profiles = await self.step3_scrape_profiles()
            return {"posts": posts, "comments": comments, "profiles": profiles}
        finally:
            await self.client.close()


def _parse_int(value: str | int) -> int:
    """Parse integer from string, handling Chinese number suffixes."""
    if isinstance(value, int):
        return value
    value = str(value).strip()
    if not value:
        return 0
    # Handle "1.2万" format
    if value.endswith("万"):
        try:
            return int(float(value[:-1]) * 10000)
        except ValueError:
            return 0
    try:
        return int(value)
    except ValueError:
        return 0


def main():
    """CLI entry point for running the crawler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Starting crawl pipeline for city: %s", settings.crawl_city)
    result = asyncio.run(CrawlRunner().run_full_pipeline())
    logger.info("Crawl complete: %s", result)


if __name__ == "__main__":
    main()
