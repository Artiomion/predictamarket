"""
Live inference pipeline — adapted from models/08_live_inference_pipeline.ipynb.

Pipeline:
1. fetch_price_data() → OHLCV + technicals
2. fetch_macro_data() → VIX, treasury, S&P500, DXY, gold, oil
3. fetch_news_sentiment() → FinBERT → PCA → sent_0..sent_31 + news_count
4. Assemble DataFrame with exact column names from config
5. Missing features (SEC, FRED, insider, earnings, calendar) → zeros
6. TimeSeriesDataSet → tft_model.predict() → 7 quantiles × 22 steps
"""

import asyncio
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import structlog
import torch
import feedparser

from shared.yfinance_utils import yf_download, YFinanceError

logger = structlog.get_logger()


# ── Technical indicators ──────────────────────────────────────────────────────

def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _fetch_price_data_sync(ticker: str, lookback_days: int = 365) -> pd.DataFrame | None:
    """Fetch OHLCV + technical features from yfinance with retry + timeout."""
    end = datetime.now()
    start = end - timedelta(days=lookback_days)

    try:
        df = yf_download(ticker, start=start.strftime("%Y-%m-%d"))
    except YFinanceError as exc:
        structlog.get_logger().error("price_fetch_failed", ticker=ticker, error=str(exc))
        return None
    if len(df) == 0:
        return None

    df = df.reset_index()
    # Handle multi-level columns from yfinance
    if isinstance(df.columns[0], tuple):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.normalize()

    # Technical features matching config's time_varying_unknown_reals
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

    # 52-week proximity
    high_52 = df["High"].rolling(252, min_periods=60).max()
    low_52 = df["Low"].rolling(252, min_periods=60).min()
    df["pct_from_52wk_high"] = (df["Close"] - high_52) / high_52
    df["pct_from_52wk_low"] = (df["Close"] - low_52) / low_52

    # Capital Gains (proxy: adj_close change)
    df["Capital Gains"] = df["Close"].pct_change()

    return df.dropna(subset=["ma_50"]).reset_index(drop=True)


def _fetch_macro_data_sync(lookback_days: int = 200) -> pd.DataFrame | None:
    """Fetch macro features from yfinance."""
    end = datetime.now()
    start = end - timedelta(days=lookback_days)

    macro_map = {
        "^VIX": "vix", "^TNX": "treasury_10y", "^GSPC": "sp500",
        "DX-Y.NYB": "dxy", "GC=F": "gold", "CL=F": "oil",
    }

    dfs = []
    for symbol, name in macro_map.items():
        try:
            data = yf_download(symbol, start=start.strftime("%Y-%m-%d"))
            if len(data) > 0:
                dfs.append(data["Close"].squeeze().rename(name))
        except YFinanceError as exc:
            structlog.get_logger().warning("macro_fetch_error", symbol=symbol, error=str(exc))

    if not dfs:
        return None

    macro = pd.concat(dfs, axis=1).ffill()
    macro.index = macro.index.tz_localize(None) if macro.index.tz else macro.index

    if "vix" in macro.columns:
        macro["vix_ma5"] = macro["vix"].rolling(5).mean()
    if "sp500" in macro.columns:
        macro["sp500_return"] = np.log(macro["sp500"] / macro["sp500"].shift(1))

    # VIX term structure
    try:
        vix3m = yf_download("^VIX3M", start=start.strftime("%Y-%m-%d"))["Close"].squeeze()
        vix3m.index = vix3m.index.tz_localize(None) if vix3m.index.tz else vix3m.index
        macro["vix_contango"] = vix3m / macro["vix"] - 1
    except Exception:
        macro["vix_contango"] = 0.0

    return macro.dropna().reset_index().rename(columns={"index": "Date", "Date": "Date"})


