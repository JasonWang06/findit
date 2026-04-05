#!/usr/bin/env python3
"""Import MediaCrawler JSONL output into findit's SQLite database.

Usage:
    python scripts/import_mediacrawler.py /path/to/MediaCrawler/data/xhs/jsonl

This reads the JSONL files produced by MediaCrawler and imports:
  - Notes → posts table + authors table
  - Comments with dating intent → posts table (source_type='comment') + authors table
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import findit
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from findit.crawler.client import COMMENT_DATING_KEYWORDS
from findit.db import Database


def read_jsonl(filepath: Path) -> list[dict]:
    """Read a JSONL file, returning a list of dicts."""
    items = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def ms_to_iso(ms_timestamp: int | str | None) -> str | None:
    """Convert millisecond timestamp to ISO datetime string."""
    if not ms_timestamp:
        return None
    try:
        ts = int(ms_timestamp) / 1000
        return datetime.fromtimestamp(ts).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def import_notes(db: Database, notes: list[dict]) -> int:
    """Import notes into posts and authors tables. Returns count imported."""
    count = 0
    for note in notes:
        user_id = note.get("user_id", "")
        if not user_id:
            continue

        # Upsert author
        db.upsert_author({
            "id": user_id,
            "nickname": note.get("nickname"),
            "avatar_url": note.get("avatar"),
            "ip_location": note.get("ip_location"),
        })

        # Build content from title + desc
        title = note.get("title", "")
        desc = note.get("desc", "")
        content = f"{title}\n{desc}".strip() if title != desc else title

        # Parse image list (MediaCrawler stores as comma-separated URLs)
        image_str = note.get("image_list", "")
        image_urls = [url.strip() for url in image_str.split(",") if url.strip()] if image_str else []

        note_id = note.get("note_id", "")
        db.upsert_post({
            "id": note_id,
            "author_id": user_id,
            "content": content,
            "image_urls": image_urls,
            "likes": _parse_int(note.get("liked_count", "0")),
            "comments_count": _parse_int(note.get("comment_count", "0")),
            "created_at": ms_to_iso(note.get("time")),
            "crawled_at": datetime.now().isoformat(),
            "post_url": note.get("note_url", ""),
            "source_type": "post",
        })
        count += 1
    return count


def import_comments(db: Database, comments: list[dict]) -> tuple[int, int]:
    """Import dating-intent comments. Returns (total_comments, dating_comments)."""
    total = len(comments)
    dating = 0

    for c in comments:
        content = c.get("content", "")
        content_lower = content.lower()

        # Check for dating intent
        has_dating_intent = any(kw in content_lower for kw in COMMENT_DATING_KEYWORDS)
        if not has_dating_intent:
            continue

        user_id = c.get("user_id", "")
        if not user_id:
            continue

        # Upsert author
        db.upsert_author({
            "id": user_id,
            "nickname": c.get("nickname"),
            "avatar_url": c.get("avatar"),
            "ip_location": c.get("ip_location"),
        })

        # Save as pseudo-post with source_type='comment'
        comment_id = f"comment_{c.get('comment_id', '')}"
        note_id = c.get("note_id", "")
        db.upsert_post({
            "id": comment_id,
            "author_id": user_id,
            "content": content,
            "image_urls": [],
            "likes": _parse_int(c.get("like_count", "0")),
            "comments_count": 0,
            "created_at": ms_to_iso(c.get("create_time")),
            "crawled_at": datetime.now().isoformat(),
            "post_url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
            "source_type": "comment",
        })
        dating += 1

    return total, dating


def _parse_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def main():
    parser = argparse.ArgumentParser(description="Import MediaCrawler data into findit")
    parser.add_argument(
        "data_dir",
        help="Path to MediaCrawler's JSONL output directory (e.g. ~/Desktop/MediaCrawler/data/xhs/jsonl)",
    )
    parser.add_argument(
        "--db",
        default="data/findit.db",
        help="Path to findit SQLite database (default: data/findit.db)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser()
    if not data_dir.exists():
        print(f"Error: directory not found: {data_dir}")
        sys.exit(1)

    # Find JSONL files
    note_files = sorted(data_dir.glob("*note*"))
    comment_files = sorted(data_dir.glob("*comment*"))

    if not note_files and not comment_files:
        # Try looking for any .jsonl files
        all_files = sorted(data_dir.glob("*.jsonl"))
        if not all_files:
            print(f"Error: no JSONL files found in {data_dir}")
            print(f"Files present: {list(data_dir.iterdir())}")
            sys.exit(1)
        # Guess based on filenames
        for f in all_files:
            if "comment" in f.name.lower():
                comment_files.append(f)
            else:
                note_files.append(f)

    print(f"Found {len(note_files)} note file(s), {len(comment_files)} comment file(s)")

    # Initialize database
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(str(db_path))

    # Import notes
    total_notes = 0
    for filepath in note_files:
        notes = read_jsonl(filepath)
        count = import_notes(db, notes)
        total_notes += count
        print(f"  Notes from {filepath.name}: {count} imported")

    # Import comments
    total_comments = 0
    total_dating = 0
    for filepath in comment_files:
        comments = read_jsonl(filepath)
        total, dating = import_comments(db, comments)
        total_comments += total
        total_dating += dating
        print(f"  Comments from {filepath.name}: {total} total, {dating} with dating intent")

    # Summary
    print()
    print("=" * 50)
    print(f"Import complete!")
    print(f"  Posts imported: {total_notes}")
    print(f"  Comments scanned: {total_comments}")
    print(f"  Dating-intent comments imported: {total_dating}")
    print(f"  Database: {db_path.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
