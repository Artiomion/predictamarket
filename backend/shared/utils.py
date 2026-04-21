"""Shared utility functions and constants."""

import math

# ── Forecast constants ───────────────────────────────────────────────────────

# Step index → horizon label (TFT outputs 22 steps = 22 trading days)
HORIZON_STEPS: dict[str, int] = {"1d": 0, "3d": 2, "1w": 4, "2w": 9, "1m": 21}
HORIZON_LABELS: dict[int, str] = {v: k for k, v in HORIZON_STEPS.items()}

# Quantile indices in TFT output: prediction shape = (22, 7)
Q_02 = 0    # 2nd percentile  (lower 95% CI)
Q_10 = 1    # 10th percentile (lower 80% CI)
Q_25 = 2    # 25th percentile
Q_MEDIAN = 3  # 50th percentile (median)
Q_75 = 4    # 75th percentile
Q_90 = 5    # 90th percentile (upper 80% CI)
Q_98 = 6    # 98th percentile (upper 95% CI)

# Tier sentinel for "unlimited"
UNLIMITED = 999_999

# ── Ensemble disagreement tiers ──────────────────────────────────────────────
# Computed as std(medians_3_models) / |mean|. Thresholds derived from the
# ensemble_3_comparison study (p50 ≈ 0.008, p90 ≈ 0.016 across 9200 windows).
# Recalibrate these if retraining materially changes model agreement.
DISAGREEMENT_TIER_HIGH_MAX = 0.005   # < this → HIGH consensus (models strongly agree)
DISAGREEMENT_TIER_MEDIUM_MAX = 0.016  # < this → MEDIUM; otherwise → LOW consensus


def sanitize_nan(obj: object) -> object:
    """Recursively replace NaN/Inf floats with 0.0 for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0.0
    if isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_nan(v) for v in obj]
    return obj