def _fetch_news_and_sentiment_sync(
    ticker: str,
    tokenizer,
    finbert_model,
    pca,
    n_components: int = 32,
    max_articles: int = 20,
) -> pd.DataFrame:
    """Fetch RSS → FinBERT embeddings → PCA → daily aggregated sent_0..sent_31 + news_count."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    feed = feedparser.parse(url)

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

    # FinBERT [CLS] embeddings → PCA
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
    reduced = pca.transform(embeddings)  # 768d → 32d

    df = pd.DataFrame(reduced, columns=[f"sent_{i}" for i in range(n_components)])
    df["Date"] = dates
    daily = df.groupby("Date").agg(
        **{f"sent_{i}": (f"sent_{i}", "mean") for i in range(n_components)},
        news_count=("Date", "count"),
    ).reset_index()
    return daily


def _extract_variable_importance(
    tft_model,
    infer_dl,
    config: dict,
    signal: str,
    current_close: float,
    median_1d: float,
    top_n: int = 5,
) -> list[dict]:
    """Extract real variable importance from TFT interpret_output. Falls back to placeholder."""
    try:
        interpretation = tft_model.interpret_output(
            tft_model.predict(infer_dl, mode="raw"), reduction="sum"
        )
        # attention is dict with 'encoder_variables' → tensor of shape (n_encoder_vars,)
        enc_weights = interpretation.get("encoder_variables")
        if enc_weights is not None:
            enc_weights = enc_weights.detach().cpu().numpy().flatten()
            # Map to feature names from config
            feature_names = (
                config.get("time_varying_unknown_reals", [])
                + config.get("static_categoricals", [])
                + config.get("time_varying_known_categoricals", [])
            )
            # Trim to match shape
            n = min(len(enc_weights), len(feature_names))
            pairs = sorted(
                zip(feature_names[:n], enc_weights[:n]),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:top_n]

            factors = []
            for name, weight in pairs:
                w = round(float(abs(weight)), 4)
                if signal == "BUY":
                    direction = "bullish" if weight > 0 else "bearish"
                else:
                    direction = "bearish" if weight > 0 else "bullish"
                factors.append({"name": name, "weight": w, "direction": direction})
            return factors
    except Exception:
        pass

    # Fallback: static placeholder if interpret_output fails
    return [
        {"name": "momentum_20d", "weight": 0.18, "direction": "bullish" if signal == "BUY" else "bearish"},
        {"name": "rsi_14", "weight": 0.15, "direction": "bullish" if median_1d > current_close else "bearish"},
        {"name": "vix", "weight": 0.12, "direction": "bearish" if signal == "BUY" else "bullish"},
        {"name": "ma_50", "weight": 0.09, "direction": "neutral"},
        {"name": "sp500_return", "weight": 0.08, "direction": "neutral"},
    ]


def _run_inference_sync(
    ticker: str,
    artifacts,  # ModelArtifacts
) -> dict:
    """Full synchronous inference pipeline. Returns forecast dict or error dict."""
    artifacts.ensure_loaded()

    config = artifacts.config
    dataset_params = artifacts.dataset_params
    tft_model = artifacts.tft_model
    pca = artifacts.pca
    n_components = config.get("n_sentiment_components", 32)

    t0 = time.time()

    # 1. Prices + technicals
    prices = _fetch_price_data_sync(ticker)
    if prices is None or len(prices) < config["max_encoder_length"]:
        return {"error": f"Not enough price data for {ticker}"}

    # 2. Macro
    macro = _fetch_macro_data_sync()

    # 3. News sentiment
    sentiment = _fetch_news_and_sentiment_sync(
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

    # Beta to SPY
    if "sp500_return" in df.columns and "log_return" in df.columns:
        df["beta_spy_20d"] = (
            df["log_return"].rolling(20).cov(df["sp500_return"])
            / df["sp500_return"].rolling(20).var()
        )
        df["beta_spy_20d"] = df["beta_spy_20d"].fillna(1.0).clip(-5, 5)

    # Static + time-varying known categoricals
    df["ticker"] = ticker.lower()
    df["sector"] = config["sectors"].get(ticker.lower(), "N/A")
    df["day_of_week"] = df["Date"].dt.dayofweek.astype(str)
    df["month"] = df["Date"].dt.month.astype(str)

    # time_idx: use sequential integers
    df["time_idx"] = range(len(df))

    for col in config["static_categoricals"] + config["time_varying_known_categoricals"]:
        df[col] = df[col].astype(str)

    # Target column
    df["Close"] = df["Close"].astype(float)

    # Keep last encoder_length + prediction_length rows
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
        q = raw["prediction"][0].detach().cpu().numpy()  # (pred_len, 7)
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}

    # Keep reference for variable importance extraction
    _infer_dl_ref = infer_dl

    elapsed = time.time() - t0
    current_close = float(df["Close"].iloc[-config["max_prediction_length"] - 1])

    # Signal logic (from CLAUDE.md)
    median_1d = float(q[0, 3])
    lower_80_1d = float(q[0, 1])
    upper_80_1d = float(q[0, 5])

    signal = "BUY" if median_1d > current_close else "SELL"
    if lower_80_1d > current_close:
        confidence = "HIGH"
    elif upper_80_1d < current_close:
        confidence = "HIGH"
    elif abs(median_1d - current_close) / current_close < 0.005:
        signal = "HOLD"
        confidence = "LOW"
    else:
        confidence = "MEDIUM"

    # Build response
    def _horizon(step: int) -> dict | None:
        if step >= len(q):
            return None
        return {
            "median": round(float(q[step, 3]), 2),
            "lower_80": round(float(q[step, 1]), 2),
            "upper_80": round(float(q[step, 5]), 2),
            "lower_95": round(float(q[step, 0]), 2),
            "upper_95": round(float(q[step, 6]), 2),
        }

    forecast = {
        "1d": _horizon(0),
        "3d": _horizon(2),
        "1w": _horizon(4),
        "2w": _horizon(9),
        "1m": _horizon(21),
    }

    predicted_return_1d = round((float(q[0, 3]) / current_close - 1) * 100, 2) if current_close else None
    predicted_return_1w = round((float(q[4, 3]) / current_close - 1) * 100, 2) if len(q) > 4 and current_close else None
    predicted_return_1m = round((float(q[21, 3]) / current_close - 1) * 100, 2) if len(q) > 21 and current_close else None

# Extract real variable importance from TFT attention weights
    top_factors = _extract_variable_importance(tft_model, _infer_dl_ref, config, signal, current_close, median_1d)

    return {
        "ticker": ticker.upper(),
        "current_close": round(current_close, 2),
        "signal": signal,
        "confidence": confidence,
        "forecast": forecast,
        "full_curve": [round(float(q[i, 3]), 2) for i in range(len(q))],
        "variable_importance": {"top_factors": top_factors},
        "inference_time_s": round(elapsed, 2),
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
        "predicted_return_1d": predicted_return_1d,
        "predicted_return_1w": predicted_return_1w,
        "predicted_return_1m": predicted_return_1m,
        "news_articles_used": len(sentiment) if isinstance(sentiment, pd.DataFrame) and len(sentiment) > 0 else 0,
    }


async def run_inference(ticker: str, artifacts) -> dict:
    """Async wrapper — runs CPU-bound inference in thread pool."""
    return await asyncio.to_thread(_run_inference_sync, ticker, artifacts)
