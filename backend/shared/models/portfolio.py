import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel, SoftDeleteMixin


class Portfolio(SoftDeleteMixin, BaseModel):
    __tablename__ = "portfolios"
    __table_args__ = {"schema": "portfolio"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    total_value: Mapped[float] = mapped_column(Double, default=0)
    total_pnl: Mapped[float] = mapped_column(Double, default=0)
    total_pnl_pct: Mapped[float] = mapped_column(Double, default=0)

    items: Mapped[list["PortfolioItem"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioItem(BaseModel):
    __tablename__ = "portfolio_items"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker"),
        {"schema": "portfolio"},
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolio.portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Double, nullable=False)
    avg_buy_price: Mapped[float] = mapped_column(Double, nullable=False)
    current_price: Mapped[float | None] = mapped_column(Double)
    pnl: Mapped[float] = mapped_column(Double, default=0)
    pnl_pct: Mapped[float] = mapped_column(Double, default=0)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="items")


class Transaction(BaseModel):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "portfolio"}

    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolio.portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[float] = mapped_column(Double, nullable=False)
    price: Mapped[float] = mapped_column(Double, nullable=False)
    total_amount: Mapped[float] = mapped_column(Double, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="transactions")


class Watchlist(SoftDeleteMixin, BaseModel):
    __tablename__ = "watchlists"
    __table_args__ = {"schema": "portfolio"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="My Watchlist")

    items: Mapped[list["WatchlistItem"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(BaseModel):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "ticker"),
        {"schema": "portfolio"},
    )

    watchlist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolio.watchlists.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
