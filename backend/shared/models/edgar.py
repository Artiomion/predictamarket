import uuid
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Double, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel


class Filing(BaseModel):
    __tablename__ = "filings"
    __table_args__ = {"schema": "edgar"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    cik: Mapped[str | None] = mapped_column(String(20))
    accession_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    filing_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_of_report: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    income_statements: Mapped[list["IncomeStatement"]] = relationship(back_populates="filing", cascade="all, delete-orphan")
    balance_sheets: Mapped[list["BalanceSheet"]] = relationship(back_populates="filing", cascade="all, delete-orphan")
    cash_flows: Mapped[list["CashFlow"]] = relationship(back_populates="filing", cascade="all, delete-orphan")


class IncomeStatement(BaseModel):
    __tablename__ = "income_statements"
    __table_args__ = {"schema": "edgar"}

    filing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edgar.filings.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[float | None] = mapped_column(Double)
    cost_of_revenue: Mapped[float | None] = mapped_column(Double)
    gross_profit: Mapped[float | None] = mapped_column(Double)
    operating_income: Mapped[float | None] = mapped_column(Double)
    net_income: Mapped[float | None] = mapped_column(Double)
    eps_basic: Mapped[float | None] = mapped_column(Double)
    eps_diluted: Mapped[float | None] = mapped_column(Double)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger)

    filing: Mapped["Filing"] = relationship(back_populates="income_statements")


class BalanceSheet(BaseModel):
    __tablename__ = "balance_sheets"
    __table_args__ = {"schema": "edgar"}

    filing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edgar.filings.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_assets: Mapped[float | None] = mapped_column(Double)
    total_liabilities: Mapped[float | None] = mapped_column(Double)
    stockholders_equity: Mapped[float | None] = mapped_column(Double)
    cash_and_equivalents: Mapped[float | None] = mapped_column(Double)
    total_debt: Mapped[float | None] = mapped_column(Double)
    current_assets: Mapped[float | None] = mapped_column(Double)
    current_liabilities: Mapped[float | None] = mapped_column(Double)
    property_plant_equipment: Mapped[float | None] = mapped_column(Double)
    retained_earnings: Mapped[float | None] = mapped_column(Double)
    # Path B extensions — XBRL concepts required by the TFT feature set.
    common_stock_value: Mapped[float | None] = mapped_column(Double)
    accounts_payable_current: Mapped[float | None] = mapped_column(Double)
    accounts_receivable_net_current: Mapped[float | None] = mapped_column(Double)
    inventory_net: Mapped[float | None] = mapped_column(Double)
    dividends_per_share_declared: Mapped[float | None] = mapped_column(Double)

    filing: Mapped["Filing"] = relationship(back_populates="balance_sheets")


class CashFlow(BaseModel):
    __tablename__ = "cash_flows"
    __table_args__ = {"schema": "edgar"}

    filing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("edgar.filings.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    operating_cash_flow: Mapped[float | None] = mapped_column(Double)
    investing_cash_flow: Mapped[float | None] = mapped_column(Double)
    financing_cash_flow: Mapped[float | None] = mapped_column(Double)
    capital_expenditures: Mapped[float | None] = mapped_column(Double)
    free_cash_flow: Mapped[float | None] = mapped_column(Double)
    dividends_paid: Mapped[float | None] = mapped_column(Double)
    stock_repurchases: Mapped[float | None] = mapped_column(Double)
    # Path B extensions — additional XBRL concepts (SBC, buyback programs, etc.)
    proceeds_from_sale_of_ppe: Mapped[float | None] = mapped_column(Double)
    stock_issued_sbc_value: Mapped[float | None] = mapped_column(Double)
    stock_issued_sbc_shares: Mapped[float | None] = mapped_column(Double)
    payments_tax_withholding_sbc: Mapped[float | None] = mapped_column(Double)
    dividends_common_stock_cash: Mapped[float | None] = mapped_column(Double)
    stock_repurchase_authorized_amount: Mapped[float | None] = mapped_column(Double)
    stock_repurchase_remaining_amount: Mapped[float | None] = mapped_column(Double)

    filing: Mapped["Filing"] = relationship(back_populates="cash_flows")
