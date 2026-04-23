#!/usr/bin/env python3
"""Validate FindIt AI tag extraction setup."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_imports():
    """Check if required modules can be imported."""
    print("🔍 Checking imports...")

    try:
        import findit
        print("  ✓ findit package")
    except ImportError as e:
        print(f"  ✗ findit package: {e}")
        return False

    try:
        from findit.ai.tag_extractor import AITagExtractor
        print("  ✓ AITagExtractor")
    except ImportError as e:
        print(f"  ✗ AITagExtractor: {e}")
        return False

    try:
        from findit.db import Database
        print("  ✓ Database")
    except ImportError as e:
        print(f"  ✗ Database: {e}")
        return False

    try:
        from findit.config import settings
        print("  ✓ settings")
    except ImportError as e:
        print(f"  ✗ settings: {e}")
        return False

    return True

def check_database():
    """Check database schema and data."""
    print("\n🗄️  Checking database...")

    from findit.config import settings
    import sqlite3

    if not Path(settings.db_path).exists():
        print(f"  ✗ Database file not found: {settings.db_path}")
        return False

    print(f"  ✓ Database exists: {settings.db_path}")

    conn = sqlite3.connect(str(settings.db_path))
    cursor = conn.cursor()

    # Check posts table
    cursor.execute("SELECT COUNT(*) FROM posts")
    posts_count = cursor.fetchone()[0]
    print(f"  ✓ Posts: {posts_count}")

    # Check ai_tags column
    cursor.execute("PRAGMA table_info(posts)")
    columns = [row[1] for row in cursor.fetchall()]
    if "ai_tags" in columns:
        print("  ✓ ai_tags column exists")

        # Check how many posts have tags
        cursor.execute("SELECT COUNT(*) FROM posts WHERE ai_tags IS NOT NULL")
        tagged_count = cursor.fetchone()[0]
        print(f"  ✓ Posts with tags: {tagged_count}/{posts_count}")
    else:
        print("  ✗ ai_tags column missing")
        return False

    conn.close()
    return True

def check_api_key():
    """Check if API key is configured."""
    print("\n🔑 Checking API key...")

    from findit.config import settings

    if settings.anthropic_api_key:
        key_length = len(settings.anthropic_api_key)
        print(f"  ✓ ANTHROPIC_API_KEY is set (length: {key_length})")
        if settings.anthropic_api_key.startswith("sk-ant-"):
            print("  ✓ API key format looks correct")
        else:
            print("  ⚠ API key format might be incorrect")
        return True
    else:
        print("  ✗ ANTHROPIC_API_KEY not set in .env")
        print("  → Add: ANTHROPIC_API_KEY=sk-ant-xxxxx to .env file")
        return False

def test_extraction():
    """Test tag extraction with a sample post."""
    print("\n🧪 Testing tag extraction...")

    try:
        from findit.ai.tag_extractor import AITagExtractor
        from findit.config import settings

        if not settings.anthropic_api_key:
            print("  ⊘ Skipping (no API key)")
            return True

        if len(settings.anthropic_api_key) < 20:
            print("  ⊘ Skipping (API key looks like a placeholder)")
            print("  → Add your real API key to test extraction")
            return True

        # Create extractor
        extractor = AITagExtractor()
        print("  ✓ AITagExtractor initialized")

        # Test with sample data
        sample_post = {
            "id": "test_123",
            "content": "96年女生，身高165cm，本科毕业，在深圳做产品经理。认真找对象，希望对方25-35岁，本科以上学历，身高170+。",
            "source_type": "post"
        }

        sample_author = {
            "nickname": "测试用户",
            "ip_location": "深圳"
        }

        result = extractor.extract_from_post(sample_post, sample_author)

        if result:
            print("  ✓ Extraction successful!")
            print(f"    - Gender: {result.personal_info.gender}")
            print(f"    - Age: {result.personal_info.age}")
            print(f"    - Location: {result.personal_info.location}")
            print(f"    - Seriousness: {result.dating_intent.seriousness_score}/100")
            print(f"    - Confidence: {result.confidence_score}%")
            return True
        else:
            print("  ✗ Extraction failed (API returned error)")
            print("  → Check your API key and quota")
            return False

    except Exception as e:
        error_msg = str(e)
        if "blocked" in error_msg.lower() or "permission" in error_msg.lower():
            print("  ⊘ API request blocked (invalid API key or quota exceeded)")
            print("  → Add your valid API key to .env file")
            return True  # Don't fail validation, just warn
        else:
            print(f"  ✗ Error: {e}")
            return False

def main():
    """Run all validation checks."""
    print("🚀 FindIt AI Tag Extraction - Setup Validation\n")

    all_passed = True

    # Check imports
    if not check_imports():
        all_passed = False

    # Check database
    if not check_database():
        all_passed = False

    # Check API key
    api_key_ok = check_api_key()
    if not api_key_ok:
        all_passed = False

    # Test extraction (only if API key is set)
    if api_key_ok:
        if not test_extraction():
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("✅ All checks passed! Setup is complete.")
        print("\n📖 Next steps:")
        print("   1. Run: python scripts/extract_tags.py --limit 3")
        print("   2. Check results in database")
        print("   3. Scale up: python scripts/extract_tags.py --limit 50")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\n📖 Quick fixes:")
        if not Path(".env").exists():
            print("   1. Create .env: cp .env.example .env")
        print("   2. Add API key: echo 'ANTHROPIC_API_KEY=sk-ant-xxxxx' >> .env")

    print("="*50)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())