#!/usr/bin/env python3
"""Test script for AI tag extraction with sample data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_with_mock_data():
    """Test tag extraction with mock data (no API call)."""
    from findit.ai.tag_extractor import TagExtractionResult, PersonalInfo, Requirements, DatingIntent

    # Mock result
    mock_result = TagExtractionResult(
        personal_info=PersonalInfo(
            gender="女",
            age=26,
            height=165,
            education="本科",
            location="深圳",
            occupation="产品经理"
        ),
        requirements=Requirements(
            preferred_gender="男",
            age_range={"min": 25, "max": 35},
            min_height=170,
            education="本科以上",
            location="深圳"
        ),
        dating_intent=DatingIntent(
            seriousness_score=85,
            intent_type="认真征婚",
            urgency="正常"
        ),
        extracted_tags=["26岁女", "深圳", "本科", "产品经理", "认真找对象"],
        confidence_score=90
    )

    print("✓ Mock tag extraction test passed")
    print(f"  Result: {mock_result.to_dict()}")

def test_database_query():
    """Test database queries."""
    from findit.db import Database
    from findit.config import settings

    db = Database(settings.db_path)

    # Get some posts
    posts = db.get_unprocessed_posts(limit=3)
    print(f"✓ Found {len(posts)} posts in database")

    for post in posts:
        author = db.get_author(post["author_id"])
        print(f"  Post: {post['id']}")
        print(f"    Content: {post['content'][:50]}...")
        if author:
            print(f"    Author: {author.get('nickname', 'Unknown')}")

def main():
    print("🧪 Testing FindIt AI Tag Extraction\n")

    print("1. Testing with mock data...")
    test_with_mock_data()
    print()

    print("2. Testing database queries...")
    test_database_query()
    print()

    print("3. API testing setup...")
    print("   To test with real Claude API:")
    print("   1. Edit .env file and add: ANTHROPIC_API_KEY=sk-ant-xxx")
    print("   2. Run: python scripts/extract_tags.py --limit 3")
    print()

if __name__ == "__main__":
    main()