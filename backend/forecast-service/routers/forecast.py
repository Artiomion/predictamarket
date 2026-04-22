import json
import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.auth import require_user_id
from shared.database import get_read_session, get_session
from shared.rate_limit import check_rate_limit
from shared.redis_client import redis_client
from shared.tier_limits import FORECAST_DAILY_LIMITS, TOP_PICKS_LIMITS
from shared.utils import sanitize_nan

from schemas.forecast import (
    AlphaSignalResponse,
    BatchJobResponse,
    BatchJobStatus,
    BatchRequest,
    ForecastFromDB,
    ForecastResponse,
    TopPickItem,
)
from shared.models.forecast import AlphaSignal
from services.forecast_service import (
    get_forecast_history,
    get_latest_forecast,
    get_signals,
    get_top_picks,
    store_forecast,
)
from services.forecast_service import VALID_TICKERS
from shared.models.forecast import Forecast
from services.ensemble import run_ensemble
from services.inference import run_inference
from services.model_loader import artifacts

logger = structlog.get_logger()
router = APIRouter()

ONE_DAY_SECONDS = 86400
BATCH_JOB_TTL_SECONDS = 3600
BATCH_JOB_ID_LENGTH = 12
FINBERT_BATCH_SIZE = 16
FINBERT_MAX_LENGTH = 512


async def _check_forecast_rate_limit(user_id: str, tier: str) -> None:
    limit = FORECAST_DAILY_LIMITS.get(tier, 1)
    key = f"fc:daily:{user_id}"
    count, remaining, ttl = await check_rate_limit(key, limit, window_seconds=ONE_DAY_SECONDS)
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


ALPHA_SIGNALS_RATE_LIMIT = 60  # requests/minute per user
ALPHA_SIGNALS_RATE_WINDOW = 60  # seconds


@router.get("/alpha-signals", response_model=list[AlphaSignalResponse])
async def alpha_signals_feed(
    limit: int = Query(50, ge=1, le=200),
    confident_only: bool = Query(True),
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_read_session),
) -> list[AlphaSignalResponse]:
    """Alpha Signals feed — latest ensemble signals (Pro/Premium only).

    `confident_only=True` returns only rows where all 3 models agree (q_10 > close).
    These back-test (single test window) with Sharpe 8.15 + 63% win rate.
    """
    if x_user_tier not in {"pro", "premium"}:
        raise HTTPException(status_code=403, detail="Alpha Signals require Pro or Premium subscription")

    # Cheap DB read but we still cap abuse. 60/min = one poll per second.
    count, _remaining, ttl = await check_rate_limit(
        f"alpha:feed:{user_id}",
        limit=ALPHA_SIGNALS_RATE_LIMIT,
        window_seconds=ALPHA_SIGNALS_RATE_WINDOW,
    )
    if count > ALPHA_SIGNALS_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {ALPHA_SIGNALS_RATE_LIMIT} requests per {ALPHA_SIGNALS_RATE_WINDOW}s. Retry in {ttl}s.",
            headers={"Retry-After": str(ttl)},
        )

    # Select only the columns we serialize — skip ensemble_weights (array of 3
    # floats × 346 rows ≈ 12KB wasted per request) and bookkeeping columns
    # (id, instrument_id, created_at, updated_at, is_latest). Uses
    # idx_alpha_confident partial index when confident_only=True and
    # idx_alpha_return_1d for the ORDER BY.
    stmt = select(
        AlphaSignal.ticker,
        AlphaSignal.signal,
        AlphaSignal.confidence,
        AlphaSignal.confident_long,
        AlphaSignal.model_consensus,
        AlphaSignal.disagreement_score,
        AlphaSignal.current_close,
        AlphaSignal.median_1d,
        AlphaSignal.lower_80_1d,
        AlphaSignal.upper_80_1d,
        AlphaSignal.predicted_return_1d,
        AlphaSignal.predicted_return_1w,
        AlphaSignal.predicted_return_1m,
        AlphaSignal.forecast_date,
        AlphaSignal.expires_at,
    ).where(AlphaSignal.is_latest.is_(True))

    if confident_only:
        stmt = stmt.where(AlphaSignal.confident_long.is_(True))
    stmt = stmt.order_by(AlphaSignal.predicted_return_1d.desc().nullslast()).limit(limit)

    rows = (await session.execute(stmt)).all()
    return [AlphaSignalResponse.from_row(r) for r in rows]


