"""Fetch current prices from Redis cache or market-data-service fallback."""

import json
import httpx
import structlog

from shared.redis_client import redis_client
from shared.config import settings

logger = structlog.get_logger()


async def get_current_price(ticker: str) -> float | None:
    """Get current price for a ticker. Returns None if unavailable."""
    ticker_upper = ticker.upper()

    # 1. Try Redis cache
    try:
        cached = await redis_client.get(f"mkt:price:{ticker_upper}")
        if cached:
            data = json.loads(cached)
            price = data.get("price")
            if price is not None:
                return float(price)
    except Exception:
        pass

    # 2. Fallback: call market-data-service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.MARKET_SERVICE_URL}/api/market/instruments/{ticker_upper}/price"
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("price", 0))
    except Exception as e:
        await logger.awarning("price_fetch_failed", ticker=ticker_upper, error=str(e))

    return None


async def enrich_positions_with_prices(positions: list) -> list:
    """Set current_price, pnl, pnl_pct on each position from live price data."""
    for pos in positions:
        price = await get_current_price(pos.ticker)
        if price is not None:
            pos.current_price = price
            pos.pnl = round((price - pos.avg_buy_price) * pos.quantity, 2)
            pos.pnl_pct = round(
                (price - pos.avg_buy_price) / pos.avg_buy_price * 100, 2
            ) if pos.avg_buy_price else 0
    return positions
