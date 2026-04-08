"""
Unit tests — pure business logic, no DB/Redis/network required.
Tests functions that can be called without infrastructure.
"""

import hashlib
import time

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Auth: password hashing, email normalization, token hashing
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthLogic:
    def test_email_normalization(self) -> None:
        from auth_service_logic import normalize_email
        assert normalize_email("User@Example.COM") == "user@example.com"
        assert normalize_email("  ALICE@test.com  ") == "alice@test.com"
        assert normalize_email("bob@test.com") == "bob@test.com"

    def test_refresh_token_hash(self) -> None:
        from auth_service_logic import hash_refresh_token
        token = "abc123"
        h = hash_refresh_token(token)
        assert h == hashlib.sha256(token.encode()).hexdigest()
        assert len(h) == 64
        assert hash_refresh_token(token) == h  # deterministic

    def test_refresh_token_uniqueness(self) -> None:
        from auth_service_logic import create_refresh_token
        t1 = create_refresh_token()
        t2 = create_refresh_token()
        assert t1 != t2
        assert len(t1) == 64  # secrets.token_hex(32)


# ═══════════════════════════════════════════════════════════════════════════════
# Market: LIKE escaping, period mapping
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketLogic:
    def test_like_escape(self) -> None:
        from market_logic import escape_like
        assert escape_like("apple") == "apple"
        assert escape_like("100%") == "100\\%"
        assert escape_like("a_b") == "a\\_b"
        assert escape_like("a\\b") == "a\\\\b"
        assert escape_like("%_%") == "\\%\\_\\%"

    def test_period_to_days(self) -> None:
        from market_logic import period_to_days
        assert period_to_days("1m") == 30
        assert period_to_days("1y") == 365
        assert period_to_days("5y") == 1825
        assert period_to_days("max") == 9999
        assert period_to_days("invalid") == 365  # default


# ═══════════════════════════════════════════════════════════════════════════════
# Portfolio: weighted average, CSV sanitization, sell clamping
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioLogic:
    def test_weighted_average(self) -> None:
        from portfolio_logic import weighted_avg
        # 10 shares @ $100, then 10 @ $120 = avg $110
        assert weighted_avg(10, 100, 10, 120) == 110.0
        # 10 @ $100, then 5 @ $200 = (1000 + 1000) / 15 = $133.33
        assert round(weighted_avg(10, 100, 5, 200), 2) == 133.33

    def test_csv_sanitize(self) -> None:
        from portfolio_logic import sanitize_csv
        assert sanitize_csv("normal text") == "normal text"
        assert sanitize_csv("=CMD()") == "'=CMD()"
        assert sanitize_csv("+1+1") == "'+1+1"
        assert sanitize_csv("-formula") == "'-formula"
        assert sanitize_csv("@SUM") == "'@SUM"
        assert sanitize_csv("") == ""
        assert sanitize_csv("\tcmd") == "'\tcmd"

    def test_sell_clamp(self) -> None:
        from portfolio_logic import clamp_sell
        assert clamp_sell(held=15, requested=9999) == 15
        assert clamp_sell(held=15, requested=5) == 5
        assert clamp_sell(held=15, requested=None) == 15
        assert clamp_sell(held=15, requested=15) == 15


# ═══════════════════════════════════════════════════════════════════════════════
# Forecast: signal logic, confidence determination
# ═══════════════════════════════════════════════════════════════════════════════

class TestForecastLogic:
    def test_signal_buy(self) -> None:
        from forecast_logic import determine_signal
        assert determine_signal(median_1d=110, current_close=100) == "BUY"

    def test_signal_sell(self) -> None:
        from forecast_logic import determine_signal
        assert determine_signal(median_1d=90, current_close=100) == "SELL"

    def test_signal_hold(self) -> None:
        from forecast_logic import determine_signal
        assert determine_signal(median_1d=100.3, current_close=100) == "HOLD"

    def test_confidence_high_buy(self) -> None:
        from forecast_logic import determine_confidence
        # Entire 80% CI above current price
        assert determine_confidence(lower_80=101, upper_80=110, median=105, current=100) == "HIGH"

    def test_confidence_high_sell(self) -> None:
        from forecast_logic import determine_confidence
        # Entire 80% CI below current price
        assert determine_confidence(lower_80=85, upper_80=95, median=90, current=100) == "HIGH"

    def test_confidence_medium(self) -> None:
        from forecast_logic import determine_confidence
        assert determine_confidence(lower_80=95, upper_80=110, median=105, current=100) == "MEDIUM"


# ═══════════════════════════════════════════════════════════════════════════════
# News: ticker matching
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsLogic:
    def test_html_strip(self) -> None:
        from news_logic import strip_html
        assert strip_html("<p>Hello</p>") == "Hello"
        assert strip_html("<a href='x'>Link</a> text") == "Link text"
        assert strip_html("No tags") == "No tags"
        assert strip_html("&amp; &lt;") == "& <"

    def test_ambiguous_tickers(self) -> None:
        from news_logic import AMBIGUOUS_TICKERS
        assert "GE" in AMBIGUOUS_TICKERS
        assert "LOW" in AMBIGUOUS_TICKERS
        assert "AAPL" not in AMBIGUOUS_TICKERS


# ═══════════════════════════════════════════════════════════════════════════════
# Rate limiting: tier limits consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestTierLimits:
    def test_all_tiers_defined(self) -> None:
        from tier_logic import ALL_LIMITS
        for name, limits in ALL_LIMITS.items():
            assert "free" in limits, f"{name} missing free tier"
            assert "pro" in limits, f"{name} missing pro tier"
            assert "premium" in limits, f"{name} missing premium tier"

    def test_pro_greater_than_free(self) -> None:
        from tier_logic import ALL_LIMITS
        for name, limits in ALL_LIMITS.items():
            assert limits["pro"] >= limits["free"], f"{name}: pro < free"

    def test_premium_greater_than_pro(self) -> None:
        from tier_logic import ALL_LIMITS
        for name, limits in ALL_LIMITS.items():
            assert limits["premium"] >= limits["pro"], f"{name}: premium < pro"


# ═══════════════════════════════════════════════════════════════════════════════
# yfinance: circuit breaker logic
# ═══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_opens_after_threshold(self) -> None:
        from circuit_logic import CircuitBreaker
        cb = CircuitBreaker(threshold=3, cooldown=1)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_resets_on_success(self) -> None:
        from circuit_logic import CircuitBreaker
        cb = CircuitBreaker(threshold=3, cooldown=1)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failures == 0

    def test_cooldown(self) -> None:
        from circuit_logic import CircuitBreaker
        cb = CircuitBreaker(threshold=2, cooldown=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open
        time.sleep(0.15)
        assert not cb.is_open  # cooldown passed
