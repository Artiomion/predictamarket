import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Double, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel


class Article(BaseModel):
    __tablename__ = "articles"
    __table_args__ = {"schema": "news"}

    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))
    impact_level: Mapped[str] = mapped_column(String(20), default="low", index=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    instrument_sentiments: Mapped[list["InstrumentSentiment"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class InstrumentSentiment(BaseModel):
    __tablename__ = "instrument_sentiment"
    __table_args__ = {"schema": "news"}

    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("news.articles.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    relevance_score: Mapped[float | None] = mapped_column(Double, default=1.0)
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))
    # 32-dim FinBERT[CLS]→IncrementalPCA vector used as sent_0..sent_31 features.
    # Null for legacy rows inserted before the embedding pipeline was wired up.
    pca_vector: Mapped[list[float] | None] = mapped_column(ARRAY(Double))

    article: Mapped["Article"] = relationship(back_populates="instrument_sentiments")


class SocialMention(BaseModel):
    __tablename__ = "social_mentions"
    __table_args__ = {"schema": "news"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    post_id: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    sentiment_label: Mapped[str | None] = mapped_column(String(20))
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class SentimentDaily(BaseModel):
    __tablename__ = "sentiment_daily"
    __table_args__ = (
        UniqueConstraint("ticker", "date"),
        {"schema": "news"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    avg_sentiment: Mapped[float | None] = mapped_column(Double)
    news_count: Mapped[int] = mapped_column(Integer, default=0)
    social_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
