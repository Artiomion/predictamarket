from datetime import date
from uuid import UUID

from pydantic import BaseModel


class FilingResponse(BaseModel):
    id: UUID
    ticker: str
    cik: str | None
    accession_number: str
    filing_type: str
    filing_date: date
    period_of_report: date | None
    url: str | None

    model_config = {"from_attributes": True}


class IncomeStatementResponse(BaseModel):
    period_end: date
    revenue: float | None
    cost_of_revenue: float | None
    gross_profit: float | None
    operating_income: float | None
    net_income: float | None
    eps_basic: float | None
    eps_diluted: float | None
    shares_outstanding: int | None

    model_config = {"from_attributes": True}


class BalanceSheetResponse(BaseModel):
    period_end: date
    total_assets: float | None
    total_liabilities: float | None
    stockholders_equity: float | None
    cash_and_equivalents: float | None
    total_debt: float | None
    current_assets: float | None
    current_liabilities: float | None
    property_plant_equipment: float | None
    retained_earnings: float | None

    model_config = {"from_attributes": True}


class CashFlowResponse(BaseModel):
    period_end: date
    operating_cash_flow: float | None
    investing_cash_flow: float | None
    financing_cash_flow: float | None
    capital_expenditures: float | None
    free_cash_flow: float | None
    dividends_paid: float | None
    stock_repurchases: float | None

    model_config = {"from_attributes": True}
