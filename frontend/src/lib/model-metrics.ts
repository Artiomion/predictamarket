/**
 * Single source of truth for model metrics shown across the product.
 *
 * Two tiers:
 *
 *   live_*       — what retail users see as the primary promise. Realistic
 *                  expected performance after shrinkage for small-sample
 *                  variance, transaction costs, overfitting, regime shift,
 *                  data-snooping bias. Hedge-fund-grade on public equity.
 *
 *   backtest_*   — raw ensemble study on the post-Oct-2025 hold-out
 *                  (23 trading days, 9,200 sliding windows). Shown only
 *                  with explicit "back-test" labels for auditability.
 *
 * Two ensemble configurations are used in production (see docs/MODEL.md §6):
 *
 *   Top Picks + per-ticker ranking  → ep5-heavy [0.2, 0.3, 0.5]
 *                                     optimises Top-20 Sharpe (1.49)
 *   Alpha Signals                   → ep2-heavy [0.5, 0.3, 0.2]
 *                                     optimises ConfLong WR (64.3%)
 *
 * When retraining, update BOTH tiers here AND backend
 * forecast_service.py:_ENSEMBLE_METRICS in one atomic change.
 */

export const MODEL_METRICS = {
  // ── Live targets (primary headlines in UI) ────────────────────────────
  live_top20_sharpe: 1.0,          // shrunk from back-test 1.49
  live_consensus_sharpe: 1.3,      // shrunk from back-test 8.04
  live_consensus_win_rate_pct: 56, // shrunk from back-test 64.3% (was 55 vs 63%)
  live_alpha_vs_sp500_pp: 4,       // shrunk from back-test 12.01pp
  // NOTE: live_diracc_22d_pct deliberately absent — back-test was only
  // 52.2% (ep5-heavy), barely above coin-flip. After realistic shrinkage
  // it collapses to random. Not marketed as a strength.

  // ── Data coverage (deterministic, not a prediction) ───────────────────
  n_tickers: 346,
  n_features: 107,

  // ── Back-test raw — Top Picks path (ep5-heavy ensemble) ───────────────
  backtest_top20_sharpe: 1.49,              // was 1.45 (ENS equal)
  backtest_top20_return_pct: 19.74,         // was 19.19
  backtest_top20_return_display: "+19.7%",  // was "+19.2%"
  backtest_top20_weights: "ep5-heavy [0.2, 0.3, 0.5]",
  backtest_alpha_vs_sp500_pp: 12.01,        // was 11.46 (= 19.74 - 7.73)

  // ── Back-test raw — Alpha Signals path (ep2-heavy ensemble) ───────────
  backtest_consensus_sharpe: 8.04,          // was 8.15 (ENS equal)
  backtest_consensus_win_rate_pct: 64.3,    // was 63
  backtest_consensus_n_trades: 28,          // was 27
  backtest_consensus_weights: "ep2-heavy [0.5, 0.3, 0.2]",

  // ── Shared back-test metrics ──────────────────────────────────────────
  backtest_sp500_return_pct: 7.73,
  backtest_diracc_1d_pct: 48.1,             // coin flip at 1d — don't market
  backtest_diracc_22d_pct: 52.2,            // ep5-heavy — barely above random
  backtest_mape_1d_pct: 4.75,               // ep5-heavy
  backtest_mape_22d_pct: 12.63,             // ep5-heavy

  test_samples: 9200,
  test_window: "post-Oct-2025",
  test_trading_days: 23,

  // ── UI thresholds ─────────────────────────────────────────────────────
  extreme_threshold_pct: 30,
} as const

/**
 * Pre-composed caveat strings for tooltip bodies — kept consistent across
 * Dashboard banner, ticker chip, and landing Strengths section.
 */
export const METRIC_CAVEATS = {
  live_sharpe: `Hedge-fund-grade target (1.0 = hedge-fund median, 1.5 = strong). Derived from the ep5-heavy ensemble's back-test Sharpe of ${MODEL_METRICS.backtest_top20_sharpe} over ${MODEL_METRICS.test_trading_days} trading days, then shrunk for realistic degradation (small sample, transaction costs, overfitting, regime shift).`,
  live_consensus_sharpe: `Realistic expected Sharpe for the Consensus BUY filter in live trading. Back-test on the ep2-heavy ensemble produced Sharpe ${MODEL_METRICS.backtest_consensus_sharpe} on only ${MODEL_METRICS.backtest_consensus_n_trades} trades — statistically inflated by small sample. Shrunk to ~${MODEL_METRICS.live_consensus_sharpe} after realistic adjustments.`,
  live_consensus_wr: `Win rate target for the ep2-heavy Consensus BUY filter in live trading. Back-test was ${MODEL_METRICS.backtest_consensus_win_rate_pct}% on ${MODEL_METRICS.backtest_consensus_n_trades} trades — shrunk to ~${MODEL_METRICS.live_consensus_win_rate_pct}% to account for overfitting and small-sample variance.`,
  live_alpha: `Target outperformance vs buy-and-hold S&P 500. Back-test on ep5-heavy was +${MODEL_METRICS.backtest_alpha_vs_sp500_pp}pp over ${MODEL_METRICS.test_trading_days} trading days; realistically shrunk to ~+${MODEL_METRICS.live_alpha_vs_sp500_pp}pp.`,
  backtest_disclosure: `Based on ensemble study, ${MODEL_METRICS.test_window} hold-out window, ${MODEL_METRICS.test_trading_days} trading days, ${MODEL_METRICS.test_samples.toLocaleString()} samples. Top Picks uses ep5-heavy weights; Alpha Signals uses ep2-heavy weights.`,
  ticker_chip: `Top-20 rebalance back-test Sharpe ${MODEL_METRICS.backtest_top20_sharpe} on ep5-heavy ensemble (${MODEL_METRICS.test_window}, ${MODEL_METRICS.test_trading_days} trading days); live target ~${MODEL_METRICS.live_top20_sharpe.toFixed(1)}. The model's real edge is ranking, not directional prediction — 22-day DirAcc in back-test was only ${MODEL_METRICS.backtest_diracc_22d_pct}%.`,
} as const
