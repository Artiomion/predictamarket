"use client"

import { motion } from "framer-motion"
import { CheckCircle2, Info } from "lucide-react"
import { MODEL_METRICS } from "@/lib/model-metrics"

/**
 * Model-strength showcase — the things the ensemble is demonstrably good at.
 *
 * Each card is backed by the ep2+ep4+ep5 ensemble study on the post-Oct-2025
 * test window. Numbers come from lib/model-metrics.ts (single source of truth).
 */
const strengths = [
  {
    title: `Relative ranking (${MODEL_METRICS.n_tickers} stocks)`,
    metric: `Sharpe ${MODEL_METRICS.top20_sharpe.toFixed(2)}`,
    detail: `The model's core competency. Top-20 daily rebalance returned ${MODEL_METRICS.top20_return_display} vs S&P 500's +${MODEL_METRICS.sp500_return_pct}% over ${MODEL_METRICS.test_trading_days} trading days — hedge-fund-grade risk-adjusted return.`,
  },
  {
    title: "3-model consensus filter",
    metric: `${MODEL_METRICS.conflong_win_rate_pct}% win rate`,
    detail: `When all 3 ensemble checkpoints (ep2+ep4+ep5) agree that the 80% CI bottom is above current price, the signal backtests at Sharpe ${MODEL_METRICS.conflong_sharpe} across ${MODEL_METRICS.conflong_n_trades} trades.`,
  },
  {
    title: "1-month direction (up/down)",
    metric: `${MODEL_METRICS.diracc_22d_pct}% accuracy`,
    detail: `Ensemble DirAcc at 22-trading-day horizon is ${MODEL_METRICS.diracc_22d_pct}% across ${MODEL_METRICS.test_samples.toLocaleString()} test samples — ~34σ above a coin flip. Strong signal for "will this stock be higher or lower in a month".`,
  },
  {
    title: "Short-horizon MAPE (1-day)",
    metric: `${MODEL_METRICS.mape_1d_pct}% error`,
    detail:
      "Next-day price predictions are accurate within ~5% on average — usable for timing around earnings or event windows.",
  },
  {
    title: "Top-20 vs S&P 500",
    metric: `+${MODEL_METRICS.alpha_vs_sp500_pp}pp alpha`,
    detail: `Ensemble Top-20 daily-rebalance portfolio outperformed the S&P 500 benchmark by ${MODEL_METRICS.alpha_vs_sp500_pp} percentage points over the same test window.`,
  },
  {
    title: "Data coverage per forecast",
    metric: `${MODEL_METRICS.n_features} signals`,
    detail: `Each prediction ingests ${MODEL_METRICS.n_features} features: OHLCV, 15 technicals, 27 SEC financials, 32-dim news-sentiment PCA, 15 macro inputs, earnings surprises, insider flow, and calendar events.`,
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
            Six measurable strengths, backed by the ensemble back-test on the
            post-Oct-2025 hold-out window. Every number here is reproducible
            from the shipped checkpoints.
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
            consensus, and validate with your own research. Back-test
            performance on a single test window does not guarantee future
            results. This is not investment advice.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
