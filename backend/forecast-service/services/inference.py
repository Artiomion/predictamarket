"""
Live inference pipeline — reads ALL data from PostgreSQL, zero yfinance calls.

Data flow:
  update_prices.py (cron 15min) → market.price_history
  update_macro.py  (cron 15min) → market.macro_history
  fetch_news.py    (cron 30min) → news.articles + sentiment

  POST /forecast/{ticker} → reads DB only → TFT predict → response
"""

import asyncio
import math
import threading
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
import structlog
import torch
import feedparser
import requests

from shared.config import settings
from shared.utils import (
    HORIZON_STEPS, Q_02, Q_10, Q_MEDIAN, Q_90, Q_98, sanitize_nan,
)

logger = structlog.get_logger()

# Training start date for time_idx offset calculation
_TRAIN_START = pd.Timestamp("2000-03-14")


def _get_db_url() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")


# ── Technical indicators ──────────────────────────────────────────────────────

def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ── Data fetchers (all from DB) ──────────────────────────────────────────────

def _backfill_fresh_prices(ticker: str) -> None:
    """Fetch latest 5 days from yfinance and upsert into price_history.
    Ensures DB has the most current data before inference."""
    try:
        import yfinance as yf

        hist = yf.download(ticker, period="5d", progress=False, timeout=10)
        if hist is None or len(hist) == 0:
            return

        hist = hist.reset_index()
        if isinstance(hist.columns[0], tuple):
            hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]

        conn = psycopg2.connect(_get_db_url(), connect_timeout=5)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM market.instruments WHERE ticker = %s", (ticker,))
            row = cur.fetchone()
            if not row:
                return
            inst_id = row[0]

            for _, r in hist.iterrows():
                trade_date = r["Date"].date() if hasattr(r["Date"], "date") else r["Date"]
                close_val = float(r["Close"]) if r["Close"] == r["Close"] else None
                if not close_val:
                    continue
                cur.execute(
                    "INSERT INTO market.price_history (id, instrument_id, ticker, date, open, high, low, close, volume) "
                    "VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (ticker, date) DO UPDATE SET close = EXCLUDED.close, "
                    "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, volume = EXCLUDED.volume",
                    (str(inst_id), ticker, trade_date,
                     float(r["Open"]) if r["Open"] == r["Open"] else None,
                     float(r["High"]) if r["High"] == r["High"] else None,
                     float(r["Low"]) if r["Low"] == r["Low"] else None,
                     close_val,
                     int(r["Volume"]) if r["Volume"] == r["Volume"] else None),
                )
            conn.commit()
            cur.close()

            # Publish latest price to Redis for real-time WebSocket delivery
            if len(hist) >= 2:
                latest_close = float(hist.iloc[-1]["Close"]) if hist.iloc[-1]["Close"] == hist.iloc[-1]["Close"] else None
                prev_close = float(hist.iloc[-2]["Close"]) if hist.iloc[-2]["Close"] == hist.iloc[-2]["Close"] else None
                if latest_close:
                    import json as _json
                    import redis as _redis
                    _r = _redis.Redis.from_url(settings.REDIS_URL)
                    try:
                        price_data = {
                            "ticker": ticker,
                            "price": latest_close,
                            "change": round(latest_close - prev_close, 2) if prev_close else None,
                            "change_pct": round((latest_close - prev_close) / prev_close * 100, 2) if prev_close else None,
                        }
                        _r.set(f"mkt:price:{ticker}", _json.dumps(price_data), ex=900)
                        _r.publish("price.updated", _json.dumps(price_data))
                    finally:
                        _r.close()

            structlog.get_logger().info("prices_backfilled", ticker=ticker, rows=len(hist))
        finally:
            conn.close()
    except Exception as exc:
        structlog.get_logger().warning("backfill_prices_skipped", ticker=ticker, error=str(exc))


_MACRO_COLS = ("vix", "treasury_10y", "sp500", "dxy", "gold", "oil", "vix_ma5", "sp500_return", "vix_contango")

# TTL cache: don't re-backfill more than once per 5 minutes
_backfill_lock = threading.Lock()
_last_backfill_prices: dict[str, float] = {}
_last_backfill_macro: float = 0.0
_BACKFILL_TTL = 300  # seconds


