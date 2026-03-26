"""Tests for rule-based filtering (SharedFilter + UserFilter)."""

from findit.ai.filter_rules import SharedFilter, UserFilter, RuleFilter


class TestSharedFilter:
    """Tests for user-independent shared filtering."""

    def setup_method(self):
        self.f = SharedFilter()

    # ── Matchmaker detection ────────────────────────────────────────────

    def test_filters_matchmaker_keyword_in_nickname(self):
        author = {
            "nickname": "深圳红娘小王",
            "bio": "帮你找到真爱",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "matchmaker_keyword" in reason

    def test_filters_matchmaker_keyword_in_bio(self):
        author = {
            "nickname": "小王",
            "bio": "专业婚介服务，十年经验",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "matchmaker_keyword" in reason

    def test_filters_matchmaker_service_keywords(self):
        """Test new service-related keywords like 加v, 免费介绍."""
        for keyword in ["加v咨询", "免费介绍对象", "进群了解"]:
            author = {
                "nickname": "小花",
                "bio": keyword,
                "ip_location": "深圳",
                "notes_summary": [{"title": "日常"}],
            }
            keep, reason = self.f.evaluate(author)
            assert keep is False, f"Should filter '{keyword}'"
            assert "matchmaker_keyword" in reason

    def test_filters_high_dating_ratio(self):
        """Notes where >60% are dating posts → matchmaker."""
        author = {
            "nickname": "小红",
            "bio": "帮你找到真爱",
            "ip_location": "深圳",
            "followers": 5000,
            "following": 100,
            "notes_summary": [
                {"title": "95年找对象"},
                {"title": "征婚启事"},
                {"title": "找男友"},
                {"title": "相亲"},
                {"title": "单身交友"},
                {"title": "日常穿搭"},
            ],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "dating_ratio" in reason

    def test_filters_multiple_ages_in_titles(self):
        """Different birth years in note titles → posting for multiple people."""
        author = {
            "nickname": "小花",
            "bio": "爱生活",
            "ip_location": "深圳",
            "notes_summary": [
                {"title": "95年深圳找对象"},
                {"title": "98年女生征男友"},
                {"title": "00年单身"},
                {"title": "日常分享"},
            ],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "multiple_ages" in reason

    def test_keeps_single_age_in_titles(self):
        """Same birth year repeated is fine (real person)."""
        author = {
            "nickname": "小花",
            "bio": "爱生活",
            "ip_location": "深圳",
            "notes_summary": [
                {"title": "95年找对象"},
                {"title": "95年女生日常"},
                {"title": "周末去哪玩"},
            ],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is True

    # ── Marketing detection ─────────────────────────────────────────────

    def test_filters_marketing_keyword(self):
        author = {
            "nickname": "品牌合作找我",
            "bio": "全网推广",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "marketing" in reason

    def test_filters_high_followers_low_content(self):
        author = {
            "nickname": "小美",
            "bio": "爱美食",
            "ip_location": "深圳",
            "followers": 100000,
            "notes_summary": [{"title": "唯一一篇"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "marketing" in reason

    # ── Empty account ───────────────────────────────────────────────────

    def test_filters_empty_account(self):
        author = {
            "nickname": "user123",
            "bio": "",
            "ip_location": "深圳",
            "following": 0,
            "notes_summary": [],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "empty" in reason

    # ── Inactive detection ──────────────────────────────────────────────

    def test_filters_inactive_old_posts(self):
        author = {
            "nickname": "小花",
            "bio": "爱生活",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        posts = [{"created_at": "2024-01-01T00:00:00"}]
        keep, reason = self.f.evaluate(author, posts=posts)
        assert keep is False
        assert "inactive" in reason

    def test_keeps_recent_posts(self):
        from datetime import datetime
        author = {
            "nickname": "小花",
            "bio": "爱生活",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        posts = [{"created_at": datetime.now().isoformat()}]
        keep, reason = self.f.evaluate(author, posts=posts)
        assert keep is True

    # ── Suspicious patterns ─────────────────────────────────────────────

    def test_filters_default_name_with_dating_posts(self):
        author = {
            "nickname": "小红书用户ABC123",
            "bio": "",
            "ip_location": "深圳",
            "notes_summary": [
                {"title": "找对象"},
                {"title": "征婚"},
                {"title": "美食分享"},
            ],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "default_name" in reason

    def test_filters_contact_in_bio(self):
        author = {
            "nickname": "小花",
            "bio": "v：match123456",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "contact_in_bio" in reason

    def test_filters_phone_in_bio(self):
        author = {
            "nickname": "小花",
            "bio": "联系我13800138000",
            "ip_location": "深圳",
            "notes_summary": [{"title": "日常"}],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is False
        assert "contact_in_bio" in reason

    # ── Normal profiles pass ────────────────────────────────────────────

    def test_keeps_normal_profile(self):
        author = {
            "nickname": "小花",
            "bio": "爱旅行爱美食",
            "ip_location": "深圳",
            "followers": 500,
            "following": 200,
            "notes_summary": [
                {"title": "周末去哪玩"},
                {"title": "今天做了好吃的"},
            ],
        }
        keep, reason = self.f.evaluate(author)
        assert keep is True
        assert reason is None


class TestUserFilter:
    """Tests for per-user filtering."""

    def test_filters_wrong_city(self):
        f = UserFilter(user_city="深圳", allow_remote=False)
        author = {"ip_location": "北京"}
        keep, reason = f.evaluate(author)
        assert keep is False
        assert "location" in reason

    def test_allows_same_city(self):
        f = UserFilter(user_city="深圳")
        author = {"ip_location": "广东深圳"}
        keep, reason = f.evaluate(author)
        assert keep is True

    def test_allows_remote_when_configured(self):
        f = UserFilter(user_city="深圳", allow_remote=True)
        author = {"ip_location": "北京"}
        keep, reason = f.evaluate(author)
        assert keep is True

    def test_allows_unknown_location(self):
        f = UserFilter(user_city="深圳")
        author = {"ip_location": ""}
        keep, reason = f.evaluate(author)
        assert keep is True


class TestRuleFilterCompat:
    """Test backward-compatible RuleFilter wrapper."""

    def test_combines_shared_and_user_filters(self):
        f = RuleFilter(user_city="深圳")
        # Should be filtered by shared filter (matchmaker keyword)
        author = {"nickname": "红娘小王", "bio": "", "notes_summary": [{"title": "a"}]}
        keep, reason = f.evaluate(author)
        assert keep is False

    def test_filters_by_location(self):
        f = RuleFilter(user_city="深圳", allow_remote=False)
        author = {
            "nickname": "小花", "bio": "爱生活",
            "ip_location": "北京",
            "notes_summary": [{"title": "日常"}],
            "following": 10,
        }
        keep, reason = f.evaluate(author)
        assert keep is False
        assert "location" in reason
