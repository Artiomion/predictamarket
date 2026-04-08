"""
Fetch SEC EDGAR data for all 94 tickers → parse into financial statements.

Pipeline:
1. Resolve ticker → CIK (cached in Redis)
2. Fetch XBRL company facts from SEC EDGAR API
3. Parse into: Income Statement, Balance Sheet, Cash Flow
4. Store in: edgar.filings, edgar.income_statements, edgar.balance_sheets, edgar.cash_flows

Usage:
  PYTHONPATH=backend .venv/bin/python backend/edgar-service/scripts/fetch_edgar.py
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_svc_dir = _script_dir.parent
if str(_svc_dir) not in sys.path:
    sys.path.insert(0, str(_svc_dir))

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.edgar import BalanceSheet, CashFlow, Filing, IncomeStatement
from shared.models.market import Instrument
from shared.redis_client import redis_client

from services.sec_client import sec_client

setup_logging()
logger = structlog.get_logger()

# XBRL taxonomy → our column mapping
INCOME_FIELDS = {
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "SalesRevenueNet": "revenue",
    "CostOfRevenue": "cost_of_revenue",
    "CostOfGoodsAndServicesSold": "cost_of_revenue",
    "GrossProfit": "gross_profit",
    "OperatingIncomeLoss": "operating_income",
    "NetIncomeLoss": "net_income",
    "EarningsPerShareBasic": "eps_basic",
    "EarningsPerShareDiluted": "eps_diluted",
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted": "shares_outstanding",
    "CommonStockSharesOutstanding": "shares_outstanding",
}

BALANCE_FIELDS = {
    "Assets": "total_assets",
    "Liabilities": "total_liabilities",
    "StockholdersEquity": "stockholders_equity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "stockholders_equity",
    "CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
    "LongTermDebt": "total_debt",
    "LongTermDebtNoncurrent": "total_debt",
    "AssetsCurrent": "current_assets",
    "LiabilitiesCurrent": "current_liabilities",
    "PropertyPlantAndEquipmentNet": "property_plant_equipment",
    "RetainedEarningsAccumulatedDeficit": "retained_earnings",
}

CASHFLOW_FIELDS = {
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "NetCashProvidedByUsedInInvestingActivities": "investing_cash_flow",
    "NetCashProvidedByUsedInFinancingActivities": "financing_cash_flow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditures",
    "PaymentsOfDividends": "dividends_paid",
    "PaymentsOfDividendsCommonStock": "dividends_paid",
    "PaymentsForRepurchaseOfCommonStock": "stock_repurchases",
}


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _extract_facts(
    facts: dict,
    field_map: dict[str, str],
    form_filter: str = "10-K",
) -> dict[date, dict[str, float]]:
    """Extract XBRL facts into {period_end: {column: value}} dict."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    if not us_gaap:
        # Try IFRS for non-US companies
        us_gaap = facts.get("facts", {}).get("ifrs-full", {})
    results: dict[date, dict[str, float]] = {}

    for xbrl_tag, column in field_map.items():
        concept = us_gaap.get(xbrl_tag, {})
        units = concept.get("units", {})

        # Try USD first, then shares, then pure
        for unit_key in ["USD", "USD/shares", "shares", "pure"]:
            if unit_key not in units:
                continue
            for entry in units[unit_key]:
                form = entry.get("form", "")
                if form_filter and form != form_filter:
                    continue

                period_end = _parse_date(entry.get("end", ""))
                if not period_end:
                    continue

                val = entry.get("val")
                if val is None:
                    continue

                if period_end not in results:
                    results[period_end] = {}
                # First value wins (don't overwrite with restated)
                if column not in results[period_end]:
                    results[period_end][column] = float(val)
            break  # Use first matching unit

    return results


