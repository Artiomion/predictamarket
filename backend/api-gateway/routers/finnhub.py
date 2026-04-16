"""Finnhub proxy — serves quote data and WS token without exposing API key."""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query

from shared.config import settings

logger = structlog.get_logger()
router = APIRouter()

FINNHUB_BASE = "https://finnhub.io/api/v1"


@router.get("/quote")
async def get_quote(symbol: str) -> dict:
    """Get real-time quote from Finnhub."""
    if not settings.FINNHUB_API_KEY:
        raise HTTPException(status_code=503, detail="Finnhub not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{FINNHUB_BASE}/quote",
            params={"symbol": symbol.upper(), "token": settings.FINNHUB_API_KEY},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Finnhub API error")

    data = resp.json()
    return {
        "symbol": symbol.upper(),
        "price": data.get("c"),
        "change": data.get("d"),
        "change_pct": data.get("dp"),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "prev_close": data.get("pc"),
    }


@router.get("/ws-token")
async def get_ws_token() -> dict:
    """Return Finnhub API key for WebSocket connection."""
    if not settings.FINNHUB_API_KEY:
        raise HTTPException(status_code=503, detail="Finnhub not configured")
    return {"token": settings.FINNHUB_API_KEY}
