"""Centralized tier limits — single source of truth for all services."""

# API Gateway rate limiting (requests per minute)
GATEWAY_RATE_LIMITS = {"free": 60, "pro": 300, "premium": 1000}

# Forecast daily limits
FORECAST_DAILY_LIMITS = {"free": 1, "pro": 10, "premium": 999999}

# Top picks visible
TOP_PICKS_LIMITS = {"free": 5, "pro": 20, "premium": 20}

# Portfolio limits
PORTFOLIO_LIMITS = {"free": 1, "pro": 5, "premium": 10}
POSITION_LIMITS = {"free": 10, "pro": 999999, "premium": 999999}

# Watchlist limits
WATCHLIST_LIMITS = {"free": 1, "pro": 5, "premium": 10}
WATCHLIST_ITEM_LIMITS = {"free": 10, "pro": 999999, "premium": 999999}

# Alert limits
ALERT_LIMITS = {"free": 3, "pro": 20, "premium": 999999}
