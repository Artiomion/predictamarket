"""
Integration tests for forecast-service.
Requires: forecast-service running on localhost:8004 with TFT model loaded.
NOTE: POST /forecast/{ticker} triggers real ML inference (~5-15s per ticker).
      Tests use PRO tier to avoid rate limiting.
"""

import time

import httpx
import psycopg2
import pytest

BASE = "http://localhost:8004/api/forecast"
TIMEOUT = 60  # TFT inference can take time

# Valid tickers from our 94 S&P 500 set
VALID = ["AAPL", "MSFT", "NVDA", "CVX", "LLY"]

# Use unique UUIDs per test to avoid rate limit collisions
import uuid as _uuid

def _headers(prefix: str, tier: str = "pro") -> dict:
    return {"X-User-Id": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"{prefix}-{int(time.time())}")), "X-User-Tier": tier}


class TestForecastStructure:
    def test_response_shape(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[0]}", headers=_headers("struct1"), timeout=TIMEOUT)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        d = r.json()
        for f in ["ticker", "current_close", "signal", "confidence", "forecast",
                   "full_curve", "variable_importance", "inference_time_s"]:
            assert f in d, f"Field {f} missing"

    def test_signal_values(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[1]}", headers=_headers("struct2"), timeout=TIMEOUT)
        d = r.json()
        assert d["signal"] in ["BUY", "SELL", "HOLD"]
        assert d["confidence"] in ["HIGH", "MEDIUM", "LOW"]

    def test_horizons_present(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[2]}", headers=_headers("struct3"), timeout=TIMEOUT)
        forecast = r.json()["forecast"]
        for h in ["1d", "1w", "1m"]:
            assert h in forecast, f"Horizon {h} missing"

    def test_ci_logic(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[3]}", headers=_headers("struct4"), timeout=TIMEOUT)
        for h, vals in r.json()["forecast"].items():
            if vals is None:
                continue
            assert vals["lower_95"] <= vals["lower_80"], f"CI violation in {h}: l95 > l80"
            assert vals["lower_80"] <= vals["median"], f"CI violation in {h}: l80 > median"
            assert vals["median"] <= vals["upper_80"], f"CI violation in {h}: median > u80"
            assert vals["upper_80"] <= vals["upper_95"], f"CI violation in {h}: u80 > u95"

    def test_full_curve_length(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[4]}", headers=_headers("struct5"), timeout=TIMEOUT)
        assert len(r.json()["full_curve"]) == 22, "full_curve should have 22 values"

    def test_variable_importance(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[0]}", headers=_headers("struct6"), timeout=TIMEOUT)
        factors = r.json()["variable_importance"]["top_factors"]
        assert len(factors) >= 3, "Should have at least 3 factors"
        for f in factors:
            assert "name" in f and "weight" in f and "direction" in f
            assert f["direction"] in ["bullish", "bearish", "neutral"]

    def test_invalid_ticker_404(self) -> None:
        r = httpx.post(f"{BASE}/XXXX_INVALID", headers=_headers("struct7"), timeout=10)
        assert r.status_code == 404


class TestRateLimiting:
    def test_free_tier_one_per_day(self) -> None:
        h = _headers("free-rl", tier="free")
        r1 = httpx.post(f"{BASE}/{VALID[0]}", headers=h, timeout=TIMEOUT)
        assert r1.status_code == 200, "First free forecast should succeed"
        r2 = httpx.post(f"{BASE}/{VALID[1]}", headers=h, timeout=TIMEOUT)
        assert r2.status_code == 429, f"Second free forecast should be 429, got {r2.status_code}"

    def test_no_auth_returns_401(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[0]}", timeout=10)
        assert r.status_code == 401


class TestTopPicks:
    def test_returns_list(self) -> None:
        r = httpx.get(f"{BASE}/top-picks?limit=10")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_sorted_by_return(self) -> None:
        r = httpx.get(f"{BASE}/top-picks?limit=20", headers={"X-User-Tier": "pro"})
        picks = r.json()
        if len(picks) > 1:
            returns = [p["predicted_return_1m"] for p in picks if p.get("predicted_return_1m") is not None]
            assert returns == sorted(returns, reverse=True), "Not sorted by return"

    def test_free_tier_max_5(self) -> None:
        r = httpx.get(f"{BASE}/top-picks?limit=20", headers={"X-User-Tier": "free"})
        assert len(r.json()) <= 5, "Free tier should see max 5 picks"


class TestSignals:
    def test_filter_buy(self) -> None:
        r = httpx.get(f"{BASE}/signals?signal=BUY")
        assert r.status_code == 200
        for item in r.json():
            assert item["signal"] == "BUY"

    def test_filter_confidence(self) -> None:
        r = httpx.get(f"{BASE}/signals?confidence=HIGH")
        assert r.status_code == 200
        for item in r.json():
            assert item["confidence"] == "HIGH"


class TestGetForecast:
    def test_get_latest(self) -> None:
        """After POST, GET should return the stored forecast."""
        # POST first
        httpx.post(f"{BASE}/{VALID[0]}", headers=_headers("get1"), timeout=TIMEOUT)
        # GET
        r = httpx.get(f"{BASE}/{VALID[0]}")
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == VALID[0]
        assert "forecast" in d

    def test_history(self) -> None:
        r = httpx.get(f"{BASE}/{VALID[0]}/history?limit=5")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_nonexistent_ticker_404(self) -> None:
        r = httpx.get(f"{BASE}/ZZZNOTREAL")
        assert r.status_code == 404


class TestRealModel:
    def test_inference_time_realistic(self) -> None:
        r = httpx.post(f"{BASE}/{VALID[0]}", headers=_headers("real1"), timeout=TIMEOUT)
        assert r.json()["inference_time_s"] > 0.3, "Too fast — looks like a mock"

    def test_different_forecasts_for_different_tickers(self) -> None:
        medians = []
        for t in VALID[:3]:
            r = httpx.post(f"{BASE}/{t}", headers=_headers(f"real-{t}"), timeout=TIMEOUT)
            medians.append(r.json()["forecast"]["1d"]["median"])
        assert len(set(medians)) > 1, "All forecasts identical — model not working"

    def test_only_sp500_tickers(self) -> None:
        """AAME is in the training model but NOT in our 94 S&P 500 set."""
        r = httpx.post(f"{BASE}/AAME", headers=_headers("real3"), timeout=10)
        assert r.status_code == 404


class TestPersistence:
    def test_saved_to_db(self) -> None:
        ticker = VALID[0]
        httpx.post(f"{BASE}/{ticker}", headers=_headers("persist1"), timeout=TIMEOUT)

        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/predictamarket")
        cur = conn.cursor()
        cur.execute(
            "SELECT ticker, signal FROM forecast.forecasts WHERE ticker=%s ORDER BY created_at DESC LIMIT 1",
            (ticker,),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None, "Forecast not saved to DB"
        assert row[0] == ticker
        assert row[1] in ["BUY", "SELL", "HOLD"]
