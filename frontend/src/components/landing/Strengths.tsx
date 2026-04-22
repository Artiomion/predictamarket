"use client"

import { motion } from "framer-motion"
import { CheckCircle2, Info } from "lucide-react"
import { MODEL_METRICS } from "@/lib/model-metrics"

/**
 * Model-strength showcase — live targets as headlines, back-test numbers
 * as secondary context. We publish realistic expected performance (after
 * shrinkage for small-sample, overfitting, costs, regime shift) rather
 * than raw back-test numbers that would not hold in production.
 */
const strengths = [
  {
    title: `Relative ranking (${MODEL_METRICS.n_tickers} stocks)`,
    metric: `Sharpe ~${MODEL_METRICS.live_top20_sharpe.toFixed(1)} live target`,
    detail: `Top-20 daily-rebalance with ep5-heavy ensemble [0.2/0.3/0.5] targets hedge-fund-grade risk-adjusted return in live trading. Back-test on ${MODEL_METRICS.test_trading_days} trading days produced Sharpe ${MODEL_METRICS.backtest_top20_sharpe}; shrunk to ~${MODEL_METRICS.live_top20_sharpe.toFixed(1)} after costs, overfitting, and regime shift.`,
  },
  {
    title: "3-model consensus filter",
    metric: `~${MODEL_METRICS.live_consensus_win_rate_pct}% win rate live`,
    detail: `When all 3 ensemble checkpoints (ep2+ep4+ep5) agree the 80% CI bottom is above current price. Uses ep2-heavy weights [0.5/0.3/0.2] optimised for conviction. Back-test: ${MODEL_METRICS.backtest_consensus_win_rate_pct}% WR on ${MODEL_METRICS.backtest_consensus_n_trades} trades (small sample — expect ~${MODEL_METRICS.live_consensus_win_rate_pct}% in live trading).`,
  },
  {
    title: "Short-horizon MAPE (1-day)",
    metric: `${MODEL_METRICS.backtest_mape_1d_pct}% error (back-test)`,
    detail: `Next-day price predictions are accurate within ~${MODEL_METRICS.backtest_mape_1d_pct}% on average across ${MODEL_METRICS.test_samples.toLocaleString()} back-test samples — usable for timing around earnings or event windows. Like all metrics, expect some degradation in live trading.`,
  },
  {
    title: "Longer-horizon MAPE (1-month)",
    metric: `${MODEL_METRICS.backtest_mape_22d_pct}% error (back-test)`,
    detail: `1-month price predictions have wider error bands (~±${MODEL_METRICS.backtest_mape_22d_pct.toFixed(0)}%) — don't anchor trades on the exact dollar target. Use the rank tier on the ticker page instead; that's the metric the ensemble is demonstrably strong at.`,
  },
  {
    title: "Top-20 vs S&P 500",
    metric: `~+${MODEL_METRICS.live_alpha_vs_sp500_pp}pp alpha target`,
    detail: `Expected outperformance vs buy-and-hold S&P 500 in live trading. ep5-heavy ensemble back-test showed +${MODEL_METRICS.backtest_alpha_vs_sp500_pp}pp on ${MODEL_METRICS.test_trading_days} days; shrunk to ~+${MODEL_METRICS.live_alpha_vs_sp500_pp}pp realistically.`,
  },
  {
    title: "Data coverage per forecast",
    metric: `${MODEL_METRICS.n_features} signals`,
    detail: `Each prediction ingests ${MODEL_METRICS.n_features} features: OHLCV, 15 technicals, 27 SEC financials, 32-dim news-sentiment PCA, 15 macro inputs, earnings surprises, insider flow, and calendar events. (Note: ~32 sentiment features don't make the model's top-20 importance list — the real signal comes from price, technicals, and financials.)`,
  },
]

export function Strengths() {
  return (
    <section className="px-4 py-24">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            What the Model Does Well
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-text-secondary md:text-base">
            Six measurable strengths. Headline numbers are <strong>live-trading
            targets</strong> — derived from back-test results then shrunk for
            realistic degradation (transaction costs, overfitting, regime
            shift). Back-test origin numbers are in the detail text. Every
            number here is auditable against the shipped checkpoints.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="mt-14 rounded-card border border-success/20 bg-success/[0.03] p-6 md:p-8"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-success" />
            <h3 className="font-heading text-lg font-semibold text-success">
              Where the ensemble excels
            </h3>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-x-8 gap-y-6 md:grid-cols-2">
            {strengths.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 6 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 + i * 0.05, duration: 0.3, ease: "easeOut" }}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-sm font-medium text-text-primary">{c.title}</p>
                  <span className="shrink-0 font-mono text-xs font-medium text-success">
                    {c.metric}
                  </span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-text-muted">
                  {c.detail}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.3, ease: "easeOut" }}
          className="mt-8 flex items-start gap-2 rounded-card border border-border-subtle bg-bg-surface/40 px-5 py-4"
        >
          <Info className="size-4 shrink-0 text-text-secondary mt-0.5" />
          <p className="text-xs leading-relaxed text-text-muted">
            <strong className="text-text-secondary">How to use this:</strong>{" "}
            treat PredictaMarket as a ranking + conviction filter. Use the Top
            Picks list to source ideas, check Alpha Signals for the tightest
            consensus, and validate with your own research. Live-target Sharpe
            of ~{MODEL_METRICS.live_top20_sharpe.toFixed(1)} matches hedge-fund
            median on public equity — this is solid, not supernatural.
            Back-test performance on a single test window does not guarantee
            future results. This is not investment advice.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
