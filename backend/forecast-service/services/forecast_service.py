"""Forecast DB operations — store and retrieve forecasts."""

import uuid
from datetime import date
from pathlib import Path

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.forecast import Forecast, ForecastFactor, ForecastPoint, ModelVersion
from shared.models.market import Instrument
from shared.utils import HORIZON_LABELS

logger = structlog.get_logger()

# Load valid tickers from file at module level (works without model loaded)
_TICKERS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "models" / "old_model_sp500_tickers.txt"
_MODELS_DIR_ENV = None  # Set from env if needed

VALID_TICKERS: set[str] = set()
try:
    import os
    _tf = Path(os.environ.get("MODELS_DIR", str(_TICKERS_FILE.parent))) / "old_model_sp500_tickers.txt"
    VALID_TICKERS = {t.strip().upper() for t in _tf.read_text().strip().splitlines() if t.strip()}
except Exception as exc:
    logger.warning("valid_tickers_load_failed", error=str(exc), path=str(_TICKERS_FILE))


async def get_or_create_model_version(session: AsyncSession, checkpoint_name: str = "") -> uuid.UUID:
    result = await session.execute(
        select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
    )
    mv = result.scalar_one_or_none()
    if mv:
        return mv.id

    # Derive version from checkpoint filename (e.g. "tft-epoch=02-val_loss=3.6789.ckpt")
    version = checkpoint_name.replace(".ckpt", "") if checkpoint_name else "tft-unknown"
    mv = ModelVersion(
        version=version,
        checkpoint_path=f"models/{checkpoint_name}" if checkpoint_name else "unknown",
        is_active=True,
        # Metrics from the 3-model ensemble (ep2+ep4+ep5 equal-weight) study
        # on the post-Oct-2024 test window — see docs/ENSEMBLE_NOTES.md.
        # DirAcc is computed against prev_close (true direction of future close
        # relative to today), NOT against day-1-of-forecast curve.
        metrics={
            "mape_1d": 4.78,
            "mape_22d": 12.49,
            "diracc_1d": 0.488,   # coin flip at 1 day — don't market
            "diracc_22d": 0.680,  # strong edge at 1 month — 34σ above chance
            "top20_sharpe": 1.45,
            "top20_return_pct": 19.19,
            "conflong_sharpe": 8.15,
            "conflong_win_rate": 63.0,
            "conflong_n_trades": 27,
            "test_samples": 9200,
        },
    )
    session.add(mv)
    await session.flush()
    return mv.id


async def store_forecast(session: AsyncSession, result: dict) -> Forecast:
    """Store inference result into forecast tables."""
    ticker = result["ticker"]

    inst_result = await session.execute(
        select(Instrument.id).where(Instrument.ticker == ticker)
    )
    instrument_id = inst_result.scalar_one_or_none()
    if not instrument_id:
        raise ValueError(f"Instrument {ticker} not found in DB")

    # Get checkpoint name from model loader if available
    try:
        from services.model_loader import artifacts
        ckpt = artifacts.checkpoint_name
    except Exception:
        ckpt = ""
    model_version_id = await get_or_create_model_version(session, checkpoint_name=ckpt)

# Single UPDATE statement instead of SELECT+loop
    await session.execute(
        update(Forecast)
        .where(Forecast.ticker == ticker, Forecast.is_latest.is_(True))
        .values(is_latest=False)
    )

    forecast = Forecast(
        instrument_id=instrument_id,
        model_version_id=model_version_id,
        ticker=ticker,
        forecast_date=date.today(),
        current_close=result["current_close"],
        signal=result["signal"],
        confidence=result["confidence"],
        predicted_return_1d=result.get("predicted_return_1d"),
        predicted_return_1w=result.get("predicted_return_1w"),
        predicted_return_1m=result.get("predicted_return_1m"),
        inference_time_s=result["inference_time_s"],
        is_latest=True,
    )
    session.add(forecast)
    await session.flush()

