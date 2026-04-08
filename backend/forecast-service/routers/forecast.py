import json
import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_read_session, get_session
from shared.rate_limit import check_rate_limit
from shared.redis_client import redis_client
from shared.tier_limits import FORECAST_DAILY_LIMITS, TOP_PICKS_LIMITS

from schemas.forecast import (
    BatchJobResponse,
    BatchJobStatus,
    BatchRequest,
    ForecastFromDB,
    ForecastResponse,
    TopPickItem,
)
from services.forecast_service import (
    get_forecast_history,
    get_latest_forecast,
    get_signals,
    get_top_picks,
    store_forecast,
)
from services.forecast_service import VALID_TICKERS
from services.inference import run_inference
from services.model_loader import artifacts

logger = structlog.get_logger()
router = APIRouter()



async def _check_forecast_rate_limit(user_id: str, tier: str) -> None:
    limit = FORECAST_DAILY_LIMITS.get(tier, 1)
    key = f"fc:daily:{user_id}"
    count, remaining, ttl = await check_rate_limit(key, limit, window_seconds=86400)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily forecast limit reached ({limit}/day for {tier} tier). Upgrade for more.",
        )


# ── Fixed-path routes MUST come before /{ticker} to avoid path conflicts ──────

@router.get("/top-picks", response_model=list[TopPickItem])
async def top_picks(
    limit: int = Query(20, ge=1, le=50),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_read_session),
) -> list[dict]:
    """Top picks by predicted return. Free→5, Pro/Premium→20."""
    max_limit = TOP_PICKS_LIMITS.get(x_user_tier, 5)
    return await get_top_picks(session, limit=min(limit, max_limit))


@router.get("/signals", response_model=list[ForecastFromDB])
async def signals(
    signal: str | None = Query(None, pattern="^(BUY|SELL|HOLD)$"),
    confidence: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
    session: AsyncSession = Depends(get_read_session),
) -> list[ForecastFromDB]:
    rows = await get_signals(session, signal=signal, confidence=confidence)
    return [ForecastFromDB.model_validate(r) for r in rows]


@router.post("/batch", response_model=BatchJobResponse)
async def create_batch_forecast(
    body: BatchRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
) -> BatchJobResponse:
    """Queue batch forecast job. Pro/Premium only."""
    if x_user_tier not in ("pro", "premium"):
        raise HTTPException(status_code=403, detail="Batch forecasting requires Pro or Premium tier")
    job_id = uuid.uuid4().hex[:12]
    await redis_client.set(
        f"fc:batch:{job_id}",
        json.dumps({"status": "queued", "tickers": body.tickers, "completed": 0, "total": len(body.tickers)}),
        ex=3600,
    )
    return BatchJobResponse(job_id=job_id, status="queued", tickers=body.tickers)


@router.get("/batch/{job_id}", response_model=BatchJobStatus)
async def get_batch_status(job_id: str) -> BatchJobStatus:
    raw = await redis_client.get(f"fc:batch:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Batch job not found")
    data = json.loads(raw)
    return BatchJobStatus(job_id=job_id, status=data["status"], completed=data["completed"], total=data["total"])


# ── Ticker-specific routes ────────────────────────────────────────────────────

@router.post("/{ticker}", response_model=ForecastResponse)
async def create_forecast(
    ticker: str,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run live TFT inference for a ticker. Rate limited by tier."""
    ticker_upper = ticker.upper()

    if VALID_TICKERS and ticker_upper not in VALID_TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not in supported S&P 500 set")

    await _check_forecast_rate_limit(str(user_id), x_user_tier)

    result = await run_inference(ticker_upper, artifacts)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    try:
        await store_forecast(session, result)
    except Exception as exc:
        await logger.aerror("store_forecast_error", ticker=ticker_upper, error=str(exc))

    return result


@router.get("/{ticker}", response_model=ForecastResponse)
async def get_forecast(
    ticker: str,
    session: AsyncSession = Depends(get_read_session),
) -> dict:
    """Get latest forecast from DB."""
    data = await get_latest_forecast(session, ticker)
    if not data:
        raise HTTPException(status_code=404, detail=f"No forecast found for {ticker.upper()}")
    return data


@router.get("/{ticker}/history", response_model=list[ForecastFromDB])
async def forecast_history(
    ticker: str,
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_read_session),
) -> list[ForecastFromDB]:
    rows = await get_forecast_history(session, ticker, limit=limit)
    return [ForecastFromDB.model_validate(r) for r in rows]
