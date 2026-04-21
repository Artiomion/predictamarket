"use client"

import { motion } from "framer-motion"
import { TrendingUp, Target, Zap, Trophy } from "lucide-react"

/**
 * Compact hero strip that anchors the Dashboard with the ensemble's four
 * headline metrics. Uses only positive signals — Sharpe, DirAcc 22d, consensus
 * WR, and S&P 500 alpha. Tooltips add caveat text for curious users.
 *
 * Numbers are the ep2+ep4+ep5 ensemble study on the post-Oct-2024 window
 * (see docs/ENSEMBLE_NOTES.md).
 */
const metrics = [
  {
    icon: TrendingUp,
    label: "Top-20 Sharpe",
    value: "1.45",
    detail: "Hedge-fund grade risk-adjusted return",
    tooltip:
      "Top-20 daily-rebalance back-test, 3-model ensemble, 23 trading days post-Oct-2024",
  },
  {
    icon: Target,
    label: "1-month direction",
    value: "68%",
    detail: "DirAcc at 22-trading-day horizon",
    tooltip:
      "9,200 test samples, ~34σ above a coin flip. Strongest edge on multi-week drift.",
  },
  {
    icon: Trophy,
    label: "Consensus win rate",
    value: "63%",
    detail: "3-model agreement filter · Sharpe 8.15",
    tooltip:
      "When all 3 ensemble checkpoints agree that the 80% CI bottom is above current price, 27-trade back-test at Sharpe 8.15",
  },
  {
    icon: Zap,
    label: "Alpha vs S&P 500",
    value: "+11.46pp",
    detail: "Back-test outperformance",
    tooltip:
      "Top-20 daily-rebalance portfolio: +19.19% vs S&P 500 +7.73% on the same test window",
  },
]

export function ModelStrengthBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="relative overflow-hidden rounded-card border border-success/20 bg-gradient-to-br from-success/[0.04] via-bg-surface to-[var(--accent-from)]/[0.04] p-5"
    >
      {/* accent glow */}
      <div className="pointer-events-none absolute -top-24 -right-24 h-48 w-48 rounded-full bg-[radial-gradient(ellipse,rgba(0,212,170,0.08)_0%,transparent_70%)]" />

      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-success">
            Ensemble back-test · post-Oct-2024
          </p>
          <h2 className="mt-1 font-heading text-lg font-semibold text-text-primary md:text-xl">
            Why this model ranks stocks better than the benchmark
          </h2>
        </div>
      </div>

      <div className="relative mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.05, duration: 0.3 }}
            title={m.tooltip}
            className="group cursor-help"
          >
            <div className="flex items-center gap-1.5">
              <m.icon className="size-3.5 text-success" />
              <p className="text-[10px] uppercase tracking-wider text-text-muted">
                {m.label}
              </p>
            </div>
            <p className="mt-1 font-mono text-2xl font-medium text-text-primary tabular-nums">
              {m.value}
            </p>
            <p className="mt-0.5 text-[11px] leading-tight text-text-muted">
              {m.detail}
            </p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