# Bulk add forecast points
    full_curve = result.get("full_curve", [])
    forecast_data = result.get("forecast", {})
    points = []
    for step in range(len(full_curve)):
        label = HORIZON_LABELS.get(step)
        horizon = forecast_data.get(label) if label else None
        points.append(ForecastPoint(
            forecast_id=forecast.id,
            step=step,
            horizon_label=label,
            median=full_curve[step],
            lower_80=horizon["lower_80"] if horizon else None,
            upper_80=horizon["upper_80"] if horizon else None,
            lower_95=horizon.get("lower_95") if horizon else None,
            upper_95=horizon.get("upper_95") if horizon else None,
        ))
    session.add_all(points)

    top_factors = result.get("variable_importance", {}).get("top_factors", [])
    factors = [
        ForecastFactor(
            forecast_id=forecast.id,
            factor_name=f["name"],
            weight=f["weight"],
            direction=f["direction"],
            rank=i + 1,
        )
        for i, f in enumerate(top_factors)
    ]
    session.add_all(factors)

    await logger.ainfo("forecast_stored", ticker=ticker, signal=result["signal"], confidence=result["confidence"])
    return forecast


async def get_latest_forecast(session: AsyncSession, ticker: str) -> dict | None:
    """FIX #4: Single query with selectinload instead of 3 separate queries."""
    # We can't selectinload on Forecast→ForecastPoint because they're not in
    # the same ORM relationship on the Forecast model. Use 2 queries max.
    result = await session.execute(
        select(Forecast).where(
            Forecast.ticker == ticker.upper(),
            Forecast.is_latest.is_(True),
        ).limit(1)
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        return None

    # Batch-fetch points and factors in parallel-ish (2 queries, not N+1)
    points_result, factors_result = await session.execute(
        select(ForecastPoint).where(ForecastPoint.forecast_id == forecast.id)
        .order_by(ForecastPoint.step)
    ), await session.execute(
        select(ForecastFactor).where(ForecastFactor.forecast_id == forecast.id)
        .order_by(ForecastFactor.rank)
    )
    # Note: SQLAlchemy async doesn't support gather, but these are 2 cheap queries by PK index

    points = points_result.scalars().all()
    factors = factors_result.scalars().all()

    forecast_horizons: dict[str, dict] = {}
    full_curve: list[float] = []
    for p in points:
        full_curve.append(p.median)
        if p.horizon_label:
            forecast_horizons[p.horizon_label] = {
                "median": p.median,
                "lower_80": p.lower_80,
                "upper_80": p.upper_80,
                "lower_95": p.lower_95,
                "upper_95": p.upper_95,
            }

    return {
        "ticker": forecast.ticker,
        "current_close": forecast.current_close,
        "signal": forecast.signal,
        "confidence": forecast.confidence,
        "forecast": forecast_horizons,
        "full_curve": full_curve,
        "variable_importance": {
            "top_factors": [
                {"name": f.factor_name, "weight": f.weight, "direction": f.direction}
                for f in factors
            ]
        },
        "inference_time_s": forecast.inference_time_s,
        "forecast_date": str(forecast.forecast_date),
    }


async def get_forecast_history(session: AsyncSession, ticker: str, limit: int = 30) -> list[Forecast]:
    result = await session.execute(
        select(Forecast).where(Forecast.ticker == ticker.upper())
        .order_by(Forecast.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_top_picks(session: AsyncSession, limit: int = 20) -> list[dict]:
    # "Top Picks" must only show actionable, positive-expected-return BUYs.
    # Mixing -1.75% returns under the "1m Return" column looked broken even
    # though the sort was correct — users expect every row to be positive.
    result = await session.execute(
        select(Forecast, Instrument.name)
        .join(Instrument, Forecast.instrument_id == Instrument.id)
        .where(
            Forecast.is_latest.is_(True),
            Forecast.signal == "BUY",
            Forecast.predicted_return_1m.isnot(None),
            Forecast.predicted_return_1m > 0,
        )
        .order_by(Forecast.predicted_return_1m.desc())
        .limit(limit)
    )
    return [
        {
            "ticker": f.ticker,
            "name": name,
            "current_close": f.current_close,
            "predicted_return_1m": f.predicted_return_1m,
            "signal": f.signal,
            "confidence": f.confidence,
        }
        for f, name in result.all()
    ]


async def get_signals(
    session: AsyncSession,
    signal: str | None = None,
    confidence: str | None = None,
) -> list[Forecast]:
    query = select(Forecast).where(Forecast.is_latest.is_(True))
    if signal:
        query = query.where(Forecast.signal == signal.upper())
    if confidence:
        query = query.where(Forecast.confidence == confidence.upper())
    query = query.order_by(Forecast.predicted_return_1m.desc().nullslast())

    result = await session.execute(query)
    return list(result.scalars().all())
