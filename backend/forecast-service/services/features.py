"""
Feature augmentation — pulls all 107 TFT features from Postgres.

Motivation: the bare `build_feature_df` in inference.py only populates ~30/107
features (OHLCV + technicals + yfinance macro + partial sentiment). The other
77 were zero-filled, which pushed the model deep into out-of-distribution input
and produced garbage predictions ($42 for NVDA at $202).

This module fills the remaining 77 from existing DB tables:
  - earnings.earnings_results       → 5 earnings features
  - insider.insider_transactions    → 3 insider features
  - edgar.{balance_sheets,income_statements,cash_flows} → 15+ SEC features
  - news.instrument_sentiment.pca_vector → 32 sent_0..sent_31
  - market.macro_history.{cpi,...}  → 7 FRED features (after FRED pipeline runs)
  - Derived in-code                 → calendar (FOMC, options expiry, quad witching)

Performance notes:
  - A single psycopg2 connection is shared across all feature readers via
    `augment_features()` context manager — previously we opened 5 connections
    per `/forecast/{ticker}` which exhausted Postgres pool under load.
  - Rolling-window aggregations (earnings, insider) use vectorized numpy
    searchsorted instead of per-row pandas filtering (O(n) vs O(n×m)).
"""

from __future__ import annotations

import datetime as _dt
from contextlib import contextmanager

import numpy as np
import pandas as pd
import psycopg2
import structlog

from shared.config import settings

logger = structlog.get_logger()


def _db_url() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")


@contextmanager
def _db_connection():
    """Single psycopg2 connection shared across feature readers for one ticker.

    Replaces the pattern of opening 5 separate connections per inference which
    would exhaust `max_connections=100` under even modest load.
    """
    conn = psycopg2.connect(_db_url(), connect_timeout=5)
    try:
        yield conn
    finally:
        conn.close()


# ── Earnings (5 features) ────────────────────────────────────────────────────

