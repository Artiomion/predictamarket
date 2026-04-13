"""Centralized tier limits — single source of truth for all services."""

from shared.utils import UNLIMITED

# API Gateway rate limiting (requests per minute)
GATEWAY_RATE_LIMITS = {"free": 500, "pro": 1500, "premium": 5000}

# Forecast daily limits
FORECAST_DAILY_LIMITS = {"free": 1, "pro": 10, "premium": UNLIMITED}

# Top picks visible
TOP_PICKS_LIMITS = {"free": 5, "pro": 20, "premium": 20}

# Portfolio limits
PORTFOLIO_LIMITS = {"free": 1, "pro": 5, "premium": 10}
POSITION_LIMITS = {"free": 10, "pro": UNLIMITED, "premium": UNLIMITED}

# Watchlist limits
WATCHLIST_LIMITS = {"free": 1, "pro": 5, "premium": 10}
WATCHLIST_ITEM_LIMITS = {"free": 10, "pro": UNLIMITED, "premium": UNLIMITED}

# Alert limits
ALERT_LIMITS = {"free": 3, "pro": 20, "premium": UNLIMITED}
