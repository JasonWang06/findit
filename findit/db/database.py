"""SQLite database layer with schema management."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL DEFAULT 'xiaohongshu',
    author_id TEXT NOT NULL,
    content TEXT,
    image_urls TEXT DEFAULT '[]',          -- JSON array
    likes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    created_at TEXT,
    crawled_at TEXT NOT NULL,
    post_url TEXT,
    source_type TEXT NOT NULL DEFAULT 'post',  -- 'post' or 'comment'
    FOREIGN KEY (author_id) REFERENCES authors(id)
);

CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY,
    nickname TEXT,
    avatar_url TEXT,
    ip_location TEXT,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    likes_collected INTEGER DEFAULT 0,
    bio TEXT,
    age_tag TEXT,
    notes_summary TEXT DEFAULT '[]',       -- JSON array
    is_real_person REAL,                   -- 0.0 - 1.0 confidence
    is_filtered_out INTEGER DEFAULT 0,     -- 1 if ruled out by filters
    filter_reason TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT UNIQUE NOT NULL,
    age INTEGER,
    height INTEGER,
    education TEXT,
    school TEXT,
    occupation TEXT,
    income_range TEXT,
    city TEXT,
    hobbies TEXT DEFAULT '[]',             -- JSON array
    highlights TEXT DEFAULT '[]',          -- JSON array
    preferences TEXT DEFAULT '{}',         -- JSON object
    setup_complete INTEGER DEFAULT 0,
    setup_step TEXT DEFAULT 'start',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    authenticity_score REAL,
    seriousness_score REAL,
    match_score REAL,
    match_analysis TEXT,
    generated_opener TEXT,
    alt_opener TEXT,
    user_action TEXT,                      -- 'liked' / 'passed' / 'sent'
    result TEXT,                           -- 'replied' / 'no_reply' / 'unknown'
    pushed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (author_id) REFERENCES authors(id)
);

CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_crawled ON posts(crawled_at);
CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source_type);
CREATE INDEX IF NOT EXISTS idx_authors_location ON authors(ip_location);
CREATE INDEX IF NOT EXISTS idx_authors_filtered ON authors(is_filtered_out);
CREATE INDEX IF NOT EXISTS idx_matches_user ON matches(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_pushed ON matches(pushed_at);
CREATE INDEX IF NOT EXISTS idx_matches_user_author ON matches(user_id, author_id);
"""


