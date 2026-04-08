"""
Integration tests for portfolio-service.
Requires: portfolio-service on :8005, auth-service on :8001, seeded instruments.
"""

import uuid

import httpx
import pytest

BASE = "http://localhost:8005/api/portfolio"
AUTH = "http://localhost:8001/api/auth"

# Valid tickers from our seeded instruments
TICKERS = ["AAPL", "MSFT", "NVDA", "CVX", "LLY"]


def make_user(tier: str = "pro") -> dict:
    """Register a real user via auth-service and return headers."""
    email = f"pf_{uuid.uuid4().hex[:8]}@test.com"
    r = httpx.post(f"{AUTH}/register", json={"email": email, "password": "Pass12345!", "name": "PF Test"})
    assert r.status_code == 201, f"Failed to create user: {r.text}"
    token = r.json()["access_token"]
    # Decode sub from JWT
    import base64, json
    part = token.split(".")[1]
    part += "=" * (4 - len(part) % 4)
    user_id = json.loads(base64.b64decode(part))["sub"]
    return {"X-User-Id": user_id, "X-User-Tier": tier}


class TestPortfolioCRUD:
    def test_create_and_list(self) -> None:
        h = make_user()
        r = httpx.post(f"{BASE}/portfolios", json={"name": "Test"}, headers=h)
        assert r.status_code == 201
        assert "id" in r.json()
        r_list = httpx.get(f"{BASE}/portfolios", headers=h)
        assert any(p["name"] == "Test" for p in r_list.json())

    def test_delete(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "Tmp"}, headers=h).json()["id"]
        assert httpx.delete(f"{BASE}/portfolios/{pid}", headers=h).status_code == 204
        assert httpx.get(f"{BASE}/portfolios/{pid}", headers=h).status_code == 404

    def test_free_tier_limit_one(self) -> None:
        h = make_user("free")
        r1 = httpx.post(f"{BASE}/portfolios", json={"name": "First"}, headers=h)
        assert r1.status_code == 201
        r2 = httpx.post(f"{BASE}/portfolios", json={"name": "Second"}, headers=h)
        assert r2.status_code == 403

    def test_no_cross_user_access(self) -> None:
        h1, h2 = make_user(), make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "Private"}, headers=h1).json()["id"]
        r = httpx.get(f"{BASE}/portfolios/{pid}", headers=h2)
        assert r.status_code == 404, "Should not leak existence to other users"


class TestPositions:
    def test_weighted_average_price(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "AvgTest"}, headers=h).json()["id"]
        httpx.post(f"{BASE}/portfolios/{pid}/positions",
                   json={"ticker": "AAPL", "quantity": 10, "price": 100.0}, headers=h)
        httpx.post(f"{BASE}/portfolios/{pid}/positions",
                   json={"ticker": "AAPL", "quantity": 10, "price": 120.0}, headers=h)

        positions = httpx.get(f"{BASE}/portfolios/{pid}/positions", headers=h).json()
        aapl = next(p for p in positions if p["ticker"] == "AAPL")
        assert aapl["quantity"] == 20
        assert abs(aapl["avg_buy_price"] - 110.0) < 0.01, \
            f"Expected avg=110.0, got {aapl['avg_buy_price']}"

    def test_sell_removes_position(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "SellTest"}, headers=h).json()["id"]
        httpx.post(f"{BASE}/portfolios/{pid}/positions",
                   json={"ticker": "MSFT", "quantity": 5, "price": 400.0}, headers=h)
        r = httpx.delete(f"{BASE}/portfolios/{pid}/positions/MSFT", headers=h)
        assert r.status_code == 204
        positions = httpx.get(f"{BASE}/portfolios/{pid}/positions", headers=h).json()
        assert not any(p["ticker"] == "MSFT" for p in positions)

    def test_partial_sell(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "PartialSell"}, headers=h).json()["id"]
        httpx.post(f"{BASE}/portfolios/{pid}/positions",
                   json={"ticker": "NVDA", "quantity": 10, "price": 800.0}, headers=h)
        httpx.delete(f"{BASE}/portfolios/{pid}/positions/NVDA?quantity=3", headers=h)
        positions = httpx.get(f"{BASE}/portfolios/{pid}/positions", headers=h).json()
        nvda = next(p for p in positions if p["ticker"] == "NVDA")
        assert nvda["quantity"] == 7.0

    def test_invalid_ticker(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "BadTicker"}, headers=h).json()["id"]
        r = httpx.post(f"{BASE}/portfolios/{pid}/positions",
                       json={"ticker": "ZZZINVALID", "quantity": 1, "price": 1.0}, headers=h)
        assert r.status_code == 404


