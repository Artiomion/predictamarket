import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Double, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel, SoftDeleteMixin


class Instrument(SoftDeleteMixin, BaseModel):
    __tablename__ = "instruments"
    __table_args__ = {"schema": "market"}

    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    exchange: Mapped[str] = mapped_column(String(20), default="NYSE")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="instrument", cascade="all, delete-orphan")
    financial_metrics: Mapped[list["FinancialMetric"]] = relationship(back_populates="instrument", cascade="all, delete-orphan")
    profile: Mapped["CompanyProfile | None"] = relationship(back_populates="instrument", cascade="all, delete-orphan", uselist=False)


class PriceHistory(BaseModel):
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ticker", "date"),
        {"schema": "market"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float | None] = mapped_column(Double)
    high: Mapped[float | None] = mapped_column(Double)
    low: Mapped[float | None] = mapped_column(Double)
    close: Mapped[float] = mapped_column(Double, nullable=False)
    adj_close: Mapped[float | None] = mapped_column(Double)
    volume: Mapped[int | None] = mapped_column(BigInteger)

    instrument: Mapped["Instrument"] = relationship(back_populates="price_history")


class FinancialMetric(BaseModel):
    __tablename__ = "financial_metrics"
    __table_args__ = (
        UniqueConstraint("ticker", "period_end", "period_type"),
        {"schema": "market"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    revenue: Mapped[float | None] = mapped_column(Double)
    net_income: Mapped[float | None] = mapped_column(Double)
    eps: Mapped[float | None] = mapped_column(Double)
    pe_ratio: Mapped[float | None] = mapped_column(Double)
    pb_ratio: Mapped[float | None] = mapped_column(Double)
    dividend_yield: Mapped[float | None] = mapped_column(Double)
    debt_to_equity: Mapped[float | None] = mapped_column(Double)
    roe: Mapped[float | None] = mapped_column(Double)
    roa: Mapped[float | None] = mapped_column(Double)
    free_cash_flow: Mapped[float | None] = mapped_column(Double)
    operating_margin: Mapped[float | None] = mapped_column(Double)
    current_ratio: Mapped[float | None] = mapped_column(Double)

    instrument: Mapped["Instrument"] = relationship(back_populates="financial_metrics")


class CompanyProfile(BaseModel):
    __tablename__ = "company_profiles"
    __table_args__ = {"schema": "market"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), unique=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    ceo: Mapped[str | None] = mapped_column(String(255))
    employees: Mapped[int | None] = mapped_column(Integer)
    headquarters: Mapped[str | None] = mapped_column(String(255))
    founded_year: Mapped[int | None] = mapped_column(Integer)

    instrument: Mapped["Instrument"] = relationship(back_populates="profile")


class MacroHistory(BaseModel):
    __tablename__ = "macro_history"
    __table_args__ = {"schema": "market"}

    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    vix: Mapped[float | None] = mapped_column(Double)
    treasury_10y: Mapped[float | None] = mapped_column(Double)
    sp500: Mapped[float | None] = mapped_column(Double)
    dxy: Mapped[float | None] = mapped_column(Double)
    gold: Mapped[float | None] = mapped_column(Double)
    oil: Mapped[float | None] = mapped_column(Double)
    vix_ma5: Mapped[float | None] = mapped_column(Double)
    sp500_return: Mapped[float | None] = mapped_column(Double)
    vix_contango: Mapped[float | None] = mapped_column(Double)
