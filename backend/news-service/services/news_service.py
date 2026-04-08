"""News query service — reads from DB for API endpoints."""

from datetime import date, timedelta
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.news import Article, InstrumentSentiment, SentimentDaily

logger = structlog.get_logger()


async def get_news(
    session: AsyncSession,
    ticker: str | None = None,
    source: str | None = None,
    sentiment: str | None = None,
    impact: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """Fetch articles with optional filters. Returns (articles, total)."""
    query = select(Article).where(Article.is_processed.is_(True))

    if source:
        query = query.where(Article.source == source)
    if sentiment:
        query = query.where(Article.sentiment_label == sentiment)
    if impact:
        query = query.where(Article.impact_level == impact)

    # If ticker filter, join through instrument_sentiment
    if ticker:
        ticker_upper = ticker.upper()
        query = query.join(
            InstrumentSentiment, InstrumentSentiment.article_id == Article.id
        ).where(InstrumentSentiment.ticker == ticker_upper)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Article.published_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    articles = result.scalars().all()

    # Fetch associated tickers for each article
    article_ids = [a.id for a in articles]
    tickers_map: dict[UUID, list[str]] = {}
    if article_ids:
        ticker_rows = await session.execute(
            select(InstrumentSentiment.article_id, InstrumentSentiment.ticker)
            .where(InstrumentSentiment.article_id.in_(article_ids))
        )
        for aid, t in ticker_rows.all():
            tickers_map.setdefault(aid, []).append(t)

    data = []
    for a in articles:
        data.append({
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "published_at": a.published_at,
            "summary": a.summary,
            "sentiment_score": a.sentiment_score,
            "sentiment_label": a.sentiment_label,
            "impact_level": a.impact_level,
            "tickers": tickers_map.get(a.id, []),
        })

    return data, total


async def get_ticker_sentiment(
    session: AsyncSession,
    ticker: str,
    days: int = 7,
) -> list[SentimentDaily]:
    ticker_upper = ticker.upper()
    start_date = date.today() - timedelta(days=days)

    result = await session.execute(
        select(SentimentDaily)
        .where(
            SentimentDaily.ticker == ticker_upper,
            SentimentDaily.date >= start_date,
        )
        .order_by(SentimentDaily.date.asc())
    )
    return list(result.scalars().all())
