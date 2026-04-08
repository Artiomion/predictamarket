"""
Integration tests for news-service.
Requires: news-service running on localhost:8003, with articles already fetched.
"""

import json

import httpx
import pytest
import redis as redis_lib

BASE = "http://localhost:8003/api/news"


class TestNewsFetch:
    def test_articles_exist(self) -> None:
        r = httpx.get(f"{BASE}/news?per_page=20")
        assert r.status_code == 200
        assert len(r.json()["data"]) > 0, "No articles — run fetch_news.py first"

    def test_article_structure(self) -> None:
        r = httpx.get(f"{BASE}/news?per_page=1")
        article = r.json()["data"][0]
        for field in ["id", "title", "source", "published_at", "url",
                      "sentiment_label", "sentiment_score", "impact_level", "tickers"]:
            assert field in article, f"Field {field} missing"

    def test_sentiment_values(self) -> None:
        r = httpx.get(f"{BASE}/news?per_page=1")
        a = r.json()["data"][0]
        assert a["sentiment_label"] in ["positive", "neutral", "negative"]
        assert 0.0 <= a["sentiment_score"] <= 1.0
        assert a["impact_level"] in ["high", "medium", "low"]

    def test_finbert_actually_works(self) -> None:
        """FinBERT should produce varied sentiment across articles."""
        r = httpx.get(f"{BASE}/news?per_page=50")
        sentiments = set(a["sentiment_label"] for a in r.json()["data"])
        assert len(sentiments) >= 2, \
            f"FinBERT returns only {sentiments} — model may not be loaded"


class TestFilters:
    def test_filter_sentiment(self) -> None:
        r = httpx.get(f"{BASE}/news?sentiment=positive")
        assert r.status_code == 200
        for a in r.json()["data"]:
            assert a["sentiment_label"] == "positive"

    def test_filter_impact(self) -> None:
        r = httpx.get(f"{BASE}/news?impact=high")
        assert r.status_code == 200
        for a in r.json()["data"]:
            assert a["impact_level"] == "high"

    def test_filter_ticker(self) -> None:
        # Use CPB which has the most articles matched
        r = httpx.get(f"{BASE}/news?ticker=CPB&per_page=10")
        assert r.status_code == 200
        for a in r.json()["data"]:
            assert "CPB" in a.get("tickers", []), \
                f"Article {a['id']} not linked to CPB"

    def test_pagination(self) -> None:
        p1 = httpx.get(f"{BASE}/news?page=1&per_page=5").json()["data"]
        p2 = httpx.get(f"{BASE}/news?page=2&per_page=5").json()["data"]
        ids1 = {a["id"] for a in p1}
        ids2 = {a["id"] for a in p2}
        assert ids1 & ids2 == set(), "Pages overlap"

    def test_invalid_sentiment_filter(self) -> None:
        r = httpx.get(f"{BASE}/news?sentiment=invalid")
        assert r.status_code == 422


class TestTickerNews:
    def test_ticker_news_returns_paginated(self) -> None:
        r = httpx.get(f"{BASE}/news/CPB")
        assert r.status_code == 200
        data = r.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] > 0

    def test_empty_for_unknown_ticker(self) -> None:
        r = httpx.get(f"{BASE}/news/XXXX_NOSUCHCO")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["data"] == []


class TestSentimentTrend:
    def test_trend_structure(self) -> None:
        # Use a ticker that has sentiment_daily data
        r = httpx.get(f"{BASE}/news/CPB/sentiment?days=30")
        assert r.status_code == 200
        data = r.json()
        if data:
            for field in ["date", "avg_sentiment", "news_count"]:
                assert field in data[0], f"Field {field} missing in sentiment trend"

    def test_empty_for_unknown_ticker(self) -> None:
        r = httpx.get(f"{BASE}/news/ZZZZ/sentiment?days=7")
        assert r.status_code == 200
        assert r.json() == []


class TestNewsFeed:
    def test_feed_requires_auth(self) -> None:
        r = httpx.get(f"{BASE}/feed")
        assert r.status_code == 401

    def test_feed_with_user_id(self) -> None:
        r = httpx.get(
            f"{BASE}/feed",
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )
        assert r.status_code == 200
        assert "data" in r.json()


class TestRedisPubSub:
    def test_channel_available(self) -> None:
        """Verify Redis pub/sub channel is accessible."""
        r = redis_lib.Redis(host="localhost", port=6379)
        count = r.publish(
            "news.high_impact",
            json.dumps({"ticker": "TEST", "sentiment": "positive", "impact": "high"}),
        )
        # count >= 0 means channel is accessible (0 = no subscribers, which is fine)
        assert count >= 0, "Redis pub/sub not available"
        print(f"\n  Subscribers on news.high_impact: {count}")
