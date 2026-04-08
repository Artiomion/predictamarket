"""Tier limits — mirrors shared/tier_limits.py for unit testing."""

ALL_LIMITS = {
    "gateway_rate": {"free": 60, "pro": 300, "premium": 1000},
    "forecast_daily": {"free": 1, "pro": 10, "premium": 999999},
    "top_picks": {"free": 5, "pro": 20, "premium": 20},
    "portfolios": {"free": 1, "pro": 5, "premium": 10},
    "positions": {"free": 10, "pro": 999999, "premium": 999999},
    "watchlists": {"free": 1, "pro": 5, "premium": 10},
    "watchlist_items": {"free": 10, "pro": 999999, "premium": 999999},
    "alerts": {"free": 3, "pro": 20, "premium": 999999},
}
