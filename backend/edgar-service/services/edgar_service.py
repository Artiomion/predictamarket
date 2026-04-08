"""EDGAR DB operations — query stored financial statements."""

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.edgar import BalanceSheet, CashFlow, Filing, IncomeStatement

logger = structlog.get_logger()


async def get_filings(
    session: AsyncSession,
    ticker: str,
    filing_type: str | None = None,
    limit: int = 20,
) -> list[Filing]:
    ticker_upper = ticker.upper()
    query = select(Filing).where(Filing.ticker == ticker_upper)
    if filing_type:
        query = query.where(Filing.filing_type == filing_type)
    query = query.order_by(Filing.filing_date.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_income_statements(
    session: AsyncSession,
    ticker: str,
    limit: int = 20,
) -> list[IncomeStatement]:
    ticker_upper = ticker.upper()
    result = await session.execute(
        select(IncomeStatement)
        .where(IncomeStatement.ticker == ticker_upper)
        .order_by(IncomeStatement.period_end.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_balance_sheets(
    session: AsyncSession,
    ticker: str,
    limit: int = 20,
) -> list[BalanceSheet]:
    ticker_upper = ticker.upper()
    result = await session.execute(
        select(BalanceSheet)
        .where(BalanceSheet.ticker == ticker_upper)
        .order_by(BalanceSheet.period_end.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_cash_flows(
    session: AsyncSession,
    ticker: str,
    limit: int = 20,
) -> list[CashFlow]:
    ticker_upper = ticker.upper()
    result = await session.execute(
        select(CashFlow)
        .where(CashFlow.ticker == ticker_upper)
        .order_by(CashFlow.period_end.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
