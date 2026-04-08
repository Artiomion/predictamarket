from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int


class ArticleResponse(BaseModel):
    id: UUID
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None
    sentiment_score: float | None
    sentiment_label: str | None
    impact_level: str | None
    tickers: list[str] = []

    model_config = {"from_attributes": True}


class ArticleListResponse(PaginatedResponse):
    data: list[ArticleResponse]


class SentimentPointResponse(BaseModel):
    date: date
    avg_sentiment: float | None
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int

    model_config = {"from_attributes": True}
