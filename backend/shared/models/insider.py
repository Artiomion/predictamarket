import uuid
from datetime import date

from sqlalchemy import Date, Double, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import BaseModel


class InsiderTransaction(BaseModel):
    __tablename__ = "insider_transactions"
    __table_args__ = {"schema": "insider"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    insider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    insider_title: Mapped[str | None] = mapped_column(String(255))
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    shares: Mapped[float] = mapped_column(Double, nullable=False)
    price_per_share: Mapped[float | None] = mapped_column(Double)
    total_value: Mapped[float | None] = mapped_column(Double)
    shares_owned_after: Mapped[float | None] = mapped_column(Double)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    transaction_date: Mapped[date | None] = mapped_column(Date)
    sec_url: Mapped[str | None] = mapped_column(Text)
