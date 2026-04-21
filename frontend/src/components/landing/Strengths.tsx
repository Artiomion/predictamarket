"use client"

import { motion } from "framer-motion"
import { CheckCircle2, XCircle, Info } from "lucide-react"

/**
 * Honest capabilities matrix — where the ensemble excels vs where it doesn't.
 *
 * The copy deliberately calls out weaknesses. Institutional investors evaluate
 * quant models on this exact dimension: can the team name the edge and the
 * limits? Fake marketing claims like "95% accuracy on all horizons" get you
 * written off immediately. Honest framing is a trust signal.
 */
const capabilities = {
  strengths: [
    {
      title: "Relative ranking (346 stocks)",
      metric: "Sharpe 1.45",
      detail:
        "The model's core competency. Top-20 daily rebalance returned +19.2% vs S&P 500's +7.7% over 23 trading days in back-test.",
    },
    {
      title: "3-model consensus filter",
      metric: "63% win rate",
      detail:
        "When all 3 ensemble checkpoints (ep2+ep4+ep5) agree that the 80% CI bottom is above current price, the signal backtests at Sharpe 8.15 across 27 trades.",
    },
    {
      title: "Short-horizon MAPE (1-day)",
      metric: "4.78% error",
      detail:
        "Next-day price predictions are accurate within ~5% on average — usable for directional trade timing.",
    },
  ],
  limitations: [
    {
      title: "Single-day direction (up/down)",
      metric: "~50% DirAcc",
      detail:
        "Binary up/down prediction at 1-day horizon is no better than a coin flip. Don't use the signal as a standalone 'will it go up tomorrow?' indicator.",
    },
    {
      title: "Long-horizon absolute prices",
      metric: "±12% at 1-month",
      detail:
        "The 1-month median-absolute-error of 12.5% is too wide to anchor trades on a specific target price. Use the rank tier, not the dollar figure.",
    },
    {
      title: "Short / SELL signals",
      metric: "Backtest: loss",
      detail:
        "Bottom-20 short strategy loses money in back-test. We show avoidance signals but do not recommend shorting based on them.",
    },
  ],
}

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
            Every AI trading tool claims high accuracy on everything. This one
            doesn&apos;t. Here&apos;s an honest map of where the ensemble adds
            value — and where it shouldn&apos;t be trusted.
          </p>
        </motion.div>

        <div className="mt-14 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Strengths column */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="rounded-card border border-success/20 bg-success/[0.03] p-6"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-5 text-success" />
              <h3 className="font-heading text-lg font-semibold text-success">
                Where it excels
              </h3>
            </div>
            <div className="mt-5 space-y-5">
              {capabilities.strengths.map((c, i) => (
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
                  <p className="mt-1 text-xs leading-relaxed text-text-muted">{c.detail}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Limitations column */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="rounded-card border border-warning/20 bg-warning/[0.03] p-6"
          >
            <div className="flex items-center gap-2">
              <XCircle className="size-5 text-warning" />
              <h3 className="font-heading text-lg font-semibold text-warning">
                Known limitations
              </h3>
            </div>
            <div className="mt-5 space-y-5">
              {capabilities.limitations.map((c, i) => (
                <motion.div
                  key={c.title}
                  initial={{ opacity: 0, y: 6 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 + i * 0.05, duration: 0.3, ease: "easeOut" }}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-sm font-medium text-text-primary">{c.title}</p>
                    <span className="shrink-0 font-mono text-xs font-medium text-warning">
                      {c.metric}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-text-muted">{c.detail}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

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
            treat PredictaMarket as a ranking + conviction filter, not a price
            oracle. Use the Top Picks list to source ideas, check Alpha Signals
            for the tightest consensus, and validate with your own research.
            Back-test performance on a single test window does not guarantee
            future results. This is not investment advice.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
