"""
Update macro data: yfinance → market.macro_history.

Fetches VIX, Treasury 10Y, S&P 500, DXY, Gold, Oil + computed (vix_ma5, sp500_return, vix_contango).
Run every 15 min via cron alongside update_prices.py.

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/update_macro.py
"""

import asyncio
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import structlog
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database import async_session_factory
from shared.logging import setup_logging

setup_logging()
logger = structlog.get_logger()

MACRO_SYMBOLS = {
    "^VIX": "vix",
    "^TNX": "treasury_10y",
    "^GSPC": "sp500",
    "DX-Y.NYB": "dxy",
    "GC=F": "gold",
    "CL=F": "oil",
}


async def main() -> None:
    import pandas as pd
    await logger.ainfo("update_macro_start")

    # Fetch all macro symbols
    dfs = []
    for symbol, name in MACRO_SYMBOLS.items():
        try:
            data = await asyncio.to_thread(
                lambda s=symbol: yf.download(s, period="1y", progress=False, timeout=15)
            )
            if len(data) > 0:
                dfs.append(data["Close"].squeeze().rename(name))
                await logger.ainfo("macro_fetched", symbol=symbol, name=name, rows=len(data))
            else:
                await logger.awarning("macro_empty", symbol=symbol)
        except Exception as exc:
            await logger.aerror("macro_error", symbol=symbol, error=str(exc))

    if not dfs:
        await logger.aerror("no_macro_data")
        return

    macro = pd.concat(dfs, axis=1).ffill()
    macro.index = macro.index.tz_localize(None) if macro.index.tz else macro.index

    # Computed features
    if "vix" in macro.columns:
        macro["vix_ma5"] = macro["vix"].rolling(5).mean()
    if "sp500" in macro.columns:
        macro["sp500_return"] = np.log(macro["sp500"] / macro["sp500"].shift(1))

    # VIX term structure
    try:
        vix3m = await asyncio.to_thread(
            lambda: yf.download("^VIX3M", period="1y", progress=False, timeout=15)["Close"].squeeze()
        )
        vix3m.index = vix3m.index.tz_localize(None) if vix3m.index.tz else vix3m.index
        macro["vix_contango"] = vix3m / macro["vix"] - 1
    except Exception:
        macro["vix_contango"] = 0.0

    macro = macro.dropna(subset=["vix", "sp500"]).reset_index()
    macro.rename(columns={"index": "date", "Date": "date"}, inplace=True)
    if "date" not in macro.columns:
        macro["date"] = macro.index

    # Upsert into DB
    rows_upserted = 0
    async with async_session_factory() as session:
        for _, row in macro.iterrows():
            trade_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]
            values = {
                "date": trade_date,
                "vix": float(row.get("vix", 0)) if row.get("vix") == row.get("vix") else None,
                "treasury_10y": float(row.get("treasury_10y", 0)) if row.get("treasury_10y") == row.get("treasury_10y") else None,
                "sp500": float(row.get("sp500", 0)) if row.get("sp500") == row.get("sp500") else None,
                "dxy": float(row.get("dxy", 0)) if row.get("dxy") == row.get("dxy") else None,
                "gold": float(row.get("gold", 0)) if row.get("gold") == row.get("gold") else None,
                "oil": float(row.get("oil", 0)) if row.get("oil") == row.get("oil") else None,
                "vix_ma5": float(row.get("vix_ma5", 0)) if row.get("vix_ma5") == row.get("vix_ma5") else None,
                "sp500_return": float(row.get("sp500_return", 0)) if row.get("sp500_return") == row.get("sp500_return") else None,
                "vix_contango": float(row.get("vix_contango", 0)) if row.get("vix_contango") == row.get("vix_contango") else None,
            }

            from shared.models.market import MacroHistory
            stmt = pg_insert(MacroHistory).values(**values).on_conflict_do_update(
                index_elements=["date"],
                set_={k: v for k, v in values.items() if k != "date"},
            )
            await session.execute(stmt)
            rows_upserted += 1

        await session.commit()

    await logger.ainfo("update_macro_complete", rows=rows_upserted)


if __name__ == "__main__":
    asyncio.run(main())