def fetch_earnings_features(
    conn, ticker: str, dates: pd.Series,
) -> pd.DataFrame:
    """For each date, return the latest-before earnings_result.

    Features: eps_surprise_pct, earnings_beat, earnings_miss, has_earnings,
    days_since_earnings. Vectorized using merge_asof + searchsorted — no
    per-row iteration.
    """
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})
    out["eps_surprise_pct"] = 0.0
    out["earnings_beat"] = 0.0
    out["earnings_miss"] = 0.0
    out["has_earnings"] = 0.0
    out["days_since_earnings"] = 365.0

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT report_date, eps_surprise_pct, beat_estimate
                FROM earnings.earnings_results
                WHERE ticker = %s
                ORDER BY report_date ASC
                """,
                (ticker,),
            )
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        logger.warning("earnings_fetch_failed", ticker=ticker, error=str(exc))
        return out

    if not rows:
        return out

    er = pd.DataFrame(rows, columns=["report_date", "eps_surprise_pct", "beat"])
    er["report_date"] = pd.to_datetime(er["report_date"])
    er = er.sort_values("report_date").reset_index(drop=True)

    # Backward merge: latest earnings ≤ Date.
    joined = pd.merge_asof(
        out.sort_values("Date"),
        er,
        left_on="Date",
        right_on="report_date",
        direction="backward",
    )

    joined["eps_surprise_pct"] = joined["eps_surprise_pct_y"].fillna(0.0)
    joined["earnings_beat"] = (joined["beat"] == True).astype(float)  # noqa: E712
    joined["earnings_miss"] = (joined["beat"] == False).astype(float)  # noqa: E712
    joined["days_since_earnings"] = (
        (joined["Date"] - joined["report_date"]).dt.days.fillna(365).clip(0, 365)
    )

    # Vectorized has_earnings: for each Date, check if any report is within ±5 days.
    # searchsorted returns insertion positions; difference between +5d and -5d
    # position gives count of earnings in the window.
    dates_np = joined["Date"].values.astype("datetime64[ns]")
    reports = er["report_date"].values.astype("datetime64[ns]")
    window = np.timedelta64(5, "D")
    left_positions = np.searchsorted(reports, dates_np - window, side="left")
    right_positions = np.searchsorted(reports, dates_np + window, side="right")
    joined["has_earnings"] = (right_positions - left_positions > 0).astype(float)

    return joined[["Date", "eps_surprise_pct", "earnings_beat", "earnings_miss",
                   "has_earnings", "days_since_earnings"]]


# ── Insider (3 features) ─────────────────────────────────────────────────────

def fetch_insider_features(
    conn, ticker: str, dates: pd.Series,
) -> pd.DataFrame:
    """Rolling 60-day insider buy/sell counts and net shares.

    Uses numpy searchsorted for O(n) rolling window instead of O(n×m) iterrows.
    60-day window (was 30) catches late filings — insider Form 4 can be submitted
    up to 2 business days after a transaction, plus weekends.
    """
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})
    out["insider_buys"] = 0.0
    out["insider_sells"] = 0.0
    out["insider_net"] = 0.0

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT transaction_date, transaction_type, shares
                FROM insider.insider_transactions
                WHERE ticker = %s AND transaction_date IS NOT NULL
                ORDER BY transaction_date ASC
                """,
                (ticker,),
            )
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        logger.warning("insider_fetch_failed", ticker=ticker, error=str(exc))
        return out

    if not rows:
        return out

    tx = pd.DataFrame(rows, columns=["tdate", "ttype", "shares"])
    tx["tdate"] = pd.to_datetime(tx["tdate"])
    tx = tx.sort_values("tdate").reset_index(drop=True)
    tx["is_buy"] = tx["ttype"].str.upper().isin(["BUY", "P", "PURCHASE"]).astype(int)
    tx["is_sell"] = tx["ttype"].str.upper().isin(["SELL", "S", "SALE"]).astype(int)
    tx["signed_shares"] = tx["shares"] * (tx["is_buy"] - tx["is_sell"])

    # Vectorized rolling 60d via searchsorted + cumulative sums.
    WINDOW_DAYS = 60
    tdates = tx["tdate"].values.astype("datetime64[ns]")
    buys_cum = np.concatenate([[0], np.cumsum(tx["is_buy"].values)])
    sells_cum = np.concatenate([[0], np.cumsum(tx["is_sell"].values)])
    net_cum = np.concatenate([[0.0], np.cumsum(tx["signed_shares"].values)])

    dates_np = out["Date"].values.astype("datetime64[ns]")
    window = np.timedelta64(WINDOW_DAYS, "D")
    # side='right' so transactions ON the Date are included on the upper bound
    upper = np.searchsorted(tdates, dates_np, side="right")
    lower = np.searchsorted(tdates, dates_np - window, side="right")

    out["insider_buys"] = (buys_cum[upper] - buys_cum[lower]).astype(float)
    out["insider_sells"] = (sells_cum[upper] - sells_cum[lower]).astype(float)
    out["insider_net"] = (net_cum[upper] - net_cum[lower]).astype(float)
    return out


# ── SEC financials from EDGAR ────────────────────────────────────────────────

