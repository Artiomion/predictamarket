"""Evaluate past forecasts against actual prices → populate forecast_history."""

from datetime import date, datetime, timedelta, timezone

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.models.forecast import Forecast, ForecastPoint, ForecastHistory
from shared.models.market import PriceHistory

logger = structlog.get_logger()

# Map horizon labels to trading days offset
EVAL_HORIZONS = {
    "1d": 1,
    "3d": 3,
    "1w": 5,
    "2w": 10,
    "1m": 22,
}


async def evaluate_forecasts(days_back: int = 30) -> dict:
    """Evaluate forecasts from the last N days against actual prices.

    Batch-fetches prices to avoid N+1 queries. Uses (ticker, forecast_date, horizon_days)
    as natural key for idempotent upserts.
    """
    evaluated = 0
    skipped = 0

    async with async_session_factory() as session:
        cutoff = date.today() - timedelta(days=days_back)

        # 1. Get all forecasts with their points in the evaluation window
        result = await session.execute(
            select(Forecast, ForecastPoint)
            .join(ForecastPoint, ForecastPoint.forecast_id == Forecast.id)
            .where(Forecast.forecast_date >= cutoff)
            .where(ForecastPoint.horizon_label.in_(list(EVAL_HORIZONS.keys())))
            .order_by(Forecast.forecast_date.desc())
        )
        all_rows = result.all()

        if not all_rows:
            return {"evaluated": 0, "skipped": 0}

        # Deduplicate: keep only the newest forecast per (ticker, date, horizon)
        seen_forecast_keys: set[tuple[str, date, str]] = set()
        forecast_rows = []
        for forecast, point in all_rows:
            key = (forecast.ticker, forecast.forecast_date, point.horizon_label)
            if key in seen_forecast_keys:
                continue
            seen_forecast_keys.add(key)
            forecast_rows.append((forecast, point))

        # 2. Collect all (ticker, date_range) pairs needed for price lookup
        tickers = set()
        min_date = date.today()
        max_date = cutoff
        for forecast, point in forecast_rows:
            tickers.add(forecast.ticker)
            if forecast.forecast_date < min_date:
                min_date = forecast.forecast_date
            horizon_days = EVAL_HORIZONS.get(point.horizon_label, 1)
            target = forecast.forecast_date + timedelta(days=int(horizon_days * 1.5) + 2)
            if target > max_date:
                max_date = target

        # 3. Batch-fetch all relevant prices in one query
        price_result = await session.execute(
            select(PriceHistory.ticker, PriceHistory.date, PriceHistory.close)
            .where(
                and_(
                    PriceHistory.ticker.in_(list(tickers)),
                    PriceHistory.date >= min_date,
                    PriceHistory.date <= max_date,
                )
            )
        )
        # Build lookup: {(ticker, date): close}
        price_map: dict[tuple[str, date], float] = {}
        for row in price_result.all():
            price_map[(row.ticker, row.date)] = float(row.close)

        # 4. Check which (ticker, forecast_date, horizon_days) already evaluated
        existing_result = await session.execute(
            select(
                ForecastHistory.ticker,
                ForecastHistory.forecast_date,
                ForecastHistory.horizon_days,
            )
            .where(ForecastHistory.forecast_date >= cutoff)
            .where(ForecastHistory.actual_price.isnot(None))
        )
        existing_keys = set(
            (r.ticker, r.forecast_date, r.horizon_days)
            for r in existing_result.all()
        )

        # 5. Evaluate each forecast point
        inserts = []
        for forecast, point in forecast_rows:
            horizon_days = EVAL_HORIZONS.get(point.horizon_label)
            if not horizon_days:
                continue

            # Skip already evaluated
            key = (forecast.ticker, forecast.forecast_date, horizon_days)
            if key in existing_keys:
                skipped += 1
                continue

            # Find actual price: look for closest date in range
            actual_price = None
            for offset in range(horizon_days, int(horizon_days * 1.5) + 3):
                target_date = forecast.forecast_date + timedelta(days=offset)
                price = price_map.get((forecast.ticker, target_date))
                if price is not None:
                    actual_price = price
                    break

            if actual_price is None:
                skipped += 1
                continue

            predicted_price = float(point.median)
            error_pct = round((predicted_price - actual_price) / actual_price * 100, 2) if actual_price != 0 else 0.0

            # Direction: did price move in the direction the signal predicted?
            was_correct = None
            if forecast.signal and forecast.current_close:
                if forecast.signal == "BUY":
                    was_correct = actual_price > forecast.current_close
                elif forecast.signal == "SELL":
                    was_correct = actual_price < forecast.current_close

            inserts.append({
                "instrument_id": forecast.instrument_id,
                "ticker": forecast.ticker,
                "forecast_date": forecast.forecast_date,
                "horizon_days": horizon_days,
                "predicted_price": predicted_price,
                "actual_price": actual_price,
                "error_pct": error_pct,
                "signal": forecast.signal,
                "was_correct": was_correct,
                "evaluated_at": datetime.now(timezone.utc),
            })
            evaluated += 1

        # 6. Bulk insert
        if inserts:
            await session.execute(pg_insert(ForecastHistory), inserts)
            await session.commit()

    await logger.ainfo("evaluation_complete", evaluated=evaluated, skipped=skipped)
    return {"evaluated": evaluated, "skipped": skipped}