@router.post("/batch", response_model=BatchJobResponse, status_code=201)
async def create_batch_forecast(
    body: BatchRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
) -> BatchJobResponse:
    """Queue batch forecast job. Pro/Premium only."""
    if x_user_tier not in ("pro", "premium"):
        raise HTTPException(status_code=403, detail="Batch forecasting requires Pro or Premium tier")
    job_id = uuid.uuid4().hex[:BATCH_JOB_ID_LENGTH]
    await redis_client.set(
        f"fc:batch:{job_id}",
        json.dumps({"status": "queued", "tickers": body.tickers, "completed": 0, "total": len(body.tickers)}),
        ex=BATCH_JOB_TTL_SECONDS,
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

@router.post("/{ticker}", response_model=ForecastResponse, status_code=201)
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

    result = sanitize_nan(result)

    try:
        await store_forecast(session, result)
        result["persisted"] = True
    except Exception as exc:
        await session.rollback()
        await logger.aerror("store_forecast_error", ticker=ticker_upper, error=str(exc))
        result["persisted"] = False

    return result


@router.post("/{ticker}/signals", status_code=201)
async def create_signal_forecast(
    ticker: str,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
) -> dict:
    """Run 3-model ensemble inference (ep2+ep4+ep5).

    Premium/Pro-only. Returns a signal-oriented payload with a disagreement score
    — NOT the primary forecast. Used by Alpha Signals feed on frontend.
    """
    if x_user_tier not in {"pro", "premium"}:
        raise HTTPException(status_code=403, detail="Alpha Signals require Pro or Premium subscription")

    ticker_upper = ticker.upper()
    if VALID_TICKERS and ticker_upper not in VALID_TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not supported")

    await _check_forecast_rate_limit(str(user_id), x_user_tier)

    # Same weights as dag_alpha_signals batch — ep2-heavy optimises WR for
    # this Pro-only Alpha Signals path. See docs/MODEL.md §6.
    result = await run_ensemble(ticker_upper, artifacts, weights=[0.5, 0.3, 0.2])
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return sanitize_nan(result)


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


@router.get("/{ticker}/rank")
async def get_ticker_rank(
    ticker: str,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_read_session),
) -> dict:
    """Return the ticker's position in the 346-ticker catalog, ranked by
    predicted return on each horizon.

    This is the metric the TFT is actually good at — *relative* ranking of
    stocks — as opposed to absolute price prediction (MAPE 12% at 1-month is
    too wide to anchor on). Rank 1 = strongest predicted performer.
    """
    from sqlalchemy import func

    from shared.models.forecast import Forecast

    ticker_upper = ticker.upper()

    # Distinguish 404s: ticker not in catalog vs no forecasts yet.
    if VALID_TICKERS and ticker_upper not in VALID_TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not in supported S&P 500 set")

    # Rate-limit this — cheap read but 3×sort on 346 rows × 1000 RPS still
    # DoS'able. Reuse the forecast endpoint daily quota (same tier table).
    await _check_forecast_rate_limit(str(user_id), x_user_tier)

    # Single SQL pass with 3 window functions — ~2ms on 346 rows vs the old
    # 3×Python-side sort approach which was O(3·N log N) per request.
    # NULLS LAST behaviour: Postgres RANK() already handles nulls; we push them
    # to the bottom via NULLS LAST so rank is monotonic & meaningful.
    ranked_subq = (
        select(
            Forecast.ticker,
            func.rank().over(
                order_by=Forecast.predicted_return_1d.desc().nullslast()
            ).label("r1d"),
            func.rank().over(
                order_by=Forecast.predicted_return_1w.desc().nullslast()
            ).label("r1w"),
            func.rank().over(
                order_by=Forecast.predicted_return_1m.desc().nullslast()
            ).label("r1m"),
            Forecast.predicted_return_1d,
            Forecast.predicted_return_1w,
            Forecast.predicted_return_1m,
        )
        .where(Forecast.is_latest.is_(True))
        .subquery()
    )

    total_stmt = select(func.count()).select_from(ranked_subq)
    total = (await session.execute(total_stmt)).scalar_one()
    if total == 0:
        raise HTTPException(status_code=404, detail="No forecasts available yet — wait for next batch run")

    row_stmt = select(
        ranked_subq.c.r1d, ranked_subq.c.r1w, ranked_subq.c.r1m,
        ranked_subq.c.predicted_return_1d,
        ranked_subq.c.predicted_return_1w,
        ranked_subq.c.predicted_return_1m,
    ).where(ranked_subq.c.ticker == ticker_upper)
    row = (await session.execute(row_stmt)).first()

    if row is None or row.r1m is None or row.predicted_return_1m is None:
        raise HTTPException(status_code=404, detail=f"No forecast ranking for {ticker_upper} — wait for next batch run")

    return {
        "ticker": ticker_upper,
        "total_tickers": total,
        "rank_1d": row.r1d if row.predicted_return_1d is not None else None,
        "rank_1w": row.r1w if row.predicted_return_1w is not None else None,
        "rank_1m": row.r1m,
        # Percentile from the top: rank 1 → 1.0 (top), rank 346 → 0.003
        "percentile_1m": round(1 - (row.r1m - 1) / max(total, 1), 3),
    }