def fetch_sec_features(
    conn, ticker: str, dates: pd.Series,
) -> pd.DataFrame:
    """Pull latest-before SEC filing metrics for each date. Forward-fills.

    Column names in the returned DataFrame match the TFT's expected feature names
    (e.g. 'Assets', 'CommonStockValue') — they're the XBRL concept names verbatim.
    """
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})

    try:
        with conn.cursor() as cur:
            # Balance sheets — 7 core + 5 Path B extensions = 12 columns
            cur.execute(
                """
                SELECT period_end,
                       total_assets, stockholders_equity, retained_earnings,
                       property_plant_equipment, current_assets, current_liabilities,
                       total_liabilities,
                       common_stock_value, accounts_payable_current,
                       accounts_receivable_net_current, inventory_net,
                       dividends_per_share_declared
                FROM edgar.balance_sheets WHERE ticker = %s ORDER BY period_end ASC
                """,
                (ticker,),
            )
            bs_rows = cur.fetchall()

            # Cash flows — 5 core + 7 Path B extensions = 12 columns
            cur.execute(
                """
                SELECT period_end,
                       financing_cash_flow, investing_cash_flow, operating_cash_flow,
                       capital_expenditures, dividends_paid,
                       proceeds_from_sale_of_ppe,
                       stock_issued_sbc_value, stock_issued_sbc_shares,
                       payments_tax_withholding_sbc,
                       dividends_common_stock_cash,
                       stock_repurchase_authorized_amount,
                       stock_repurchase_remaining_amount
                FROM edgar.cash_flows WHERE ticker = %s ORDER BY period_end ASC
                """,
                (ticker,),
            )
            cf_rows = cur.fetchall()
    except psycopg2.Error as exc:
        logger.warning("sec_fetch_failed", ticker=ticker, error=str(exc))
        return out

    # Merge as-of each row
    if bs_rows:
        bs = pd.DataFrame(bs_rows, columns=[
            "period_end",
            # Core 7 → TFT feature names
            "Assets", "StockholdersEquity", "RetainedEarningsAccumulatedDeficit",
            "PropertyPlantAndEquipmentNet", "AssetsCurrent", "LiabilitiesCurrent",
            "Liabilities",
            # Path B 5 → TFT feature names
            "CommonStockValue", "AccountsPayableCurrent",
            "AccountsReceivableNetCurrent", "InventoryNet",
            "DividendsPayableAmountPerShare",
        ])
        bs["period_end"] = pd.to_datetime(bs["period_end"])
        bs = bs.sort_values("period_end")
        out = pd.merge_asof(
            out.sort_values("Date"), bs,
            left_on="Date", right_on="period_end", direction="backward",
        )
        out = out.drop(columns=["period_end"], errors="ignore")
        out["AssetsNoncurrent"] = (out["Assets"].fillna(0) - out["AssetsCurrent"].fillna(0))
        out["LiabilitiesNoncurrent"] = (out["Liabilities"].fillna(0) - out["LiabilitiesCurrent"].fillna(0))

    if cf_rows:
        cf = pd.DataFrame(cf_rows, columns=[
            "period_end",
            # Core 5 → TFT feature names
            "NetCashProvidedByUsedInFinancingActivities",
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInOperatingActivities",
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsOfDividends",
            # Path B 7 → TFT feature names
            "ProceedsFromSaleOfPropertyPlantAndEquipment",
            "StockIssuedDuringPeriodValueShareBasedCompensation",
            "StockIssuedDuringPeriodSharesShareBasedCompensation",
            "PaymentsRelatedToTaxWithholdingForShareBasedCompensation",
            "DividendsCommonStockCash",
            "StockRepurchaseProgramAuthorizedAmount1",
            "StockRepurchaseProgramRemainingAuthorizedRepurchaseAmount1",
        ])
        cf["period_end"] = pd.to_datetime(cf["period_end"])
        cf = cf.sort_values("period_end")
        for c in (
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsOfDividends",
            "PaymentsRelatedToTaxWithholdingForShareBasedCompensation",
            "DividendsCommonStockCash",
        ):
            cf[c] = pd.to_numeric(cf[c], errors="coerce").abs()

        out = pd.merge_asof(
            out.sort_values("Date"), cf,
            left_on="Date", right_on="period_end", direction="backward",
        )
        out = out.drop(columns=["period_end"], errors="ignore")

    # Derived: CashAndCashEquivalentsPeriodIncreaseDecrease ≈ op + inv + fin
    if "NetCashProvidedByUsedInOperatingActivities" in out.columns:
        out["CashAndCashEquivalentsPeriodIncreaseDecrease"] = (
            out["NetCashProvidedByUsedInOperatingActivities"].fillna(0)
            + out["NetCashProvidedByUsedInInvestingActivities"].fillna(0)
            + out["NetCashProvidedByUsedInFinancingActivities"].fillna(0)
        )

    # Fallback: DividendsCommonStockCash → generic PaymentsOfDividends
    if "DividendsCommonStockCash" in out.columns and "PaymentsOfDividends" in out.columns:
        dccs = pd.to_numeric(out["DividendsCommonStockCash"], errors="coerce")
        generic = pd.to_numeric(out["PaymentsOfDividends"], errors="coerce")
        out["DividendsCommonStockCash"] = dccs.fillna(generic).fillna(0.0)

    cols_to_fill = [c for c in out.columns if c != "Date"]
    out[cols_to_fill] = out[cols_to_fill].ffill().fillna(0.0)
    return out


