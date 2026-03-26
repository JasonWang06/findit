"""Tests for rule-based filtering."""

from findit.ai.filter_rules import RuleFilter


def test_keeps_normal_profile():
    f = RuleFilter(user_city="深圳")
    author = {
        "nickname": "小花",
        "bio": "爱旅行爱美食",
        "ip_location": "深圳",
        "followers": 500,
        "following": 200,
        "notes_summary": [{"title": "周末去哪玩"}],
    }
    keep, reason = f.evaluate(author)
    assert keep is True
    assert reason is None


def test_filters_matchmaker():
    f = RuleFilter(user_city="深圳")
    author = {
        "nickname": "深圳红娘小王",
        "bio": "专业婚介服务",
        "ip_location": "深圳",
    }
    keep, reason = f.evaluate(author)
    assert keep is False
    assert "matchmaker" in reason


def test_filters_empty_account():
    f = RuleFilter(user_city="深圳")
    author = {
        "nickname": "user123",
        "bio": "",
        "ip_location": "深圳",
        "following": 0,
        "notes_summary": [],
    }
    keep, reason = f.evaluate(author)
    assert keep is False
    assert "empty" in reason


def test_filters_wrong_city():
    f = RuleFilter(user_city="深圳", allow_remote=False)
    author = {
        "nickname": "小美",
        "bio": "找对象",
        "ip_location": "北京",
        "followers": 100,
        "following": 50,
        "notes_summary": [{"title": "日常"}],
    }
    keep, reason = f.evaluate(author)
    assert keep is False
    assert "location" in reason


def test_allows_remote_when_configured():
    f = RuleFilter(user_city="深圳", allow_remote=True)
    author = {
        "nickname": "小美",
        "bio": "找对象",
        "ip_location": "北京",
        "followers": 100,
        "following": 50,
        "notes_summary": [{"title": "日常"}],
    }
    keep, reason = f.evaluate(author)
    assert keep is True


def test_filters_all_dating_posts_matchmaker():
    f = RuleFilter(user_city="深圳")
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
            {"title": "找对象"},
        ],
    }
    keep, reason = f.evaluate(author)
    assert keep is False
    assert "matchmaker" in reason
