"use client"

import { motion } from "framer-motion"
import { MODEL_METRICS } from "@/lib/model-metrics"

// Numbers pulled from lib/model-metrics.ts (single source of truth — also
// sourced by Strengths, ModelStrengthBanner, landing hero stats, Top Picks).
//
// Previous incarnation used a requestAnimationFrame count-up gated by an
// IntersectionObserver. Both were fragile: observer missed fast scrolls,
// RAF throttled in background tabs → users saw stuck-at-zero stats. The
// numbers themselves are the product here; a cosmetic count-up isn't worth
// that failure mode.
const metrics = [
  {
    value: `${MODEL_METRICS.conflong_win_rate_pct}%`,
    label: "Consensus Win Rate",
  },
  {
    value: `${MODEL_METRICS.top20_return_pct.toFixed(1)}%`,
    label: "Top-20 Return",
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
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Model Performance
          </h2>
          <p className="mt-3 text-text-secondary">
            Backtested on S&P 500 data from Nov 2024 — Apr 2026
          </p>
        </motion.div>

        <div className="mt-16 grid grid-cols-2 gap-8 md:grid-cols-4">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
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
