#!/usr/bin/env python3
"""Database migration: Add AI tags column to posts table."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from findit.config import settings

def migrate():
    """Add tags column to posts table."""
    db_path = settings.db_path

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Check if column already exists
        cursor = conn.execute("PRAGMA table_info(posts)")
        columns = [row["name"] for row in cursor.fetchall()]

        if "ai_tags" in columns:
            print("✓ Column 'ai_tags' already exists in posts table")
            return

        # Add the column
        conn.execute("ALTER TABLE posts ADD COLUMN ai_tags TEXT")
        conn.commit()

        print("✓ Added 'ai_tags' column to posts table")
        print("  This column will store JSON-formatted tag extraction results")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()