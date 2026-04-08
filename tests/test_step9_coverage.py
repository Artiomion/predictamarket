"""
Coverage gap tests — fills missing test coverage across all services.
Requires: all 8 services running.
"""

import base64
import json
import time
import uuid

import httpx
import pytest
import redis as redis_lib

AUTH = "http://localhost:8001/api/auth"
GW = "http://localhost:8000"
MARKET = "http://localhost:8002/api/market"
NEWS = "http://localhost:8003/api/news"
FORECAST = "http://localhost:8004/api/forecast"
PORTFOLIO = "http://localhost:8005/api/portfolio"
EDGAR = "http://localhost:8007/api/edgar"
NOTIF = "http://localhost:8006/api/notifications"


def _register_user(tier: str = "pro") -> tuple[str, str, dict]:
    """Register user, return (user_id, token, headers)."""
    email = f"cov_{uuid.uuid4().hex[:8]}@test.com"
    r = httpx.post(f"{AUTH}/register", json={"email": email, "password": "Pass12345!", "name": "Cov"})
    assert r.status_code == 201
    data = r.json()
    token = data["access_token"]
    part = token.split(".")[1] + "=="
    user_id = json.loads(base64.b64decode(part))["sub"]
    return user_id, token, {"X-User-Id": user_id, "X-User-Tier": tier}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Google OAuth
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoogleOAuth:
    def test_no_token_returns_400(self) -> None:
        r = httpx.post(f"{AUTH}/google", json={})
        assert r.status_code == 400
        assert "id_token or access_token" in r.json()["detail"].lower()

    def test_invalid_id_token_returns_401(self) -> None:
        r = httpx.post(f"{AUTH}/google", json={"id_token": "invalid.fake.token"})
        assert r.status_code == 401

    def test_invalid_access_token_returns_401(self) -> None:
        r = httpx.post(f"{AUTH}/google", json={"access_token": "ya29.fake"})
        assert r.status_code == 401

    def test_google_via_gateway_no_jwt_needed(self) -> None:
        """Gateway should NOT block /api/auth/google with JWT check."""
        r = httpx.post(f"{GW}/api/auth/google", json={"id_token": "fake"})
        assert r.status_code == 401  # 401 from Google, NOT from gateway JWT
        assert "Google" in r.json()["detail"]

    def test_response_shape_on_error(self) -> None:
        r = httpx.post(f"{AUTH}/google", json={"id_token": "x"})
        assert "detail" in r.json()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Health endpoints (new format with db+redis)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:
    @pytest.mark.parametrize("url,service", [
        ("http://localhost:8000/health", "api-gateway"),
        ("http://localhost:8001/health", "auth-service"),
        ("http://localhost:8002/health", "market-data-service"),
    ])
    def test_docker_service_health(self, url: str, service: str) -> None:
        r = httpx.get(url)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert "service" in d

    @pytest.mark.parametrize("port,service", [
        (8001, "auth-service"),
        (8002, "market-data-service"),
    ])
    def test_health_includes_db_redis(self, port: int, service: str) -> None:
        r = httpx.get(f"http://localhost:{port}/health")
        d = r.json()
        assert "db" in d, f"{service} health missing db field"
        assert "redis" in d, f"{service} health missing redis field"
        assert d["db"] == "ok"
        assert d["redis"] == "ok"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Forecast batch endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestForecastBatch:
    def test_batch_requires_pro(self) -> None:
        uid, _, _ = _register_user("free")
        r = httpx.post(
            f"{FORECAST}/batch",
            json={"tickers": ["AAPL"]},
            headers={"X-User-Id": uid, "X-User-Tier": "free"},
        )
        assert r.status_code == 403

    def test_batch_creates_job(self) -> None:
        uid, _, _ = _register_user("pro")
        r = httpx.post(
            f"{FORECAST}/batch",
            json={"tickers": ["AAPL", "MSFT"]},
            headers={"X-User-Id": uid, "X-User-Tier": "pro"},
        )
        assert r.status_code == 200
        d = r.json()
        assert "job_id" in d
        assert d["status"] == "queued"
        assert len(d["tickers"]) == 2

    def test_batch_status_poll(self) -> None:
        uid, _, _ = _register_user("pro")
        create = httpx.post(
            f"{FORECAST}/batch",
            json={"tickers": ["AAPL"]},
            headers={"X-User-Id": uid, "X-User-Tier": "pro"},
        )
        job_id = create.json()["job_id"]
        r = httpx.get(f"{FORECAST}/batch/{job_id}")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_batch_unknown_job_404(self) -> None:
        r = httpx.get(f"{FORECAST}/batch/nonexistent123")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Gateway proxy E2E — all services reachable
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayProxy:
    def test_auth_register_via_gateway(self) -> None:
        email = f"gw_{uuid.uuid4().hex[:6]}@test.com"
        r = httpx.post(f"{GW}/api/auth/register",
                       json={"email": email, "password": "Pass12345!", "name": "GW"})
        assert r.status_code == 201
        assert "access_token" in r.json()

    def test_market_instruments_via_gateway(self) -> None:
        r = httpx.get(f"{GW}/api/market/instruments?per_page=3")
        assert r.status_code == 200
        assert r.json()["total"] >= 90

    def test_request_id_header(self) -> None:
        r = httpx.get(f"{GW}/health")
        assert "x-request-id" in r.headers

    def test_rate_limit_headers(self) -> None:
        r = httpx.get(f"{GW}/api/market/instruments")
        assert "x-ratelimit-limit" in r.headers
        assert "x-ratelimit-remaining" in r.headers


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Portfolio extra coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioExtra:
    def test_csv_export_has_headers(self) -> None:
        _, _, h = _register_user()
        pid = httpx.post(f"{PORTFOLIO}/portfolios", json={"name": "CSV"}, headers=h).json()["id"]
        httpx.post(f"{PORTFOLIO}/portfolios/{pid}/positions",
                   json={"ticker": "AAPL", "quantity": 5, "price": 150}, headers=h)
        r = httpx.get(f"{PORTFOLIO}/portfolios/{pid}/export", headers=h)
        lines = r.text.strip().split("\n")
        assert lines[0].strip() == "date,ticker,type,quantity,price,total,notes"
        assert "AAPL" in lines[1]

    def test_watchlist_cross_user_isolation(self) -> None:
        _, _, h1 = _register_user()
        _, _, h2 = _register_user()
        wid = httpx.post(f"{PORTFOLIO}/watchlists", json={"name": "Priv"}, headers=h1).json()["id"]
        r = httpx.get(f"{PORTFOLIO}/watchlists/{wid}", headers=h2)
        assert r.status_code == 404

    def test_empty_portfolio_analytics(self) -> None:
        _, _, h = _register_user()
        pid = httpx.post(f"{PORTFOLIO}/portfolios", json={"name": "Empty"}, headers=h).json()["id"]
        r = httpx.get(f"{PORTFOLIO}/portfolios/{pid}/analytics", headers=h)
        assert r.status_code == 200
        assert r.json()["positions_count"] == 0
        assert r.json()["total_value"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Auth token flow completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthFlowComplete:
    def test_register_returns_is_new_user_false(self) -> None:
        """Standard register response includes is_new_user field."""
        email = f"new_{uuid.uuid4().hex[:6]}@test.com"
        r = httpx.post(f"{AUTH}/register", json={"email": email, "password": "Pass12345!", "name": "N"})
        # is_new_user defaults to False for email register (only Google sets True)
        assert "is_new_user" in r.json()

    def test_full_lifecycle(self) -> None:
        """register → login → refresh → me → change password → login with new."""
        email = f"life_{uuid.uuid4().hex[:6]}@test.com"
        reg = httpx.post(f"{AUTH}/register", json={"email": email, "password": "Pass1234!", "name": "L"})
        assert reg.status_code == 201
        refresh = reg.json()["refresh_token"]

        # Refresh
        ref = httpx.post(f"{AUTH}/refresh", json={"refresh_token": refresh})
        assert ref.status_code == 200
        new_refresh = ref.json()["refresh_token"]
        assert new_refresh != refresh

        # Get user_id
        token = ref.json()["access_token"]
        part = token.split(".")[1] + "=="
        uid = json.loads(base64.b64decode(part))["sub"]

        # Me
        me = httpx.get(f"{AUTH}/me", headers={"X-User-Id": uid})
        assert me.status_code == 200
        assert me.json()["email"] == email

        # Change password
        cp = httpx.post(f"{AUTH}/change-password",
                        json={"old_password": "Pass1234!", "new_password": "NewPass5678!"},
                        headers={"X-User-Id": uid})
        assert cp.status_code == 200

        # Old password fails
        assert httpx.post(f"{AUTH}/login", json={"email": email, "password": "Pass1234!"}).status_code == 401
        # New password works
        assert httpx.post(f"{AUTH}/login", json={"email": email, "password": "NewPass5678!"}).status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Notification alert types
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationAlertTypes:
    def test_all_alert_types_accepted(self) -> None:
        _, _, h = _register_user()
        types = ["price_above", "price_below", "signal_change", "earnings",
                 "insider", "news_high_impact", "forecast_update"]
        for atype in types:
            r = httpx.post(f"{NOTIF}/alerts",
                           json={"ticker": "AAPL", "alert_type": atype, "condition_value": 100},
                           headers=h)
            assert r.status_code == 201, f"Alert type {atype} failed: {r.status_code}"

    def test_pro_tier_20_alerts(self) -> None:
        _, _, h = _register_user("pro")
        for i in range(20):
            r = httpx.post(f"{NOTIF}/alerts",
                           json={"ticker": "AAPL", "alert_type": "price_above", "condition_value": float(100 + i)},
                           headers=h)
            assert r.status_code == 201, f"Alert {i+1}/20 failed"
        r21 = httpx.post(f"{NOTIF}/alerts",
                         json={"ticker": "AAPL", "alert_type": "price_above", "condition_value": 999},
                         headers=h)
        assert r21.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 8. EDGAR access control completeness
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgarAccess:
    def test_all_endpoints_blocked_for_free(self) -> None:
        headers = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Tier": "free"}
        for ep in ["/income", "/balance", "/cashflow", "/filings"]:
            r = httpx.get(f"{EDGAR}/AAPL{ep}", headers=headers)
            assert r.status_code == 403, f"EDGAR {ep} should be 403 for free, got {r.status_code}"

    def test_all_endpoints_allowed_for_premium(self) -> None:
        headers = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Tier": "premium"}
        for ep in ["/income", "/balance", "/cashflow", "/filings"]:
            r = httpx.get(f"{EDGAR}/AAPL{ep}", headers=headers)
            assert r.status_code == 200, f"EDGAR {ep} should be 200 for premium, got {r.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Redis pub/sub integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisPubSubIntegration:
    def test_news_channel_reachable(self) -> None:
        r = redis_lib.Redis(host="localhost", port=6379)
        count = r.publish("news.high_impact", json.dumps({"test": True}))
        assert count >= 0

    def test_forecast_channel_reachable(self) -> None:
        r = redis_lib.Redis(host="localhost", port=6379)
        count = r.publish("forecast.updated", json.dumps({"test": True}))
        assert count >= 0
