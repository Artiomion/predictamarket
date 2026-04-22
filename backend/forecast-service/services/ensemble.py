"""
Ensemble inference — runs 3 checkpoints (ep2, ep4, ep5), averages quantiles.

Empirical findings on test-set (see docs/model-eval.md):
  - MAPE barely moves (residual correlation ~0.98 between epochs)
  - Top-20 Sharpe:   1.36 (ep5 alone) → 1.45 (ensemble equal) — +7%
  - ConfLong Sharpe: 5.70 (ep2 alone) → 8.15 (ensemble equal) — +43%
  - ConfLong WR:    61.1% → 63.0%; N drops 36 → 27 (stricter consensus filter)

So: ensemble is NOT for price accuracy, it IS for signal quality.
Used by /signals endpoint + alpha_signals DAG. Not used on main /forecast.
"""

import asyncio
import math
import time
from datetime import datetime

import numpy as np
import pandas as pd
import structlog
import torch

from shared.utils import (
    DISAGREEMENT_TIER_HIGH_MAX,
    DISAGREEMENT_TIER_MEDIUM_MAX,
    HORIZON_STEPS, Q_02, Q_10, Q_MEDIAN, Q_90, Q_98, sanitize_nan,
)

from .inference import build_feature_df

logger = structlog.get_logger()


def _build_dataloader(df: pd.DataFrame, dataset_params):
    """Build inference dataloader from full encoder+prediction window."""
    from pytorch_forecasting import TimeSeriesDataSet

    infer_ds = TimeSeriesDataSet.from_parameters(
        dataset_params, df, predict=True, stop_randomization=True,
    )
    return infer_ds.to_dataloader(train=False, batch_size=1, num_workers=0)


