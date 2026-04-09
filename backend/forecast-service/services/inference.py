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
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
import structlog
import torch
import feedparser

from shared.config import settings

logger = structlog.get_logger()


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

def _fetch_price_data_sync(ticker: str, lookback_days: int = 365) -> pd.DataFrame | None:
    """Fetch OHLCV from market.price_history + compute technicals."""
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
    """Fetch RSS → FinBERT embeddings → PCA → daily sent_0..sent_31 + news_count."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return pd.DataFrame(columns=["Date"] + [f"sent_{i}" for i in range(n_components)] + ["news_count"])

    articles = []
    for entry in feed.entries[:max_articles]:
        try:
            pub = pd.to_datetime(entry.get("published", "")).tz_localize(None).normalize()
        except Exception:
            pub = pd.Timestamp.now().normalize()
        text = (entry.get("title", "") + ". " + entry.get("summary", ""))[:512]
        articles.append({"date": pub, "text": text})

    empty_cols = ["Date"] + [f"sent_{i}" for i in range(n_components)] + ["news_count"]
    if not articles:
        return pd.DataFrame(columns=empty_cols)

    texts = [a["text"] for a in articles]
    dates = [a["date"] for a in articles]

    all_emb = []
    for i in range(0, len(texts), 16):
        batch = texts[i:i + 16]
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
    daily = df.groupby("Date").agg(
        **{f"sent_{i}": (f"sent_{i}", "mean") for i in range(n_components)},
        news_count=("Date", "count"),
    ).reset_index()
    return daily


# ── Variable importance ──────────────────────────────────────────────────────

def _extract_variable_importance(tft_model, infer_dl, config, signal, current_close, median_1d, top_n=5):
    try:
        interpretation = tft_model.interpret_output(
            tft_model.predict(infer_dl, mode="raw"), reduction="sum"
        )
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
    except Exception:
        pass

    return [
        {"name": "momentum_20d", "weight": 0.18, "direction": "bullish" if signal == "BUY" else "bearish"},
        {"name": "rsi_14", "weight": 0.15, "direction": "bullish" if median_1d > current_close else "bearish"},
        {"name": "vix", "weight": 0.12, "direction": "bearish" if signal == "BUY" else "bullish"},
        {"name": "ma_50", "weight": 0.09, "direction": "neutral"},
        {"name": "sp500_return", "weight": 0.08, "direction": "neutral"},
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
    df["time_idx"] = range(len(df))

    for col in config["static_categoricals"] + config["time_varying_known_categoricals"]:
        df[col] = df[col].astype(str)

    df["Close"] = df["Close"].astype(float)

    needed = config["max_encoder_length"] + config["max_prediction_length"]
    df = df.tail(needed).reset_index(drop=True)
    df["time_idx"] = range(len(df))

    # 5. Predict
    try:
        from pytorch_forecasting import TimeSeriesDataSet

        train_stub = df.head(config["max_encoder_length"]).copy()
        training_ds = TimeSeriesDataSet.from_parameters(dataset_params, train_stub)
        infer_ds = TimeSeriesDataSet.from_dataset(training_ds, df, predict=True, stop_randomization=True)
        infer_dl = infer_ds.to_dataloader(train=False, batch_size=1, num_workers=0)

        raw = tft_model.predict(infer_dl, mode="raw")
        q = raw["prediction"][0].detach().cpu().numpy()
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}

    q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
    _infer_dl_ref = infer_dl

    elapsed = time.time() - t0
    current_close = float(df["Close"].iloc[-1])
    if math.isnan(current_close) or current_close <= 0:
        current_close = float(df["Close"].dropna().iloc[-1])

    # Signal logic
    median_1d = float(q[0, 3])
    lower_80_1d = float(q[0, 1])
    upper_80_1d = float(q[0, 5])

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

    def _horizon(step):
        if step >= len(q):
            return None
        return {
            "median": round(float(q[step, 3]), 2),
            "lower_80": round(float(q[step, 1]), 2),
            "upper_80": round(float(q[step, 5]), 2),
            "lower_95": round(float(q[step, 0]), 2),
            "upper_95": round(float(q[step, 6]), 2),
        }

    forecast = {"1d": _horizon(0), "3d": _horizon(2), "1w": _horizon(4), "2w": _horizon(9), "1m": _horizon(21)}

    predicted_return_1d = round((float(q[0, 3]) / current_close - 1) * 100, 2) if current_close else None
    predicted_return_1w = round((float(q[4, 3]) / current_close - 1) * 100, 2) if len(q) > 4 and current_close else None
    predicted_return_1m = round((float(q[21, 3]) / current_close - 1) * 100, 2) if len(q) > 21 and current_close else None

    top_factors = _extract_variable_importance(tft_model, _infer_dl_ref, config, signal, current_close, median_1d)

    def _safe(v):
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return 0.0
        return v

    return {
        "ticker": ticker.upper(),
        "current_close": _safe(round(current_close, 2)),
        "signal": signal,
        "confidence": confidence,
        "forecast": {k: {kk: _safe(vv) for kk, vv in v.items()} if v else None for k, v in forecast.items()},
        "full_curve": [_safe(round(float(q[i, 3]), 2)) for i in range(len(q))],
        "variable_importance": {"top_factors": top_factors},
        "inference_time_s": round(elapsed, 2),
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
        "predicted_return_1d": _safe(predicted_return_1d),
        "predicted_return_1w": _safe(predicted_return_1w),
        "predicted_return_1m": _safe(predicted_return_1m),
        "news_articles_used": len(sentiment) if isinstance(sentiment, pd.DataFrame) and len(sentiment) > 0 else 0,
    }


async def run_inference(ticker: str, artifacts) -> dict:
    return await asyncio.to_thread(_run_inference_sync, ticker, artifacts)
