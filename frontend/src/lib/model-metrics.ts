/**
 * Single source of truth for back-test metrics shown across the product.
 *
 * Every number here is reproducible from the ep2+ep4+ep5 ensemble study on
 * the post-Oct-2025 hold-out window. See:
 *   - docs/ENSEMBLE_NOTES.md
 *   - backend/forecast-service/services/forecast_service.py (ModelVersion.metrics)
 *
 * When retraining: update this file AND the backend ModelVersion.metrics seed.
 * (TODO: eventually fetch from GET /api/forecast/model-version so retrains
 * propagate automatically.)
 */

export const MODEL_METRICS = {
  // Ranking (Top-20 daily rebalance)
  top20_sharpe: 1.45,
  top20_return_pct: 19.19,
  top20_return_display: "+19.2%",
  sp500_return_pct: 7.73,
  alpha_vs_sp500_pp: 11.46,

  // Direction accuracy
  diracc_1d_pct: 48.8,
  diracc_22d_pct: 68,

  // Error
  mape_1d_pct: 4.78,
  mape_22d_pct: 12.49,

  // Ensemble consensus filter (Alpha Signals)
  conflong_sharpe: 8.15,
  conflong_win_rate_pct: 63,
  conflong_n_trades: 27,

  // Test coverage
  test_samples: 9200,
  test_window: "post-Oct-2025",
  test_trading_days: 23,

  // Data coverage
  n_tickers: 346,
  n_features: 107,
} as const

/**
 * Pre-composed caveat strings for tooltip bodies — kept consistent across
 * Dashboard banner, ticker chip, and landing Strengths section.
 */
export const METRIC_CAVEATS = {
  top20_sharpe: `Top-20 daily-rebalance back-test, 3-model ensemble, ${MODEL_METRICS.test_trading_days} trading days ${MODEL_METRICS.test_window}.`,
  diracc_22d: `${MODEL_METRICS.test_samples.toLocaleString()} test samples, ~34σ above a coin flip. Strongest edge on multi-week drift.`,
  consensus_wr: `When all 3 ensemble checkpoints agree that the 80% CI bottom is above current price, ${MODEL_METRICS.conflong_n_trades}-trade back-test at Sharpe ${MODEL_METRICS.conflong_sharpe}.`,
  alpha: `Top-20 daily-rebalance portfolio: +${MODEL_METRICS.top20_return_pct}% vs S&P 500 +${MODEL_METRICS.sp500_return_pct}% on the same test window.`,
  ticker_chip: `Ensemble back-test (${MODEL_METRICS.test_window}): ${MODEL_METRICS.diracc_22d_pct}% directional accuracy at 22-day horizon across ${MODEL_METRICS.test_samples.toLocaleString()} samples, Sharpe ${MODEL_METRICS.top20_sharpe} on Top-20 rebalance.`,
} as const