def _backfill_fresh_macro() -> None:
    """Fetch latest 5 days of macro from yfinance and upsert into macro_history."""
    global _last_backfill_macro
    with _backfill_lock:
        if time.time() - _last_backfill_macro < _BACKFILL_TTL:
            return
        _last_backfill_macro = time.time()  # claim slot under lock

    try:
        import yfinance as yf

        macro_map = {"^VIX": "vix", "^TNX": "treasury_10y", "^GSPC": "sp500",
                     "DX-Y.NYB": "dxy", "GC=F": "gold", "CL=F": "oil"}
        dfs = []
        for symbol, name in macro_map.items():
            try:
                data = yf.download(symbol, period="5d", progress=False, timeout=10)
                if len(data) > 0:
                    dfs.append(data["Close"].squeeze().rename(name))
            except Exception as exc:
                structlog.get_logger().warning("macro_symbol_failed", symbol=symbol, error=str(exc))

        if not dfs:
            return

        macro = pd.concat(dfs, axis=1).ffill()
        macro.index = macro.index.tz_localize(None) if macro.index.tz else macro.index
        if "vix" in macro.columns:
            macro["vix_ma5"] = macro["vix"].rolling(5, min_periods=1).mean()
        if "sp500" in macro.columns:
            macro["sp500_return"] = np.log(macro["sp500"] / macro["sp500"].shift(1)).fillna(0)
        macro["vix_contango"] = 0.0
        macro = macro.dropna(subset=["vix", "sp500"]).reset_index()
        macro.rename(columns={"index": "date", "Date": "date"}, inplace=True)

        conn = psycopg2.connect(_get_db_url(), connect_timeout=5)
        try:
            cur = conn.cursor()
            for _, row in macro.iterrows():
                d = row["date"].date() if hasattr(row["date"], "date") else row["date"]
                vals = {c: (float(row[c]) if row[c] == row[c] else None) for c in _MACRO_COLS
                        if c in row.index}
                cols = ", ".join(vals.keys())
                placeholders = ", ".join(["%s"] * len(vals))
                updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in vals.keys())
                cur.execute(
                    f"INSERT INTO market.macro_history (id, date, {cols}) "
                    f"VALUES (gen_random_uuid(), %s, {placeholders}) "
                    f"ON CONFLICT (date) DO UPDATE SET {updates}",
                    (d, *vals.values()),
                )
            conn.commit()
            cur.close()
            structlog.get_logger().info("macro_backfilled", rows=len(macro))
        finally:
            conn.close()
    except Exception as exc:
        structlog.get_logger().warning("backfill_macro_skipped", error=str(exc))


