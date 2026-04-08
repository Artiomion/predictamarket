from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.earnings import EarningsCalendar, EarningsResult
from shared.models.market import Instrument

logger = structlog.get_logger()


async def get_upcoming_earnings(
    session: AsyncSession,
    days: int = 14,
) -> list[dict]:
    today = date.today()
    end_date = today + timedelta(days=days)

    query = (
        select(EarningsCalendar, Instrument.name)
        .join(Instrument, EarningsCalendar.instrument_id == Instrument.id)
        .where(
            EarningsCalendar.report_date >= today,
            EarningsCalendar.report_date <= end_date,
        )
        .order_by(EarningsCalendar.report_date.asc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        {
            "ticker": ec.ticker,
            "name": name,
            "report_date": ec.report_date,
            "fiscal_quarter": ec.fiscal_quarter,
            "fiscal_year": ec.fiscal_year,
            "time_of_day": ec.time_of_day,
            "eps_estimate": ec.eps_estimate,
            "revenue_estimate": ec.revenue_estimate,
        }
        for ec, name in rows
    ]


async def get_earnings_history(
    session: AsyncSession,
    ticker: str,
) -> list[EarningsResult]:
    ticker_upper = ticker.upper()

    query = (
        select(EarningsResult)
        .where(EarningsResult.ticker == ticker_upper)
        .order_by(EarningsResult.report_date.desc())
        .limit(20)
    )

    result = await session.execute(query)
    return list(result.scalars().all())
