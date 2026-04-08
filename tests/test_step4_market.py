import time

import httpx
import pytest
import redis

BASE = "http://localhost:8002/api"


class TestInstrumentsList:
    def test_returns_94_plus_tickers(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments?per_page=100")
        assert r.status_code == 200
        assert r.json()["total"] >= 94

    def test_pagination(self) -> None:
        p1 = httpx.get(f"{BASE}/market/instruments?page=1&per_page=10").json()["data"]
        p2 = httpx.get(f"{BASE}/market/instruments?page=2&per_page=10").json()["data"]
        tickers_1 = [x["ticker"] for x in p1]
        tickers_2 = [x["ticker"] for x in p2]
        assert tickers_1 != tickers_2, "Page 1 and Page 2 should have different tickers"

    def test_filter_by_sector(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments?sector=Technology")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data) > 0, "Should have Technology stocks"
        for item in data:
            assert item["sector"] == "Technology"

    def test_search(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments?search=Apple")
        assert r.status_code == 200
        tickers = [x["ticker"] for x in r.json()["data"]]
        assert "AAPL" in tickers

    def test_sort_by_market_cap_desc(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments?sort_by=market_cap&order=desc&per_page=5")
        assert r.status_code == 200
        caps = [x["market_cap"] for x in r.json()["data"] if x.get("market_cap")]
        assert caps == sorted(caps, reverse=True), "Should be sorted by market_cap descending"

    def test_per_page_limit(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments?per_page=200")
        assert r.status_code == 422, "per_page > 100 should be rejected"


class TestTickerDetail:
    def test_aapl_full_card(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/AAPL")
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "AAPL"
        # Fields from InstrumentDetailResponse schema
        for field in ["name", "sector", "market_cap", "industry", "exchange",
                      "description", "website", "employees"]:
            assert field in data, f"Field {field} missing"

    def test_not_found(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/XXXINVALID999")
        assert r.status_code == 404

    def test_ticker_lowercase_handled(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/aapl")
        assert r.status_code == 200
        assert r.json()["ticker"] == "AAPL"


class TestHistory:
    def test_default_history(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/AAPL/history")
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 100, f"Expected >100 days, got {len(data)}"
        item = data[0]
        for field in ["date", "open", "high", "low", "close", "volume"]:
            assert field in item, f"Field {field} missing in price point"

    def test_ohlc_integrity(self) -> None:
        data = httpx.get(f"{BASE}/market/instruments/AAPL/history?period=1m").json()
        assert len(data) > 0
        for item in data:
            assert item["low"] <= item["close"] <= item["high"], \
                f"OHLCV integrity violated: low={item['low']}, close={item['close']}, high={item['high']}"
            assert item["low"] <= item["open"] <= item["high"], \
                f"OHLCV integrity violated: low={item['low']}, open={item['open']}, high={item['high']}"

    def test_period_filter(self) -> None:
        data_1m = httpx.get(f"{BASE}/market/instruments/AAPL/history?period=1m").json()
        data_1y = httpx.get(f"{BASE}/market/instruments/AAPL/history?period=1y").json()
        assert len(data_1m) < len(data_1y), \
            f"1m ({len(data_1m)} pts) should have fewer points than 1y ({len(data_1y)} pts)"

    def test_invalid_period(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/AAPL/history?period=99d")
        assert r.status_code == 422

    def test_nonexistent_ticker(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/ZZZZZZ/history")
        assert r.status_code == 404


class TestCurrentPrice:
    def test_aapl_price(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/AAPL/price")
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "AAPL"
        assert data["price"] > 0, "Price should be positive"
        assert "change" in data
        assert "change_pct" in data

    def test_nonexistent_ticker(self) -> None:
        r = httpx.get(f"{BASE}/market/instruments/ZZZZZZ/price")
        assert r.status_code == 404


class TestRedisCache:
    def test_cache_speedup(self) -> None:
        rc = redis.Redis(host="localhost", port=6379)
        # Clear detail cache for MSFT
        for key in rc.keys("mkt:detail:MSFT*"):
            rc.delete(key)

        t1 = time.time()
        httpx.get(f"{BASE}/market/instruments/MSFT")
        first = time.time() - t1

        t2 = time.time()
        httpx.get(f"{BASE}/market/instruments/MSFT")
        second = time.time() - t2

        print(f"\n  First: {first:.3f}s, Second (cache): {second:.3f}s")
        assert second < first or second < 0.05, "Cache should speed up second request"


class TestEarnings:
    def test_upcoming_returns_list(self) -> None:
        r = httpx.get(f"{BASE}/earnings/upcoming?days=90")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # May be empty if no earnings seeded — that's OK
        if r.json():
            item = r.json()[0]
            for field in ["ticker", "name", "report_date"]:
                assert field in item, f"Field {field} missing in earnings"

    def test_invalid_days(self) -> None:
        r = httpx.get(f"{BASE}/earnings/upcoming?days=999")
        assert r.status_code == 422, "days > 90 should be rejected"


class TestInsider:
    def test_insider_returns_list(self) -> None:
        r = httpx.get(f"{BASE}/insider/AAPL")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # May be empty if no insider data seeded — that's OK
        if r.json():
            item = r.json()[0]
            for field in ["insider_name", "transaction_type", "shares", "filing_date"]:
                assert field in item, f"Field {field} missing in insider"

    def test_insider_nonexistent_ticker(self) -> None:
        """Insider endpoint doesn't check instrument existence — returns empty list."""
        r = httpx.get(f"{BASE}/insider/ZZZZZZ")
        assert r.status_code == 200
        assert r.json() == []
