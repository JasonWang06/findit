#!/usr/bin/env python3
"""Extract AI tags from posts in the database.

Usage:
    python scripts/extract_tags.py [--limit N] [--post-id ID] [--reprocess]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from findit.ai.tag_extractor import AITagExtractor
from findit.config import settings
from findit.db import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def process_post(
    extractor: AITagExtractor,
    db: Database,
    post: dict,
    author: dict | None = None,
) -> bool:
    """Process a single post and save results."""
    post_id = post.get("id")
    author_id = post.get("author_id")

    if not author:
        author = db.get_author(author_id)

    result = extractor.extract_from_post(post, author)

    if result:
        logger.info(
            "✓ Post %s: %s, %d岁, %s - 置信度: %d%%",
            post_id,
            result.personal_info.gender or "未知",
            result.personal_info.age or "未知",
            result.personal_info.location or "未知",
            result.confidence_score,
        )

        # Save to database
        db.update_post_tags(post_id, result.to_dict())
        return True
    else:
        logger.warning("✗ Post %s: Extraction failed", post_id)
        return False


def main():
    parser = argparse.ArgumentParser(description="Extract AI tags from posts")
    parser.add_argument("--limit", type=int, default=10, help="Max posts to process")
    parser.add_argument("--post-id", type=str, help="Process specific post ID")
    parser.add_argument(
        "--reprocess", action="store_true", help="Reprocess already processed posts"
    )
    parser.add_argument("--source-type", type=str, help="Filter by source_type (post/comment)")
    args = parser.parse_args()

    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set in .env file")
        sys.exit(1)

    db = Database(settings.db_path)
    extractor = AITagExtractor()

    if args.post_id:
        # Process specific post
        with db._conn() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id=?", (args.post_id,)).fetchone()
            if not row:
                logger.error("Post %s not found", args.post_id)
                sys.exit(1)
            post = dict(row)

        author = db.get_author(post["author_id"])
        success = process_post(extractor, db, post, author)
        sys.exit(0 if success else 1)

    # Get posts to process
    if args.reprocess:
        # Get all posts
        with db._conn() as conn:
            query = "SELECT * FROM posts"
            params = []
            if args.source_type:
                query += " WHERE source_type = ?"
                params.append(args.source_type)
            query += " ORDER BY crawled_at DESC LIMIT ?"
            params.append(args.limit)

            rows = conn.execute(query, params).fetchall()
            posts = [dict(r) for r in rows]
    else:
        # Get posts without AI tags
        posts = db.get_posts_without_tags(limit=args.limit, source_type=args.source_type)

    if not posts:
        logger.info("No posts to process")
        return

    logger.info("Found %d posts to process", len(posts))

    # Process posts
    success_count = 0
    for i, post in enumerate(posts, 1):
        logger.info("[%d/%d] Processing post %s", i, len(posts), post.get("id"))
        if process_post(extractor, db, post):
            success_count += 1

    logger.info("Processing complete: %d/%d successful", success_count, len(posts))


if __name__ == "__main__":
    main()