# ── Sentiment PCA vector (32 features: sent_0..sent_31) ──────────────────────

def fetch_sentiment_pca(
    conn, ticker: str, dates: pd.Series, n_components: int = 32,
) -> pd.DataFrame:
    """Read pre-computed PCA vectors from news.instrument_sentiment.pca_vector."""
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})
    sent_cols = [f"sent_{i}" for i in range(n_components)]
    for c in sent_cols:
        out[c] = 0.0
    out["news_count"] = 0.0

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.published_at::date AS day,
                       s.sentiment_score, s.pca_vector
                FROM news.instrument_sentiment s
                JOIN news.articles a ON s.article_id = a.id
                WHERE s.ticker = %s
                  AND a.published_at >= NOW() - INTERVAL '180 days'
                """,
                (ticker,),
            )
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        logger.warning("sentiment_pca_fetch_failed", ticker=ticker, error=str(exc))
        return out

    if not rows:
        return out

    by_day: dict[_dt.date, list[np.ndarray]] = {}
    by_day_count: dict[_dt.date, int] = {}
    for day, score, vec in rows:
        if vec is None or len(vec) < n_components:
            v = np.zeros(n_components, dtype=np.float32)
            if score is not None:
                v[0] = float(score)
        else:
            v = np.asarray(vec[:n_components], dtype=np.float32)
        by_day.setdefault(day, []).append(v)
        by_day_count[day] = by_day_count.get(day, 0) + 1

    daily_rows = []
    for day, vecs in by_day.items():
        mean_vec = np.mean(np.stack(vecs, axis=0), axis=0)
        rec = {"Date": pd.Timestamp(day)}
        for i in range(n_components):
            rec[f"sent_{i}"] = float(mean_vec[i])
        rec["news_count"] = float(by_day_count[day])
        daily_rows.append(rec)

    daily_df = pd.DataFrame(daily_rows)
    merged = out[["Date"]].merge(daily_df, on="Date", how="left")
    for c in sent_cols + ["news_count"]:
        out[c] = merged[c].fillna(0.0).values
    return out


# ── FRED macro (7 features) ──────────────────────────────────────────────────

def fetch_fred_features(conn, dates: pd.Series) -> pd.DataFrame:
    """Pull FRED macro from market.macro_history (populated by update_fred.py)."""
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})
    cols = ["cpi", "unemployment", "fed_funds_rate", "yield_curve_spread",
            "m2_money_supply", "wti_crude", "fred_vix"]
    for c in cols:
        out[c] = 0.0

    try:
        with conn.cursor() as cur:
            # psycopg2 doesn't parameterize column names, but `cols` is a module
            # constant (not user input) — safe to embed via sql.Identifier.
            from psycopg2 import sql as _sql
            query = _sql.SQL(
                "SELECT date, {cols} FROM market.macro_history WHERE {nonnull} ORDER BY date ASC"
            ).format(
                cols=_sql.SQL(", ").join(_sql.Identifier(c) for c in cols),
                nonnull=_sql.SQL(" OR ").join(
                    _sql.SQL("{} IS NOT NULL").format(_sql.Identifier(c)) for c in cols
                ),
            )
            cur.execute(query)
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        logger.warning("fred_fetch_failed", error=str(exc))
        return out

    if not rows:
        return out

    fred = pd.DataFrame(rows, columns=["Date"] + cols)
    fred["Date"] = pd.to_datetime(fred["Date"])
    fred = fred.sort_values("Date")

    merged = pd.merge_asof(
        out.sort_values("Date"), fred,
        on="Date", direction="backward",
        suffixes=("", "_fred"),
    )
    for c in cols:
        src = f"{c}_fred" if f"{c}_fred" in merged.columns else c
        out[c] = merged[src].ffill().fillna(0.0).values
    return out


# ── Calendar features (4) — pure Python rules ────────────────────────────────

# TODO: refresh this list annually. After the last listed date, _days_to_next_fomc
# falls back to 90 — model won't be catastrophically wrong but `days_to_fomc`
# stops contributing signal. Federal Reserve publishes next year's calendar in
# August of the previous year: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
_FOMC_DATES: list[_dt.date] = [
    _dt.date(2025, 1, 29), _dt.date(2025, 3, 19), _dt.date(2025, 5, 7),
    _dt.date(2025, 6, 18), _dt.date(2025, 7, 30), _dt.date(2025, 9, 17),
    _dt.date(2025, 10, 29), _dt.date(2025, 12, 10),
    _dt.date(2026, 1, 28), _dt.date(2026, 3, 18), _dt.date(2026, 4, 29),
    _dt.date(2026, 6, 17), _dt.date(2026, 7, 29), _dt.date(2026, 9, 16),
    _dt.date(2026, 10, 28), _dt.date(2026, 12, 9),
    _dt.date(2027, 1, 27), _dt.date(2027, 3, 17), _dt.date(2027, 5, 5),
    _dt.date(2027, 6, 16), _dt.date(2027, 7, 28), _dt.date(2027, 9, 22),
    _dt.date(2027, 11, 3), _dt.date(2027, 12, 15),
]


def _days_to_next_fomc(d: _dt.date) -> int:
    for f in _FOMC_DATES:
        if f >= d:
            return (f - d).days
    return 90  # no known upcoming meeting → default 90


def _is_third_friday(d: _dt.date) -> bool:
    """Third Friday of the month = options expiration."""
    if d.weekday() != 4:  # not Friday
        return False
    return 15 <= d.day <= 21


def _is_quad_witching(d: _dt.date) -> bool:
    """Third Friday of Mar/Jun/Sep/Dec = quadruple witching."""
    return _is_third_friday(d) and d.month in (3, 6, 9, 12)


def compute_calendar_features(dates: pd.Series) -> pd.DataFrame:
    out = pd.DataFrame({"Date": pd.to_datetime(dates)})
    d_series = out["Date"].dt.date
    out["days_to_fomc"] = d_series.apply(_days_to_next_fomc).astype(float)
    out["is_options_expiration"] = d_series.apply(_is_third_friday).astype(float)
    out["is_quad_witching"] = d_series.apply(_is_quad_witching).astype(float)
    return out


# ── Master augmentation ──────────────────────────────────────────────────────

def augment_features(df: pd.DataFrame, ticker: str, n_sentiment: int = 32) -> pd.DataFrame:
    """Fill earnings/insider/SEC/sentiment-PCA/FRED/calendar columns in place.

    Opens a single Postgres connection and passes it to each reader — avoids
    5× connection churn that was exhausting max_connections under load.
    """
    dates = df["Date"]

    with _db_connection() as conn:
        earnings_df = fetch_earnings_features(conn, ticker, dates)
        insider_df = fetch_insider_features(conn, ticker, dates)
        sec_df = fetch_sec_features(conn, ticker, dates)
        sentiment_df = fetch_sentiment_pca(conn, ticker, dates, n_components=n_sentiment)
        fred_df = fetch_fred_features(conn, dates)
    cal_df = compute_calendar_features(dates)

    result = df.copy()
    for aux in (earnings_df, insider_df, sec_df, sentiment_df, fred_df, cal_df):
        keys = [c for c in aux.columns if c != "Date"]
        if not keys:
            continue
        merged = result[["Date"]].merge(aux, on="Date", how="left")
        for c in keys:
            result[c] = merged[c].fillna(0.0).values

    return result