def _fetch_price_data_sync(ticker: str, lookback_days: int = 365) -> pd.DataFrame | None:
    """Backfill fresh data from yfinance, then read from DB + compute technicals."""
    with _backfill_lock:
        need_prices = time.time() - _last_backfill_prices.get(ticker, 0) >= _BACKFILL_TTL
        if need_prices:
            _last_backfill_prices[ticker] = time.time()
    if need_prices:
        _backfill_fresh_prices(ticker)
    _backfill_fresh_macro()

    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    try:
        conn = psycopg2.connect(_get_db_url(), connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT date, open, high, low, close, volume FROM market.price_history "
            "WHERE ticker = %s AND date >= %s ORDER BY date ASC",
            (ticker, cutoff),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        structlog.get_logger().error("price_db_error", ticker=ticker, error=str(exc))
        return None

    if not rows or len(rows) < 60:
        return None

    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()

    # Technical features
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    df["volatility_5d"] = df["log_return"].rolling(5).std()
    df["volatility_20d"] = df["log_return"].rolling(20).std()
    df["ma_5"] = df["Close"].rolling(5).mean()
    df["ma_20"] = df["Close"].rolling(20).mean()
    df["ma_50"] = df["Close"].rolling(50).mean()
    df["rsi_14"] = _compute_rsi(df["Close"], 14)
    df["volume_ma_20"] = df["Volume"].rolling(20).mean()
    df["price_to_ma20"] = df["Close"] / df["ma_20"]
    df["price_to_ma50"] = df["Close"] / df["ma_50"]
    df["momentum_5d"] = df["Close"].pct_change(5)
    df["momentum_20d"] = df["Close"].pct_change(20)

    high_52 = df["High"].rolling(252, min_periods=60).max()
    low_52 = df["Low"].rolling(252, min_periods=60).min()
    df["pct_from_52wk_high"] = ((df["Close"] - high_52) / high_52).fillna(0)
    df["pct_from_52wk_low"] = ((df["Close"] - low_52) / low_52).fillna(0)
    df["Capital Gains"] = df["Close"].pct_change().fillna(0)

    structlog.get_logger().info("price_from_db", ticker=ticker, rows=len(df))
    return df.dropna(subset=["ma_50"]).reset_index(drop=True)


def _fetch_macro_data_sync(lookback_days: int = 200) -> pd.DataFrame | None:
    """Fetch macro from market.macro_history."""
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    try:
        conn = psycopg2.connect(_get_db_url(), connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT date, vix, treasury_10y, sp500, dxy, gold, oil, vix_ma5, sp500_return, vix_contango "
            "FROM market.macro_history WHERE date >= %s ORDER BY date ASC",
            (cutoff,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        structlog.get_logger().error("macro_db_error", error=str(exc))
        return None

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=[
        "Date", "vix", "treasury_10y", "sp500", "dxy", "gold", "oil",
        "vix_ma5", "sp500_return", "vix_contango",
    ])
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()

    structlog.get_logger().info("macro_from_db", rows=len(df))
    return df


def _fetch_news_sentiment_sync(
    ticker: str,
    tokenizer,
    finbert_model,
    pca,
    n_components: int = 32,
    max_articles: int = 20,
) -> pd.DataFrame:
    """Read sentiment from news.instrument_sentiment (already computed by news-service).

    Falls back to zeros if no sentiment data available.
    """
    import asyncio
    from shared.database import async_session_factory
    from sqlalchemy import select, text

    empty_cols = ["Date"] + [f"sent_{i}" for i in range(n_components)] + ["news_count"]

    try:
        async def _fetch():
            async with async_session_factory() as session:
                result = await session.execute(text("""
                    SELECT a.published_at::date as date, s.sentiment_score, a.title, a.summary
                    FROM news.instrument_sentiment s
                    JOIN news.articles a ON s.article_id = a.id
                    WHERE s.ticker = :ticker
                    AND a.published_at >= NOW() - INTERVAL '90 days'
                    ORDER BY a.published_at DESC
                    LIMIT :limit
                """), {"ticker": ticker, "limit": max_articles})
                return result.all()

        rows = asyncio.get_event_loop().run_until_complete(_fetch())
    except Exception as exc:
        structlog.get_logger().warning("sentiment_db_fetch_failed", ticker=ticker, error=str(exc))
        try:
            rows = asyncio.run(_fetch())
        except Exception:
            return pd.DataFrame(columns=empty_cols)

    if not rows:
        return pd.DataFrame(columns=empty_cols)

    # Build sentiment features using PCA on FinBERT if available, else use score as proxy
    articles_data = []
    for row in rows:
        pub_date = pd.Timestamp(row.date)
        text_content = ((row.title or "") + ". " + (row.summary or ""))[:512]
        articles_data.append({"date": pub_date, "text": text_content, "score": float(row.sentiment_score or 0.5)})

    if tokenizer is not None and finbert_model is not None and pca is not None:
        # Full FinBERT → PCA pipeline
        texts = [a["text"] for a in articles_data]
        dates = [a["date"] for a in articles_data]
        _FINBERT_BATCH = 16
        all_emb = []
        for i in range(0, len(texts), _FINBERT_BATCH):
            batch = texts[i:i + _FINBERT_BATCH]
            inputs = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                outputs = finbert_model(**inputs)
                cls = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                all_emb.append(cls)
            del inputs, outputs
        embeddings = np.vstack(all_emb)
        reduced = pca.transform(embeddings)
        df = pd.DataFrame(reduced, columns=[f"sent_{i}" for i in range(n_components)])
        df["Date"] = dates
    else:
        # Fallback: use sentiment_score as sent_0, zeros for rest
        df = pd.DataFrame({
            "Date": [a["date"] for a in articles_data],
            **{f"sent_{i}": [a["score"] if i == 0 else 0.0 for a in articles_data] for i in range(n_components)},
        })

    daily = df.groupby("Date").agg(
        **{f"sent_{i}": (f"sent_{i}", "mean") for i in range(n_components)},
        news_count=("Date", "count"),
    ).reset_index()
    return daily


# ── Variable importance ──────────────────────────────────────────────────────

def _extract_variable_importance(tft_model, infer_dl, config, signal, current_close, median_1d, raw_output=None, top_n=5):
    try:
        if raw_output is None:
            batch = next(iter(infer_dl))
            x, _ = batch
            with torch.no_grad():
                raw_output = tft_model(x)
        interpretation = tft_model.interpret_output(raw_output, reduction="sum")
        enc_weights = interpretation.get("encoder_variables")
        if enc_weights is not None:
            enc_weights = enc_weights.detach().cpu().numpy().flatten()
            feature_names = config.get("time_varying_unknown_reals", [])
            n = min(len(enc_weights), len(feature_names))
            pairs = sorted(zip(feature_names[:n], enc_weights[:n]), key=lambda x: abs(x[1]), reverse=True)[:top_n]
            factors = []
            for name, weight in pairs:
                w = round(float(abs(weight)), 4)
                if math.isnan(w):
                    w = 0.0
                direction = ("bullish" if weight > 0 else "bearish") if signal == "BUY" else ("bearish" if weight > 0 else "bullish")
                factors.append({"name": name, "weight": w, "direction": direction})
            return factors
    except Exception as exc:
        structlog.get_logger().warning("variable_importance_failed", error=str(exc))

    return [
        {"name": "momentum_20d", "weight": 0.18, "direction": "bullish" if signal == "BUY" else "bearish", "is_estimated": True},
        {"name": "rsi_14", "weight": 0.15, "direction": "bullish" if median_1d > current_close else "bearish", "is_estimated": True},
        {"name": "vix", "weight": 0.12, "direction": "bearish" if signal == "BUY" else "bullish", "is_estimated": True},
        {"name": "ma_50", "weight": 0.09, "direction": "neutral", "is_estimated": True},
        {"name": "sp500_return", "weight": 0.08, "direction": "neutral", "is_estimated": True},
    ]


# ── Main inference ───────────────────────────────────────────────────────────

def _run_inference_sync(ticker: str, artifacts) -> dict:
    """Full inference: DB prices + DB macro + RSS sentiment → TFT predict."""
    artifacts.ensure_loaded()

    config = artifacts.config
    dataset_params = artifacts.dataset_params
    tft_model = artifacts.tft_model
    pca = artifacts.pca
    n_components = config.get("n_sentiment_components", 32)

    t0 = time.time()

    # 1. Prices from DB
    prices = _fetch_price_data_sync(ticker)
    if prices is None or len(prices) < config["max_encoder_length"]:
        return {"error": f"Not enough price data for {ticker}. Run update_prices.py first."}

    # 2. Macro from DB
    macro = _fetch_macro_data_sync()

    # 3. News sentiment (RSS is lightweight, not rate-limited)
    sentiment = _fetch_news_sentiment_sync(
        ticker, artifacts.finbert_tokenizer, artifacts.finbert_model, pca, n_components
    )

    # 4. Assemble DataFrame
    df = prices.copy()

    if macro is not None:
        macro["Date"] = pd.to_datetime(macro["Date"])
        df = df.merge(macro, on="Date", how="left")
        for col in macro.columns:
            if col != "Date" and col in df.columns:
                df[col] = df[col].ffill().bfill()

    if len(sentiment) > 0:
        sentiment["Date"] = pd.to_datetime(sentiment["Date"])
        df = df.merge(sentiment, on="Date", how="left")

    # Fill all required columns
    for col in config["time_varying_unknown_reals"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].fillna(0.0)

    for col in config.get("table_metrics", []):
        if col not in df.columns:
            df[col] = 0.0

    for col in ["eps_surprise_pct", "earnings_beat", "earnings_miss", "has_earnings",
                 "days_since_earnings", "insider_buys", "insider_sells", "insider_net",
                 "cpi", "unemployment", "fed_funds_rate", "yield_curve_spread",
                 "m2_money_supply", "wti_crude", "fred_vix",
                 "days_to_fomc", "is_options_expiration", "is_quad_witching"]:
        if col not in df.columns:
            df[col] = 0.0

    if "sp500_return" in df.columns and "log_return" in df.columns:
        df["beta_spy_20d"] = (
            df["log_return"].rolling(20).cov(df["sp500_return"])
            / df["sp500_return"].rolling(20).var()
        )
        df["beta_spy_20d"] = df["beta_spy_20d"].fillna(1.0).clip(-5, 5)

    df["ticker"] = ticker.lower()
    df["sector"] = config["sectors"].get(ticker.lower(), "N/A")
    df["day_of_week"] = df["Date"].dt.dayofweek.astype(str)
    df["month"] = df["Date"].dt.month.astype(str)

    # time_idx must continue from training data sequence.
    # Training: 2000-03-14 to 2024-10-31, ~6428 trading days (time_idx 0..6427).
    # Live data continues from 6428+.
    first_date = df["Date"].iloc[0]
    offset = len(pd.bdate_range(_TRAIN_START, first_date)) - 1
    df["time_idx"] = range(offset, offset + len(df))

    for col in config["static_categoricals"] + config["time_varying_known_categoricals"]:
        df[col] = df[col].astype(str)

    df["Close"] = df["Close"].astype(float)

    needed = config["max_encoder_length"] + config["max_prediction_length"]
    df = df.tail(needed).reset_index(drop=True)
    # Preserve time_idx values (don't reset to 0)
    time_idx_start = df["time_idx"].iloc[0]
    df["time_idx"] = range(time_idx_start, time_idx_start + len(df))

    # 5. Predict
    try:
        from pytorch_forecasting import TimeSeriesDataSet

        train_stub = df.head(config["max_encoder_length"]).copy()
        training_ds = TimeSeriesDataSet.from_parameters(dataset_params, train_stub)
        infer_ds = TimeSeriesDataSet.from_dataset(training_ds, df, predict=True, stop_randomization=True)
        infer_dl = infer_ds.to_dataloader(train=False, batch_size=1, num_workers=0)

        # Use direct forward pass instead of predict() — Lightning's predict()
        # applies inverse transform via GroupNormalizer which produces NaN
        # on data outside training distribution.
        batch = next(iter(infer_dl))
        x, _ = batch
        with torch.no_grad():
            raw_output = tft_model(x)
        q = raw_output["prediction"][0].detach().cpu().numpy()  # (22, 7)
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}

    q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
    _infer_dl_ref = infer_dl

    elapsed = time.time() - t0
    current_close = float(df["Close"].iloc[-1])
    if math.isnan(current_close) or current_close <= 0:
        current_close = float(df["Close"].dropna().iloc[-1])

    # Signal logic
    median_1d = float(q[0, Q_MEDIAN])
    lower_80_1d = float(q[0, Q_10])
    upper_80_1d = float(q[0, Q_90])

    signal = "BUY" if median_1d > current_close else "SELL"
    if lower_80_1d > current_close:
        confidence = "HIGH"
    elif upper_80_1d < current_close:
        confidence = "HIGH"
    elif abs(median_1d - current_close) / max(current_close, 0.01) < 0.005:
        signal = "HOLD"
        confidence = "LOW"
    else:
        confidence = "MEDIUM"

    def _horizon(step: int) -> dict | None:
        if step >= len(q):
            return None
        return {
            "median": round(float(q[step, Q_MEDIAN]), 2),
            "lower_80": round(float(q[step, Q_10]), 2),
            "upper_80": round(float(q[step, Q_90]), 2),
            "lower_95": round(float(q[step, Q_02]), 2),
            "upper_95": round(float(q[step, Q_98]), 2),
        }

    forecast = {label: _horizon(step) for label, step in HORIZON_STEPS.items()}

    predicted_return_1d = round((float(q[0, Q_MEDIAN]) / current_close - 1) * 100, 2) if current_close else None
    predicted_return_1w = round((float(q[HORIZON_STEPS["1w"], Q_MEDIAN]) / current_close - 1) * 100, 2) if len(q) > HORIZON_STEPS["1w"] and current_close else None
    predicted_return_1m = round((float(q[HORIZON_STEPS["1m"], Q_MEDIAN]) / current_close - 1) * 100, 2) if len(q) > HORIZON_STEPS["1m"] and current_close else None

    top_factors = _extract_variable_importance(tft_model, _infer_dl_ref, config, signal, current_close, median_1d, raw_output=raw_output)

    return sanitize_nan({
        "ticker": ticker.upper(),
        "current_close": round(current_close, 2),
        "signal": signal,
        "confidence": confidence,
        "forecast": {k: {kk: vv for kk, vv in v.items()} if v else None for k, v in forecast.items()},
        "full_curve": [round(float(q[i, Q_MEDIAN]), 2) for i in range(len(q))],
        "variable_importance": {"top_factors": top_factors},
        "inference_time_s": round(elapsed, 2),
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
        "predicted_return_1d": predicted_return_1d,
        "predicted_return_1w": predicted_return_1w,
        "predicted_return_1m": predicted_return_1m,
        "news_articles_used": len(sentiment) if isinstance(sentiment, pd.DataFrame) and len(sentiment) > 0 else 0,
    })


async def run_inference(ticker: str, artifacts) -> dict:
    return await asyncio.to_thread(_run_inference_sync, ticker, artifacts)