async def get_accuracy(
    session: AsyncSession,
    ticker: str,
    horizon: str = "1d",
    days: int = 30,
) -> dict:
    """Get accuracy metrics for a ticker at a given horizon."""
    horizon_days = EVAL_HORIZONS.get(horizon, 1)
    cutoff = date.today() - timedelta(days=days)

    result = await session.execute(
        select(ForecastHistory)
        .where(
            and_(
                ForecastHistory.ticker == ticker.upper(),
                ForecastHistory.horizon_days == horizon_days,
                ForecastHistory.forecast_date >= cutoff,
                ForecastHistory.actual_price.isnot(None),
            )
        )
        .order_by(ForecastHistory.forecast_date.desc())
    )
    rows = list(result.scalars().all())

    if not rows:
        return {
            "ticker": ticker.upper(),
            "horizon": horizon,
            "period_days": days,
            "total_forecasts": 0,
            "direction_accuracy": None,
            "mape": None,
            "win_rate": None,
            "predictions": [],
        }

    total = len(rows)
    signals_with_result = [r for r in rows if r.was_correct is not None]
    correct_direction = sum(1 for r in signals_with_result if r.was_correct is True)
    mape = round(sum(abs(r.error_pct or 0) for r in rows) / total, 2)

    predictions = [
        {
            "date": r.forecast_date.isoformat(),
            "predicted": round(r.predicted_price, 2),
            "actual": round(r.actual_price, 2) if r.actual_price else None,
            "error_pct": r.error_pct,
            "signal": r.signal,
            "was_correct": r.was_correct,
        }
        for r in rows
    ]

    direction_pct = round(correct_direction / len(signals_with_result) * 100, 1) if signals_with_result else None
    # Win rate = % of BUY signals where price went up + SELL signals where price went down
    buy_signals = [r for r in signals_with_result if r.signal == "BUY"]
    sell_signals = [r for r in signals_with_result if r.signal == "SELL"]
    buy_wins = sum(1 for r in buy_signals if r.was_correct)
    sell_wins = sum(1 for r in sell_signals if r.was_correct)
    total_signals = len(buy_signals) + len(sell_signals)
    win_rate = round((buy_wins + sell_wins) / total_signals * 100, 1) if total_signals else None

    return {
        "ticker": ticker.upper(),
        "horizon": horizon,
        "period_days": days,
        "total_forecasts": total,
        "direction_accuracy": direction_pct,
        "mape": mape,
        "win_rate": win_rate,
        "predictions": predictions,
    }
