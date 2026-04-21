"use client"

import { motion } from "framer-motion"
import { MODEL_METRICS } from "@/lib/model-metrics"

// Numbers pulled from lib/model-metrics.ts (single source of truth).
// Headline shows live *targets* after realistic degradation. Back-test
// context lives on the Top Picks page (BacktestSummary) for users who
// want the raw numbers.
const metrics = [
  {
    value: `~${MODEL_METRICS.live_consensus_win_rate_pct}%`,
    label: "Consensus Win Rate (live target)",
  },
  {
    value: `~${MODEL_METRICS.live_top20_sharpe.toFixed(1)}`,
    label: "Top-20 Sharpe (live target)",
  },
  {
    value: String(MODEL_METRICS.n_tickers),
    label: "S&P 500 Stocks",
  },
  {
    value: String(MODEL_METRICS.n_features),
    label: "Data Signals",
  },
] as const

export function Performance() {
  return (
    <section className="py-24 px-4">
      <div className="mx-auto max-w-6xl">
        {/* SSR-safe entrance: initial opacity 1 so the content is always
            visible even if framer's viewport detection fails (happens in
            automated browsers, throttled tabs, reduced-motion users).
            Only the subtle y-offset is animated. */}
        <motion.div
          initial={{ opacity: 1, y: 12 }}
          whileInView={{ y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Model Performance
          </h2>
          <p className="mt-3 text-text-secondary">
            Backtested on S&P 500 data from Nov 2025 — early Apr 2026 (23 trading days)
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-2 gap-8 md:grid-cols-4">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 1, y: 12 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4, ease: "easeOut" }}
              className="text-center"
            >
              <span className="font-mono text-4xl font-medium tabular-nums md:text-5xl">
                {m.value}
              </span>
              <p className="mt-2 text-sm text-text-muted">{m.label}</p>
            </motion.div>
          ))}
        </div>

        <p className="mt-12 text-center text-xs text-text-muted">
          Past performance does not guarantee future results. Single test period, not rolling.
        </p>
      </div>
    </section>
  )
}
