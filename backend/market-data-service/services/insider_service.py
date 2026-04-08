import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.insider import InsiderTransaction

logger = structlog.get_logger()


async def get_insider_transactions(
    session: AsyncSession,
    ticker: str,
    limit: int = 50,
) -> list[InsiderTransaction]:
    ticker_upper = ticker.upper()

    query = (
        select(InsiderTransaction)
        .where(InsiderTransaction.ticker == ticker_upper)
        .order_by(InsiderTransaction.filing_date.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    return list(result.scalars().all())
