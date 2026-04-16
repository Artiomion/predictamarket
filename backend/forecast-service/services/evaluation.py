"""Evaluate past forecasts against actual prices → populate forecast_history."""

import uuid
from datetime import date, datetime, timedelta, timezone

import structlog
from sqlalchemy import select, text, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.models.forecast import Forecast, ForecastPoint, ForecastHistory
from shared.models.market import PriceHistory
from shared.utils import HORIZON_STEPS

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

    For each forecast + horizon, check if actual price exists in price_history,
    compute error and correctness, upsert into forecast_history.
    """
    evaluated = 0
    skipped = 0

    async with async_session_factory() as session:
        cutoff = date.today() - timedelta(days=days_back)

        # Get all forecasts with their points in the evaluation window
        result = await session.execute(
            select(Forecast, ForecastPoint)
            .join(ForecastPoint, ForecastPoint.forecast_id == Forecast.id)
            .where(Forecast.forecast_date >= cutoff)
            .where(ForecastPoint.horizon_label.in_(list(EVAL_HORIZONS.keys())))
            .order_by(Forecast.forecast_date.desc())
        )
        rows = result.all()

        for forecast, point in rows:
            horizon_days = EVAL_HORIZONS.get(point.horizon_label)
            if not horizon_days:
                continue

            # Compute target date (trading days approximation using calendar days * 1.4)
            # More accurate: just look for the Nth available price after forecast_date
            target_date = forecast.forecast_date + timedelta(days=int(horizon_days * 1.4) + 1)

            # Find actual close price on or near target date
            price_result = await session.execute(
                select(PriceHistory.close, PriceHistory.date)
                .where(
                    and_(
                        PriceHistory.ticker == forecast.ticker,
                        PriceHistory.date >= forecast.forecast_date + timedelta(days=horizon_days),
                        PriceHistory.date <= target_date,
                    )
                )
                .order_by(PriceHistory.date.asc())
                .limit(1)
            )
            price_row = price_result.first()

            if not price_row:
                skipped += 1
                continue

            actual_price = float(price_row.close)
            predicted_price = float(point.median)
            error_pct = round((predicted_price - actual_price) / actual_price * 100, 2)

            # Was the signal correct?
            was_correct = None
            if forecast.signal and forecast.current_close:
                if forecast.signal == "BUY":
                    was_correct = actual_price > forecast.current_close
                elif forecast.signal == "SELL":
                    was_correct = actual_price < forecast.current_close

            # Upsert into forecast_history
            stmt = pg_insert(ForecastHistory).values(
                instrument_id=forecast.instrument_id,
                ticker=forecast.ticker,
                forecast_date=forecast.forecast_date,
                horizon_days=horizon_days,
                predicted_price=predicted_price,
                actual_price=actual_price,
                error_pct=error_pct,
                signal=forecast.signal,
                was_correct=was_correct,
                evaluated_at=datetime.now(timezone.utc),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "actual_price": actual_price,
                    "error_pct": error_pct,
                    "was_correct": was_correct,
                    "evaluated_at": datetime.now(timezone.utc),
                },
            )
            await session.execute(stmt)
            evaluated += 1

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
    correct_direction = sum(1 for r in rows if r.was_correct is True)
    correct_signal = sum(1 for r in rows if r.was_correct is True)
    mape = round(sum(abs(r.error_pct) for r in rows) / total, 2)

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

    return {
        "ticker": ticker.upper(),
        "horizon": horizon,
        "period_days": days,
        "total_forecasts": total,
        "direction_accuracy": round(correct_direction / total * 100, 1) if total else None,
        "mape": mape,
        "win_rate": round(correct_signal / total * 100, 1) if total else None,
        "predictions": predictions,
    }