@router.get("/{ticker}/accuracy")
async def forecast_accuracy(
    ticker: str,
    horizon: str = Query("1d", regex="^(1d|3d|1w|2w|1m)$"),
    days: int = Query(30, ge=7, le=365),
    session: AsyncSession = Depends(get_read_session),
) -> dict:
    """Get forecast accuracy metrics vs actual prices."""
    from services.evaluation import get_accuracy
    return await get_accuracy(session, ticker, horizon=horizon, days=days)


@router.get("/{ticker}/walk-forward")
async def walk_forward(
    ticker: str,
    limit: int = Query(7, ge=1, le=14),
    session: AsyncSession = Depends(get_read_session),
) -> list[dict]:
    """Get last N forecasts with full 22-step curves for walk-forward overlay.

    Deduplicates by forecast_date (keeps most recent per day).
    """
    result = await session.execute(
        select(Forecast)
        .where(Forecast.ticker == ticker.upper())
        .options(selectinload(Forecast.points))
        .order_by(Forecast.created_at.desc())
        .limit(limit * 3)  # fetch extra to allow dedup
    )
    forecasts = list(result.scalars().unique().all())

    # Deduplicate: keep only the newest forecast per date
    seen_dates: set[str] = set()
    out = []
    for f in forecasts:
        date_key = f.forecast_date.isoformat()
        if date_key in seen_dates:
            continue
        seen_dates.add(date_key)

        sorted_points = sorted(f.points, key=lambda p: p.step)
        full_curve = [float(p.median) for p in sorted_points]
        if not full_curve:
            continue
        out.append({
            "forecast_date": date_key,
            "current_close": float(f.current_close) if f.current_close else None,
            "signal": f.signal,
            "confidence": f.confidence,
            "full_curve": full_curve,
        })
        if len(out) >= limit:
            break

    return out


@router.get("/{ticker}/history", response_model=list[ForecastFromDB])
async def forecast_history(
    ticker: str,
    limit: int = Query(30, ge=1, le=100),
    session: AsyncSession = Depends(get_read_session),
) -> list[ForecastFromDB]:
    rows = await get_forecast_history(session, ticker, limit=limit)
    return [ForecastFromDB.model_validate(r) for r in rows]
