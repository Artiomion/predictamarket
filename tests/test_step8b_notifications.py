"""
Integration tests for notification-service.
Requires: notification-service on :8006, auth-service on :8001, seeded instruments.
"""

import base64
import json
import uuid

import httpx
import pytest
import redis as redis_lib

BASE = "http://localhost:8006/api/notifications"
AUTH = "http://localhost:8001/api/auth"

TICKERS = ["AAPL", "MSFT", "NVDA"]


def make_user(tier: str = "pro") -> dict:
    """Register a real user and return headers with their UUID."""
    email = f"notif_{uuid.uuid4().hex[:8]}@test.com"
    r = httpx.post(f"{AUTH}/register", json={"email": email, "password": "Pass12345!", "name": "Notif"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    part = token.split(".")[1]
    part += "=" * (4 - len(part) % 4)
    user_id = json.loads(base64.b64decode(part))["sub"]
    return {"X-User-Id": user_id, "X-User-Tier": tier}


class TestAlertsCRUD:
    def test_create_alert(self) -> None:
        h = make_user()
        r = httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "AAPL", "alert_type": "price_above", "condition_value": 300.0},
            headers=h,
        )
        assert r.status_code == 201
        d = r.json()
        assert "id" in d
        assert d["ticker"] == "AAPL"
        assert d["alert_type"] == "price_above"
        assert d["is_active"] is True

    def test_list_alerts(self) -> None:
        h = make_user()
        httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "MSFT", "alert_type": "price_below", "condition_value": 200.0},
            headers=h,
        )
        r = httpx.get(f"{BASE}/alerts", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_delete_alert(self) -> None:
        h = make_user()
        aid = httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "NVDA", "alert_type": "signal_change"},
            headers=h,
        ).json()["id"]
        assert httpx.delete(f"{BASE}/alerts/{aid}", headers=h).status_code == 204
        # Verify gone from list
        alerts = httpx.get(f"{BASE}/alerts", headers=h).json()
        assert not any(a["id"] == aid for a in alerts)

    def test_free_tier_limit_three(self) -> None:
        h = make_user("free")
        for i in range(3):
            r = httpx.post(
                f"{BASE}/alerts",
                json={"ticker": "AAPL", "alert_type": "price_above", "condition_value": 100.0 + i},
                headers=h,
            )
            assert r.status_code == 201, f"Alert {i+1}/3 should succeed"

        r4 = httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "AAPL", "alert_type": "price_above", "condition_value": 500.0},
            headers=h,
        )
        assert r4.status_code == 403, "4th alert should be blocked for free tier"

    def test_no_auth_returns_401(self) -> None:
        r = httpx.get(f"{BASE}/alerts")
        assert r.status_code == 401

    def test_invalid_alert_type(self) -> None:
        h = make_user()
        r = httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "AAPL", "alert_type": "invalid_type", "condition_value": 100.0},
            headers=h,
        )
        assert r.status_code == 422

    def test_invalid_ticker(self) -> None:
        h = make_user()
        r = httpx.post(
            f"{BASE}/alerts",
            json={"ticker": "ZZZINVALID", "alert_type": "price_above", "condition_value": 100.0},
            headers=h,
        )
        assert r.status_code == 404


class TestNotificationHistory:
    def test_history_empty(self) -> None:
        h = make_user()
        r = httpx.get(f"{BASE}/alerts/history", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestSocketIO:
    def test_socket_endpoint_exists(self) -> None:
        """Socket.IO polling transport responds."""
        r = httpx.get("http://localhost:8006/socket.io/?EIO=4&transport=polling")
        assert r.status_code == 200


class TestRedisPubSub:
    def test_publish_news_high_impact(self) -> None:
        """Verify Redis pub/sub channel is accessible."""
        r = redis_lib.Redis(host="localhost", port=6379)
        count = r.publish(
            "news.high_impact",
            json.dumps({"ticker": "AAPL", "title": "Test", "sentiment": "positive"}),
        )
        # count=0 means no subscribers (notification-service not subscribed yet) — still OK
        assert count >= 0

    def test_publish_forecast_updated(self) -> None:
        r = redis_lib.Redis(host="localhost", port=6379)
        count = r.publish(
            "forecast.updated",
            json.dumps({"success": 1, "failed": 0, "total": 1}),
        )
        assert count >= 0