def _run_ensemble_sync(
    ticker: str,
    artifacts,
    weights: list[float] | None = None,
    extract_factors: bool = False,
) -> dict:
    """Run 3-model ensemble inference. Returns signal-oriented payload.

    :param weights: weighting per model in `artifacts.ensemble_models` order
        ([ep2, ep4, ep5]). Defaults to equal (1/3, 1/3, 1/3). Production uses:
          [0.2, 0.3, 0.5]  — "ep5-heavy" for Top Picks (ranking strength)
          [0.5, 0.3, 0.2]  — "ep2-heavy" for Alpha Signals (WR strength)
    :param extract_factors: if True, run TFT attention interpretation on the
        highest-weighted model and include `variable_importance.top_factors`
        in the result. Needed when storing to `forecast.forecasts` (the
        forecast_factors FK requires it). Skip for alpha_signals table which
        doesn't have a factors column — saves ~1s per ticker.
    """
    artifacts.ensure_ensemble_loaded()
    config = artifacts.config
    dataset_params = artifacts.dataset_params
    models = artifacts.ensemble_models

    if weights is None:
        weights = [1.0 / len(models)] * len(models)
    w = np.array(weights, dtype=np.float32)
    w = w / w.sum()

    t0 = time.time()

    df = build_feature_df(ticker, config)  # tokenizer/finbert/pca not needed for ensemble path
    if df is None:
        return {"error": f"Not enough price data for {ticker}."}

    infer_dl = _build_dataloader(df, dataset_params)

    # Keep a reference to the raw_output of the highest-weighted model so we
    # can run attention interpretation on it if extract_factors is True.
    primary_idx = int(np.argmax(w))
    primary_raw_output = None

    try:
        batch = next(iter(infer_dl))
        x, _ = batch

        # Run each model — reuse batch, only forward pass changes
        quantiles_per_model = []
        with torch.no_grad():
            for i, m in enumerate(models):
                out = m(x)
                q = out["prediction"][0].detach().cpu().numpy()  # (22, 7)
                quantiles_per_model.append(q)
                if i == primary_idx and extract_factors:
                    primary_raw_output = out
    except Exception as e:
        return {"error": f"Ensemble prediction failed: {e}"}

    # Stack and weighted average
    stacked = np.stack(quantiles_per_model, axis=0)  # (3, 22, 7)
    stacked = np.nan_to_num(stacked, nan=0.0, posinf=0.0, neginf=0.0)
    q_ensemble = np.einsum("i,ihj->hj", w, stacked)  # (22, 7)

    # Disagreement: mean across all 22 horizons of std(medians)/|mean|.
    # Previously only used day-0 — models can agree on short-term and diverge
    # long-term (or vice versa). Averaging gives a more stable consensus score
    # that matches how the ensemble actually behaves across the forecast curve.
    medians_all = stacked[:, :, Q_MEDIAN]  # (3, 22)
    mean_per_step = np.abs(np.mean(medians_all, axis=0))  # (22,)
    std_per_step = np.std(medians_all, axis=0)  # (22,)
    per_step_cv = std_per_step / np.maximum(mean_per_step, 1e-9)
    disagreement = float(np.mean(per_step_cv))

    current_close = float(df["Close"].iloc[-1])
    if math.isnan(current_close) or current_close <= 0:
        current_close = float(df["Close"].dropna().iloc[-1])

    median_1d = float(q_ensemble[0, Q_MEDIAN])
    lower_80_1d = float(q_ensemble[0, Q_10])
    upper_80_1d = float(q_ensemble[0, Q_90])

    signal = "BUY" if median_1d > current_close else "SELL"
    if lower_80_1d > current_close:
        confidence = "HIGH"
        confident_long = True
    elif upper_80_1d < current_close:
        confidence = "HIGH"
        confident_long = False
    elif abs(median_1d - current_close) / max(current_close, 0.01) < 0.005:
        signal = "HOLD"
        confidence = "LOW"
        confident_long = False
    else:
        confidence = "MEDIUM"
        confident_long = False

    # Model consensus tier — thresholds live in shared.utils so they can be
    # recalibrated after retraining without touching inference code.
    if disagreement < DISAGREEMENT_TIER_HIGH_MAX:
        consensus = "HIGH"
    elif disagreement < DISAGREEMENT_TIER_MEDIUM_MAX:
        consensus = "MEDIUM"
    else:
        consensus = "LOW"

    def _horizon(step: int):
        if step >= len(q_ensemble):
            return None
        return {
            "median": round(float(q_ensemble[step, Q_MEDIAN]), 2),
            "lower_80": round(float(q_ensemble[step, Q_10]), 2),
            "upper_80": round(float(q_ensemble[step, Q_90]), 2),
            "lower_95": round(float(q_ensemble[step, Q_02]), 2),
            "upper_95": round(float(q_ensemble[step, Q_98]), 2),
        }

    forecast = {label: _horizon(step) for label, step in HORIZON_STEPS.items()}

    predicted_return_1d = round((median_1d / current_close - 1) * 100, 2) if current_close else None
    predicted_return_1w = (
        round((float(q_ensemble[HORIZON_STEPS["1w"], Q_MEDIAN]) / current_close - 1) * 100, 2)
        if current_close else None
    )
    predicted_return_1m = (
        round((float(q_ensemble[HORIZON_STEPS["1m"], Q_MEDIAN]) / current_close - 1) * 100, 2)
        if current_close else None
    )

    # Extract TFT attention from the highest-weighted model if requested.
    # This populates forecast_factors when storing to forecast.forecasts
    # (used by the /stocks/{ticker} page "What Moved the Prediction" card).
    top_factors: list[dict] = []
    if extract_factors and primary_raw_output is not None:
        try:
            from services.inference import _extract_variable_importance
            top_factors = _extract_variable_importance(
                models[primary_idx], infer_dl, config, signal,
                current_close, median_1d, raw_output=primary_raw_output,
            )
        except Exception as exc:
            structlog.get_logger().warning(
                "ensemble_factor_extraction_failed", ticker=ticker, error=str(exc),
            )

    elapsed = time.time() - t0

    # Individual numeric fields below are already finite floats. The single
    # sanitize_nan wrapper is a defensive net for nested dicts (forecast[horizon])
    # — round() returns NaN-floats if input is NaN, which would break JSON.
    result = {
        "ticker": ticker.upper(),
        "current_close": round(current_close, 2),
        "signal": signal,
        "confidence": confidence,
        "confident_long": confident_long,
        "model_consensus": consensus,
        "disagreement_score": round(disagreement, 4),
        "forecast": {k: v for k, v in forecast.items()},
        "full_curve": [round(float(q_ensemble[i, Q_MEDIAN]), 2) for i in range(len(q_ensemble))],
        "predicted_return_1d": predicted_return_1d,
        "predicted_return_1w": predicted_return_1w,
        "predicted_return_1m": predicted_return_1m,
        "ensemble_weights": [round(float(x), 3) for x in w],
        "ensemble_n_models": len(models),
        "inference_time_s": round(elapsed, 2),
        "forecast_date": datetime.now().strftime("%Y-%m-%d"),
    }
    if extract_factors:
        result["variable_importance"] = {"top_factors": top_factors}
    return sanitize_nan(result)


async def run_ensemble(
    ticker: str,
    artifacts,
    weights: list[float] | None = None,
    extract_factors: bool = False,
) -> dict:
    return await asyncio.to_thread(
        _run_ensemble_sync, ticker, artifacts, weights, extract_factors,
    )