class TestAnalytics:
    def _setup(self, h: dict) -> str:
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "Analytics"}, headers=h).json()["id"]
        for ticker, price in [("AAPL", 150), ("MSFT", 400), ("CVX", 150)]:
            httpx.post(f"{BASE}/portfolios/{pid}/positions",
                       json={"ticker": ticker, "quantity": 10, "price": price}, headers=h)
        return pid

    def test_analytics_fields(self) -> None:
        h = make_user()
        pid = self._setup(h)
        r = httpx.get(f"{BASE}/portfolios/{pid}/analytics", headers=h)
        assert r.status_code == 200
        for field in ["total_value", "total_pnl", "total_pnl_pct", "positions_count",
                      "best_position", "worst_position"]:
            assert field in r.json(), f"Field {field} missing"
        assert r.json()["positions_count"] == 3

    def test_sectors_sum_100(self) -> None:
        h = make_user()
        pid = self._setup(h)
        sectors = httpx.get(f"{BASE}/portfolios/{pid}/sectors", headers=h).json()
        total = sum(s["pct"] for s in sectors)
        assert abs(total - 100.0) < 1.0, f"Sector pct sum = {total}, expected 100"


class TestExport:
    def test_csv_content_type(self) -> None:
        h = make_user()
        pid = httpx.post(f"{BASE}/portfolios", json={"name": "Export"}, headers=h).json()["id"]
        httpx.post(f"{BASE}/portfolios/{pid}/positions",
                   json={"ticker": "AAPL", "quantity": 5, "price": 150.0}, headers=h)
        r = httpx.get(f"{BASE}/portfolios/{pid}/export", headers=h)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "AAPL" in r.text
        assert "date,ticker,type" in r.text  # CSV header


class TestWatchlist:
    def test_full_crud(self) -> None:
        h = make_user()
        wid = httpx.post(f"{BASE}/watchlists", json={"name": "Watch"}, headers=h).json()["id"]
        httpx.post(f"{BASE}/watchlists/{wid}/items", json={"ticker": "NVDA"}, headers=h)
        detail = httpx.get(f"{BASE}/watchlists/{wid}", headers=h).json()
        tickers = [x["ticker"] for x in detail["items"]]
        assert "NVDA" in tickers

        httpx.delete(f"{BASE}/watchlists/{wid}/items/NVDA", headers=h)
        detail2 = httpx.get(f"{BASE}/watchlists/{wid}", headers=h).json()
        assert not any(x["ticker"] == "NVDA" for x in detail2["items"])

    def test_duplicate_item_rejected(self) -> None:
        h = make_user()
        wid = httpx.post(f"{BASE}/watchlists", json={"name": "Dups"}, headers=h).json()["id"]
        r1 = httpx.post(f"{BASE}/watchlists/{wid}/items", json={"ticker": "AAPL"}, headers=h)
        assert r1.status_code == 201
        r2 = httpx.post(f"{BASE}/watchlists/{wid}/items", json={"ticker": "AAPL"}, headers=h)
        assert r2.status_code == 400

    def test_cross_user_denied(self) -> None:
        h1, h2 = make_user(), make_user()
        wid = httpx.post(f"{BASE}/watchlists", json={"name": "Private"}, headers=h1).json()["id"]
        r = httpx.get(f"{BASE}/watchlists/{wid}", headers=h2)
        assert r.status_code == 404