class Database:
    """Thin wrapper around SQLite with helper methods for each table."""

    def __init__(self, db_path: str | Path = "data/findit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA_SQL)

    # ── Posts ────────────────────────────────────────────────────────────

    def upsert_post(self, post: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO posts (id, platform, author_id, content, image_urls,
                   likes, comments_count, created_at, crawled_at, post_url, source_type)
                   VALUES (:id, :platform, :author_id, :content, :image_urls,
                   :likes, :comments_count, :created_at, :crawled_at, :post_url, :source_type)
                   ON CONFLICT(id) DO UPDATE SET
                   content=excluded.content, likes=excluded.likes,
                   comments_count=excluded.comments_count, crawled_at=excluded.crawled_at""",
                {
                    "id": post["id"],
                    "platform": post.get("platform", "xiaohongshu"),
                    "author_id": post["author_id"],
                    "content": post.get("content", ""),
                    "image_urls": json.dumps(post.get("image_urls", [])),
                    "likes": post.get("likes", 0),
                    "comments_count": post.get("comments_count", 0),
                    "created_at": post.get("created_at"),
                    "crawled_at": post.get("crawled_at", datetime.now().isoformat()),
                    "post_url": post.get("post_url"),
                    "source_type": post.get("source_type", "post"),
                },
            )

    def get_unprocessed_posts(self, limit: int = 100) -> list[dict]:
        """Get posts whose authors haven't been AI-scored yet."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT p.* FROM posts p
                   JOIN authors a ON p.author_id = a.id
                   WHERE a.is_filtered_out = 0 AND a.is_real_person IS NULL
                   ORDER BY p.crawled_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_posts_without_tags(self, limit: int = 100, source_type: str | None = None) -> list[dict]:
        """Get posts that haven't had AI tag extraction yet."""
        with self._conn() as conn:
            query = """SELECT * FROM posts WHERE ai_tags IS NULL"""
            params = []
            if source_type:
                query += " AND source_type = ?"
                params.append(source_type)
            query += " ORDER BY crawled_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_post_tags(self, post_id: str, tags: dict) -> None:
        """Update AI tags for a post."""
        with self._conn() as conn:
            conn.execute(
                """UPDATE posts SET ai_tags = ? WHERE id = ?""",
                (json.dumps(tags, ensure_ascii=False), post_id),
            )

    def get_scored_posts(self, city: str | None = None, limit: int = 200) -> list[dict]:
        """Get posts with AI scores, optionally filtered by city."""
        with self._conn() as conn:
            query = """SELECT p.*, a.nickname, a.ip_location, a.bio, a.age_tag,
                       a.is_real_person, a.notes_summary, a.followers, a.avatar_url
                       FROM posts p
                       JOIN authors a ON p.author_id = a.id
                       WHERE a.is_filtered_out = 0 AND a.is_real_person IS NOT NULL"""
            params: list[Any] = []
            if city:
                query += " AND a.ip_location LIKE ?"
                params.append(f"%{city}%")
            query += " ORDER BY p.crawled_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # ── Authors ─────────────────────────────────────────────────────────

    def upsert_author(self, author: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO authors (id, nickname, avatar_url, ip_location,
                   followers, following, likes_collected, bio, age_tag,
                   notes_summary, updated_at)
                   VALUES (:id, :nickname, :avatar_url, :ip_location,
                   :followers, :following, :likes_collected, :bio, :age_tag,
                   :notes_summary, :updated_at)
                   ON CONFLICT(id) DO UPDATE SET
                   nickname=excluded.nickname, avatar_url=excluded.avatar_url,
                   ip_location=excluded.ip_location, followers=excluded.followers,
                   following=excluded.following, likes_collected=excluded.likes_collected,
                   bio=excluded.bio, age_tag=excluded.age_tag,
                   notes_summary=excluded.notes_summary, updated_at=excluded.updated_at""",
                {
                    "id": author["id"],
                    "nickname": author.get("nickname"),
                    "avatar_url": author.get("avatar_url"),
                    "ip_location": author.get("ip_location"),
                    "followers": author.get("followers", 0),
                    "following": author.get("following", 0),
                    "likes_collected": author.get("likes_collected", 0),
                    "bio": author.get("bio"),
                    "age_tag": author.get("age_tag"),
                    "notes_summary": json.dumps(author.get("notes_summary", []), ensure_ascii=False),
                    "updated_at": datetime.now().isoformat(),
                },
            )

    def update_author_scores(
        self, author_id: str, is_real_person: float | None = None,
        is_filtered_out: bool = False, filter_reason: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE authors SET is_real_person=?, is_filtered_out=?,
                   filter_reason=?, updated_at=? WHERE id=?""",
                (is_real_person, int(is_filtered_out), filter_reason,
                 datetime.now().isoformat(), author_id),
            )

    def get_author(self, author_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM authors WHERE id=?", (author_id,)).fetchone()
            return dict(row) if row else None

    def get_unscraped_author_ids(self, limit: int = 50) -> list[str]:
        """Get author IDs that don't have profile data yet."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT p.author_id FROM posts p
                   LEFT JOIN authors a ON p.author_id = a.id
                   WHERE a.id IS NULL LIMIT ?""",
                (limit,),
            ).fetchall()
            return [r["author_id"] for r in rows]

    def get_unfiltered_authors(self, limit: int = 100) -> list[dict]:
        """Get authors that haven't been through shared filtering yet.

        Used by the crawler service to run shared filters on new authors.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM authors
                   WHERE is_filtered_out = 0 AND is_real_person IS NULL
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_screened_candidates(
        self, city: str | None = None, limit: int = 200
    ) -> list[dict]:
        """Get authors that passed shared filtering, optionally by city.

        Used by the matching service to get candidates for per-user scoring.
        Returns authors joined with their posts.
        """
        with self._conn() as conn:
            query = """SELECT p.*, a.nickname, a.ip_location, a.bio, a.age_tag,
                       a.is_real_person, a.notes_summary, a.followers, a.avatar_url
                       FROM posts p
                       JOIN authors a ON p.author_id = a.id
                       WHERE a.is_filtered_out = 0
                       AND a.is_real_person IS NOT NULL"""
            params: list[Any] = []
            if city:
                query += " AND a.ip_location LIKE ?"
                params.append(f"%{city}%")
            query += " ORDER BY p.crawled_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_author_posts(self, author_id: str) -> list[dict]:
        """Get all posts by an author (for inactive check)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM posts WHERE author_id = ? ORDER BY created_at DESC",
                (author_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Users ───────────────────────────────────────────────────────────

    def get_or_create_user(self, telegram_id: str) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
            ).fetchone()
            if row:
                return dict(row)
            conn.execute(
                "INSERT INTO users (telegram_id, created_at) VALUES (?, ?)",
                (telegram_id, datetime.now().isoformat()),
            )
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
            ).fetchone()
            return dict(row)

    def update_user(self, telegram_id: str, **fields: Any) -> None:
        if not fields:
            return
        json_fields = {"hobbies", "highlights", "preferences"}
        set_parts = []
        values: list[Any] = []
        for k, v in fields.items():
            set_parts.append(f"{k}=?")
            values.append(json.dumps(v, ensure_ascii=False) if k in json_fields else v)
        values.append(telegram_id)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(set_parts)} WHERE telegram_id=?", values
            )

    def get_user_by_telegram(self, telegram_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
            ).fetchone()
            return dict(row) if row else None

    # ── Matches ─────────────────────────────────────────────────────────

    def create_match(self, match: dict[str, Any]) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO matches (user_id, post_id, author_id,
                   authenticity_score, seriousness_score, match_score,
                   match_analysis, generated_opener, alt_opener, created_at)
                   VALUES (:user_id, :post_id, :author_id,
                   :authenticity_score, :seriousness_score, :match_score,
                   :match_analysis, :generated_opener, :alt_opener, :created_at)""",
                {
                    "user_id": match["user_id"],
                    "post_id": match["post_id"],
                    "author_id": match["author_id"],
                    "authenticity_score": match.get("authenticity_score"),
                    "seriousness_score": match.get("seriousness_score"),
                    "match_score": match.get("match_score"),
                    "match_analysis": match.get("match_analysis"),
                    "generated_opener": match.get("generated_opener"),
                    "alt_opener": match.get("alt_opener"),
                    "created_at": datetime.now().isoformat(),
                },
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_unpushed_matches(self, user_id: int, limit: int = 5) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT m.*, p.content as post_content, p.post_url, p.image_urls,
                   a.nickname, a.ip_location, a.bio, a.age_tag, a.avatar_url
                   FROM matches m
                   JOIN posts p ON m.post_id = p.id
                   JOIN authors a ON m.author_id = a.id
                   WHERE m.user_id = ? AND m.pushed_at IS NULL
                   ORDER BY m.match_score DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_match_pushed(self, match_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE matches SET pushed_at=? WHERE id=?",
                (datetime.now().isoformat(), match_id),
            )

    def update_match_action(self, match_id: int, action: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE matches SET user_action=? WHERE id=?", (action, match_id)
            )

    def update_match_opener(self, match_id: int, opener: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE matches SET generated_opener=? WHERE id=?", (opener, match_id)
            )

    def get_already_matched_author_ids(self, user_id: int) -> set[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT author_id FROM matches WHERE user_id=?", (user_id,)
            ).fetchall()
            return {r["author_id"] for r in rows}

    def get_match_by_id(self, match_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT m.*, p.content as post_content, p.post_url,
                   a.nickname, a.ip_location, a.bio, a.age_tag
                   FROM matches m
                   JOIN posts p ON m.post_id = p.id
                   JOIN authors a ON m.author_id = a.id
                   WHERE m.id=?""",
                (match_id,),
            ).fetchone()
            return dict(row) if row else None
