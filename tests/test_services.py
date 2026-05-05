"""Tests for the service layer (CrawlerService, MatchingService)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from findit.db import Database
from findit.services.crawler_service import CrawlerService
from findit.services.matching_service import MatchingService


def _make_db() -> Database:
    """Create a temporary test database."""
    tmpdir = tempfile.mkdtemp()
    return Database(Path(tmpdir) / "test.db")


class TestCrawlerServiceFilter:
    """Test the shared filtering part of the crawler service."""

    def test_shared_filter_marks_matchmaker(self):
        db = _make_db()
        db.upsert_author({
            "id": "a1",
            "nickname": "红娘小王",
            "bio": "婚介服务",
            "ip_location": "深圳",
        })

        service = CrawlerService(db=db)
        filtered = service.run_shared_filter()

        assert filtered == 1
        author = db.get_author("a1")
        assert author["is_filtered_out"] == 1
        assert "matchmaker" in author["filter_reason"]

    def test_shared_filter_passes_normal(self):
        """Early-stage pass-through: stays pending_profile, no is_real_person yet."""
        db = _make_db()
        db.upsert_author({
            "id": "a2",
            "nickname": "小花",
            "bio": "爱旅行",
            "ip_location": "深圳",
            "notes_summary": [{"title": "周末日常"}],
        })

        service = CrawlerService(db=db)
        filtered = service.run_shared_filter(final=False)

        assert filtered == 0
        author = db.get_author("a2")
        assert author["is_filtered_out"] == 0
        assert author["crawl_state"] == "pending_profile"
        assert author["is_real_person"] is None  # set only after final filter

    def test_shared_filter_promotes_to_kept_when_final(self):
        """After Step 3 + final filter, pass-through → crawl_state='kept'."""
        db = _make_db()
        db.upsert_author({
            "id": "a5",
            "nickname": "小花",
            "bio": "爱旅行",
            "ip_location": "深圳",
            "notes_summary": [{"title": "周末日常"}],
        })
        db.upsert_post({
            "id": "p5",
            "author_id": "a5",
            "content": "周末跟朋友去爬山,风景超好",
            "source_type": "post",
        })
        db.mark_profile_crawled("a5")

        service = CrawlerService(db=db)
        filtered = service.run_shared_filter(final=True)

        assert filtered == 0
        author = db.get_author("a5")
        assert author["crawl_state"] == "kept"
        assert author["is_real_person"] == 0.5

    def test_shared_filter_marks_proxy_post(self):
        """Posts saying 代发 / 已获本人同意 → matchmaker_proxy_post."""
        db = _make_db()
        db.upsert_author({
            "id": "a3",
            "nickname": "小花",
            "bio": "",
            "ip_location": "深圳",
        })
        db.upsert_post({
            "id": "p3",
            "author_id": "a3",
            "content": "代发,已获本人同意,98年女生找对象",
            "source_type": "post",
        })

        service = CrawlerService(db=db)
        filtered = service.run_shared_filter()

        assert filtered == 1
        author = db.get_author("a3")
        assert author["is_filtered_out"] == 1
        assert author["filter_reason"] == "matchmaker_proxy_post"

    def test_shared_filter_skips_already_filtered(self):
        """Authors already filtered should not be re-processed."""
        db = _make_db()
        db.upsert_author({"id": "a4", "nickname": "小花", "bio": "正常"})
        db.update_author_scores("a4", is_filtered_out=True, filter_reason="manual")

        service = CrawlerService(db=db)
        # get_unfiltered_authors should not return a4
        unfiltered = db.get_unfiltered_authors()
        assert all(a["id"] != "a4" for a in unfiltered)


class TestMatchingService:
    """Test the matching service's candidate selection logic."""

    def test_select_daily_matches_empty(self):
        db = _make_db()
        user = db.get_or_create_user("tg100")

        service = MatchingService(db=db)
        matches = service._select_daily_matches(user["id"])
        assert matches == []

    def test_select_daily_matches_with_data(self):
        db = _make_db()
        db.upsert_author({"id": "a1", "nickname": "Girl", "bio": "爱生活"})
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "找男友", "source_type": "post",
        })
        user = db.get_or_create_user("tg200")

        # Create a match record
        db.create_match({
            "user_id": user["id"],
            "post_id": "p1",
            "author_id": "a1",
            "match_score": 85.0,
            "match_analysis": "条件匹配",
            "generated_opener": "你好",
        })

        service = MatchingService(db=db)
        matches = service._select_daily_matches(user["id"])
        assert len(matches) == 1
        assert matches[0]["match_score"] == 85.0