async def process_ticker(
    session: AsyncSession,
    ticker: str,
    instrument_id: str,
) -> dict[str, int]:
    """Fetch + parse EDGAR data for one ticker. Returns counts."""
    cik = await sec_client.get_cik_for_ticker(ticker)
    if not cik:
        await logger.awarning("no_cik", ticker=ticker)
        return {"filings": 0, "income": 0, "balance": 0, "cashflow": 0}

    facts = await sec_client.get_company_facts(cik)
    if not facts:
        return {"filings": 0, "income": 0, "balance": 0, "cashflow": 0}

    counts = {"filings": 0, "income": 0, "balance": 0, "cashflow": 0}

# Single query, consume result once
    existing_result = await session.execute(
        select(Filing.id).where(Filing.ticker == ticker, Filing.filing_type == "XBRL").limit(1)
    )
    existing_id = existing_result.scalar_one_or_none()

    if existing_id:
        filing_id = existing_id
    else:
        filing = Filing(
            instrument_id=instrument_id,
            ticker=ticker,
            cik=cik,
            accession_number=f"xbrl-{ticker}-{cik}",
            filing_type="XBRL",
            filing_date=date.today(),
            processed=True,
        )
        session.add(filing)
        await session.flush()
        filing_id = filing.id
        counts["filings"] = 1

    # Parse annual (10-K)
    for form, period_label in [("10-K", "annual"), ("10-Q", "quarterly")]:
        income_data = _extract_facts(facts, INCOME_FIELDS, form_filter=form)
        for period_end, values in sorted(income_data.items())[-8:]:  # Last 8 periods
            existing = await session.execute(
                select(IncomeStatement.id).where(
                    IncomeStatement.ticker == ticker,
                    IncomeStatement.period_end == period_end,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue
            session.add(IncomeStatement(
                filing_id=filing_id, ticker=ticker, period_end=period_end, **values,
            ))
            counts["income"] += 1

        balance_data = _extract_facts(facts, BALANCE_FIELDS, form_filter=form)
        for period_end, values in sorted(balance_data.items())[-8:]:
            existing = await session.execute(
                select(BalanceSheet.id).where(
                    BalanceSheet.ticker == ticker,
                    BalanceSheet.period_end == period_end,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue
            session.add(BalanceSheet(
                filing_id=filing_id, ticker=ticker, period_end=period_end, **values,
            ))
            counts["balance"] += 1

        cf_data = _extract_facts(facts, CASHFLOW_FIELDS, form_filter=form)
        for period_end, values in sorted(cf_data.items())[-8:]:
            # Compute free_cash_flow if we have operating and capex
            if "operating_cash_flow" in values and "capital_expenditures" in values:
                values["free_cash_flow"] = values["operating_cash_flow"] - abs(values["capital_expenditures"])
            existing = await session.execute(
                select(CashFlow.id).where(
                    CashFlow.ticker == ticker,
                    CashFlow.period_end == period_end,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue
            session.add(CashFlow(
                filing_id=filing_id, ticker=ticker, period_end=period_end, **values,
            ))
            counts["cashflow"] += 1

    return counts


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.ticker).where(
                Instrument.is_active.is_(True), Instrument.deleted_at.is_(None)
            ).order_by(Instrument.ticker)
        )
        tickers = result.all()

    await logger.ainfo("fetch_edgar_start", total=len(tickers))

    success = 0
    failed = 0
    totals = {"filings": 0, "income": 0, "balance": 0, "cashflow": 0}

    BATCH = 5
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        async with async_session_factory() as session:
            for inst_id, ticker in batch:
                try:
                    counts = await process_ticker(session, ticker, str(inst_id))
                    for k, v in counts.items():
                        totals[k] += v
                    success += 1
                except Exception as exc:
                    await logger.aerror("edgar_error", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo("edgar_batch", batch=f"{i+1}-{min(i+BATCH, len(tickers))}", success=success)

    await sec_client.close()
    await redis_client.aclose()
    await logger.ainfo("fetch_edgar_complete", success=success, failed=failed, **totals)


if __name__ == "__main__":
    asyncio.run(main())
