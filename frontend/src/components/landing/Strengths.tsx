"use client"

import { motion } from "framer-motion"
import { CheckCircle2, Info } from "lucide-react"

/**
 * Model-strength showcase — the things the ensemble is demonstrably good at.
 *
 * Each card is backed by the ep2+ep4+ep5 ensemble study on the post-Oct-2024
 * test window. Numbers are conservative (point estimates, not best-of).
 */
const strengths = [
  {
    title: "Relative ranking (346 stocks)",
    metric: "Sharpe 1.45",
    detail:
      "The model's core competency. Top-20 daily rebalance returned +19.2% vs S&P 500's +7.7% over 23 trading days — hedge-fund-grade risk-adjusted return.",
  },
  {
    title: "3-model consensus filter",
    metric: "63% win rate",
    detail:
      "When all 3 ensemble checkpoints (ep2+ep4+ep5) agree that the 80% CI bottom is above current price, the signal backtests at Sharpe 8.15 across 27 trades.",
  },
  {
    title: "1-month direction (up/down)",
    metric: "68% accuracy",
    detail:
      "Ensemble DirAcc at 22-trading-day horizon is 68% across 9,200 test samples — ~34σ above a coin flip. Strong signal for \"will this stock be higher or lower in a month\".",
  },
  {
    title: "Short-horizon MAPE (1-day)",
    metric: "4.78% error",
    detail:
      "Next-day price predictions are accurate within ~5% on average — usable for timing around earnings or event windows.",
  },
  {
    title: "Top-20 vs S&P 500",
    metric: "+11.46pp alpha",
    detail:
      "Ensemble Top-20 daily-rebalance portfolio outperformed the S&P 500 benchmark by 11.46 percentage points over the same test window.",
  },
  {
    title: "Data coverage per forecast",
    metric: "107 signals",
    detail:
      "Each prediction ingests 107 features: OHLCV, 15 technicals, 27 SEC financials, 32-dim news-sentiment PCA, 15 macro inputs, earnings surprises, insider flow, and calendar events.",
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
            post-Oct-2024 hold-out window. Every number here is reproducible
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