class TestDBNewMethods:
    """Test new database methods added for the service layer."""

    def test_get_unfiltered_authors(self):
        db = _make_db()
        db.upsert_author({"id": "a1", "nickname": "Normal"})
        db.upsert_author({"id": "a2", "nickname": "Filtered"})
        db.update_author_scores("a2", is_filtered_out=True, filter_reason="test")

        unfiltered = db.get_unfiltered_authors()
        ids = [a["id"] for a in unfiltered]
        assert "a1" in ids
        assert "a2" not in ids

    def test_get_screened_candidates(self):
        db = _make_db()
        db.upsert_author({
            "id": "a1", "nickname": "Screened",
            "ip_location": "深圳",
        })
        db.update_author_scores("a1", is_real_person=0.8)
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "找男友", "source_type": "post",
        })

        candidates = db.get_screened_candidates(city="深圳")
        assert len(candidates) == 1
        assert candidates[0]["nickname"] == "Screened"

    def test_get_screened_candidates_excludes_filtered(self):
        db = _make_db()
        db.upsert_author({"id": "a1", "nickname": "Bad"})
        db.update_author_scores("a1", is_filtered_out=True, filter_reason="test")
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "test", "source_type": "post",
        })

        candidates = db.get_screened_candidates()
        assert len(candidates) == 0

    def test_get_author_posts(self):
        db = _make_db()
        db.upsert_author({"id": "a1", "nickname": "Test"})
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "post1", "source_type": "post",
        })
        db.upsert_post({
            "id": "p2", "author_id": "a1",
            "content": "post2", "source_type": "post",
        })

        posts = db.get_author_posts("a1")
        assert len(posts) == 2


class TestMatchingServiceNoAPI:
    """Test matching service when ANTHROPIC_API_KEY is not configured."""

    def test_init_without_api_key(self):
        """MatchingService should initialize without API key."""
        db = _make_db()
        with patch("findit.services.matching_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.daily_match_count = 5
            mock_settings.high_match_count = 3
            mock_settings.db_path = db.db_path
            service = MatchingService(db=db)
            assert service._api_enabled is False
            assert service.scorer is None
            assert service.opener_gen is None

    def test_create_matches_simple_no_api(self):
        """Without API, matches should be created without scores/openers."""
        db = _make_db()
        db.upsert_author({
            "id": "a1", "nickname": "Girl", "bio": "爱生活",
            "ip_location": "深圳",
        })
        db.update_author_scores("a1", is_real_person=0.5)
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "找男友", "source_type": "post",
        })
        user = db.get_or_create_user("tg_noapi")
        db.update_user("tg_noapi", setup_complete=1, city="深圳")
        user = db.get_user_by_telegram("tg_noapi")

        with patch("findit.services.matching_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.daily_match_count = 5
            mock_settings.high_match_count = 3
            mock_settings.db_path = db.db_path
            service = MatchingService(db=db)
            matches = service.generate_matches(user)

        assert len(matches) == 1
        assert matches[0]["match_score"] is None
        assert matches[0]["generated_opener"] is None

    def test_select_unscored_matches_by_recency(self):
        """Without API, matches should be ordered by crawl time."""
        db = _make_db()
        db.upsert_author({"id": "a1", "nickname": "Girl1", "bio": "hi"})
        db.upsert_author({"id": "a2", "nickname": "Girl2", "bio": "hi"})
        db.upsert_post({
            "id": "p1", "author_id": "a1",
            "content": "找男友", "source_type": "post",
            "crawled_at": "2026-01-01T00:00:00",
        })
        db.upsert_post({
            "id": "p2", "author_id": "a2",
            "content": "找对象", "source_type": "post",
            "crawled_at": "2026-03-01T00:00:00",
        })
        user = db.get_or_create_user("tg_order")

        # Create matches without scores
        db.create_match({
            "user_id": user["id"], "post_id": "p1", "author_id": "a1",
            "match_score": None, "generated_opener": None,
        })
        db.create_match({
            "user_id": user["id"], "post_id": "p2", "author_id": "a2",
            "match_score": None, "generated_opener": None,
        })

        with patch("findit.services.matching_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            mock_settings.daily_match_count = 5
            mock_settings.high_match_count = 3
            mock_settings.db_path = db.db_path
            service = MatchingService(db=db)
            matches = service._select_daily_matches(user["id"])

        assert len(matches) == 2
        # Most recent first
        assert matches[0]["post_id"] == "p2"
        assert matches[1]["post_id"] == "p1"

    def test_init_with_api_key(self):
        """MatchingService with API key should have scorer and opener_gen."""
        db = _make_db()
        with patch("findit.services.matching_service.settings") as mock_settings:
            mock_settings.anthropic_api_key = "sk-test-key"
            mock_settings.daily_match_count = 5
            mock_settings.high_match_count = 3
            mock_settings.db_path = db.db_path
            service = MatchingService(db=db)
            assert service._api_enabled is True
            assert service.scorer is not None
            assert service.opener_gen is not None
