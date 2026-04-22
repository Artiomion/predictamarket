import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_read_session as get_session

from schemas.news import ArticleListResponse, SentimentPointResponse
from services.news_service import get_news, get_ticker_sentiment

logger = structlog.get_logger()
router = APIRouter()


@router.get("/news", response_model=ArticleListResponse)
async def list_news(
    ticker: str | None = Query(None),
    source: str | None = Query(None),
    sentiment: str | None = Query(None, pattern="^(positive|negative|neutral)$"),
    impact: str | None = Query(None, pattern="^(low|medium|high)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    data, total = await get_news(
        session, ticker=ticker, source=source, sentiment=sentiment,
        impact=impact, page=page, per_page=per_page,
    )
    return {"data": data, "total": total, "page": page, "per_page": per_page}


@router.get("/news/{ticker}", response_model=ArticleListResponse)
async def news_by_ticker(
    ticker: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    data, total = await get_news(session, ticker=ticker, page=page, per_page=per_page)
    return {"data": data, "total": total, "page": page, "per_page": per_page}


@router.get("/news/{ticker}/sentiment", response_model=list[SentimentPointResponse])
async def ticker_sentiment(
    ticker: str,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> list[SentimentPointResponse]:
    rows = await get_ticker_sentiment(session, ticker, days=days)
    return [SentimentPointResponse.model_validate(r) for r in rows]


@router.get("/feed", response_model=ArticleListResponse)
async def news_feed(
    user_id: uuid.UUID = Depends(require_user_id),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Personalized news feed — requires auth. Returns all news sorted by recency."""
    data, total = await get_news(session, page=page, per_page=per_page)
    return {"data": data, "total": total, "page": page, "per_page": per_page}
