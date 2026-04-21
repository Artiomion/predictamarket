/**
 * Single source of truth for model metrics shown across the product.
 *
 * We publish TWO tiers of numbers:
 *
 *   live_*   — expected performance after realistic degradation. These are
 *              what retail users see as the primary promise. Derived from
 *              back-test by applying shrinkage for: small-sample variance,
 *              transaction costs, overfitting (epoch cherry-picking),
 *              data-snooping bias, and market-regime shift. These are what
 *              we'll actually be measured against once live track record
 *              accumulates.
 *
 *   backtest_* — raw ep2+ep4+ep5 ensemble study on the post-Oct-2025
 *              hold-out window (23 trading days, 9,200 position-days).
 *              Shown with explicit "back-test" labels only, never as the
 *              headline number. Preserved here for auditability and for
 *              academic-context tooltips.
 *
 * When retraining: update BOTH tiers and the backend
 * forecast_service.py:_ENSEMBLE_METRICS seed. Eventually we should compute
 * live numbers from rolling walk-forward validation instead of applying
 * heuristic shrinkage.
 *
 * See: docs/ENSEMBLE_NOTES.md, CLAUDE.md Caveats section.
 */

export const MODEL_METRICS = {
  // ── Live (expected) — what we promise to retail ────────────────────────
  // Honest targets after accounting for transaction costs, overfitting,
  // regime shift, and the reality that 27-trade backtest Sharpe can't
  // repeat. These correspond to hedge-fund-grade performance on public
  // equity (Sharpe 1.0 = hedge-fund median, 1.5 = good).
  live_top20_sharpe: 1.0,          // was back-test 1.45 → shrunk
  live_consensus_sharpe: 1.3,      // was back-test 8.15 → heavily shrunk
  live_consensus_win_rate_pct: 55, // was back-test 63% → shrunk
  live_diracc_22d_pct: 60,         // was back-test 68% → shrunk
  live_alpha_vs_sp500_pp: 4,       // was back-test 11.46 → shrunk ~3×

  // ── Data coverage (deterministic, not a prediction) ────────────────────
  n_tickers: 346,
  n_features: 107,

  // ── Back-test raw numbers (for audit / caveat tooltips only) ───────────
  // Sourced from the ep2+ep4+ep5 ensemble study on the post-Oct-2025 test
  // window (Nov 2025 → early Apr 2026, 23 trading days, 9,200 samples).
  // DO NOT show these as primary metrics in UI — use the live_* fields.
  backtest_top20_sharpe: 1.45,
  backtest_top20_return_pct: 19.19,
  backtest_top20_return_display: "+19.2%",
  backtest_sp500_return_pct: 7.73,
  backtest_alpha_vs_sp500_pp: 11.46,
  backtest_diracc_1d_pct: 48.8,
  backtest_diracc_22d_pct: 68,
  backtest_mape_1d_pct: 4.78,
  backtest_mape_22d_pct: 12.49,
  backtest_consensus_sharpe: 8.15,
  backtest_consensus_win_rate_pct: 63,
  backtest_consensus_n_trades: 27,
  test_samples: 9200,
  test_window: "post-Oct-2025",
  test_trading_days: 23,

  // ── UI thresholds ──────────────────────────────────────────────────────
  // When |predicted_return_1m| exceeds this, surface a mean-reversion
  // warning (stock is likely out of training distribution).
  extreme_threshold_pct: 30,
} as const

/**
 * Pre-composed caveat strings for tooltip bodies. The top-level surfaces
 * should reference live_* metrics with the caveat pointing to backtest_*.
 */
export const METRIC_CAVEATS = {
  live_sharpe: `Hedge-fund-grade target (1.0 = hedge-fund median, 1.5 = strong). Derived from ${MODEL_METRICS.backtest_top20_sharpe} back-test Sharpe on 23 trading days, shrunk for small-sample variance, transaction costs, overfitting, and regime shift.`,
  live_consensus_sharpe: `Realistic estimate for the Consensus BUY filter in live trading. Back-test produced Sharpe ${MODEL_METRICS.backtest_consensus_sharpe} on ${MODEL_METRICS.backtest_consensus_n_trades} trades — statistically inflated by small sample. Shrunk to ~${MODEL_METRICS.live_consensus_sharpe} after accounting for overfitting, data-snooping bias, and transaction costs.`,
  live_diracc: `Directional accuracy at the 22-trading-day horizon — expected live. Back-test was ${MODEL_METRICS.backtest_diracc_22d_pct}% on ${MODEL_METRICS.test_samples.toLocaleString()} samples, shrunk to ~${MODEL_METRICS.live_diracc_22d_pct}% after accounting for overfitting and regime shift.`,
  live_consensus_wr: `Win rate of the Consensus BUY filter in expected live trading. Back-test was ${MODEL_METRICS.backtest_consensus_win_rate_pct}% on ${MODEL_METRICS.backtest_consensus_n_trades} trades — shrunk to ${MODEL_METRICS.live_consensus_win_rate_pct}% to account for small-sample overfit.`,
  live_alpha: `Target outperformance vs buy-and-hold S&P 500. Back-test was +${MODEL_METRICS.backtest_alpha_vs_sp500_pp}pp on 23 trading days, shrunk to ~+${MODEL_METRICS.live_alpha_vs_sp500_pp}pp realistically.`,
  backtest_disclosure: `Based on ep2+ep4+ep5 ensemble study, ${MODEL_METRICS.test_window} hold-out window, ${MODEL_METRICS.test_trading_days} trading days, ${MODEL_METRICS.test_samples.toLocaleString()} samples.`,
  ticker_chip: `Back-test ${MODEL_METRICS.test_window}: ${MODEL_METRICS.backtest_diracc_22d_pct}% directional accuracy at 22-day horizon; live target ~${MODEL_METRICS.live_diracc_22d_pct}%. Top-20 rebalance Sharpe ${MODEL_METRICS.backtest_top20_sharpe} back-test, ~${MODEL_METRICS.live_top20_sharpe} live target.`,
} as const
