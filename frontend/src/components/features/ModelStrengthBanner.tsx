"use client"

import { motion } from "framer-motion"
import { TrendingUp, Target, Zap, Trophy, Info } from "lucide-react"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { MODEL_METRICS, METRIC_CAVEATS } from "@/lib/model-metrics"

/**
 * Compact hero strip that anchors the Dashboard with the ensemble's four
 * headline metrics. Tooltip bodies carry caveats (test-window size, sample
 * count) so they're reachable by touch (long-press), hover, AND keyboard
 * focus — not just desktop mouse hover like a bare `title` attr.
 *
 * Numbers live in lib/model-metrics.ts (single source of truth).
 */
const metrics = [
  {
    icon: TrendingUp,
    label: "Top-20 Sharpe",
    value: MODEL_METRICS.top20_sharpe.toFixed(2),
    detail: "Hedge-fund grade risk-adjusted return",
    tooltip: METRIC_CAVEATS.top20_sharpe,
  },
  {
    icon: Target,
    label: "1-month direction",
    value: `${MODEL_METRICS.diracc_22d_pct}%`,
    detail: "DirAcc at 22-trading-day horizon",
    tooltip: METRIC_CAVEATS.diracc_22d,
  },
  {
    icon: Trophy,
    label: "Consensus win rate",
    value: `${MODEL_METRICS.conflong_win_rate_pct}%`,
    detail: `3-model agreement filter · Sharpe ${MODEL_METRICS.conflong_sharpe}`,
    tooltip: METRIC_CAVEATS.consensus_wr,
  },
  {
    icon: Zap,
    label: "Alpha vs S&P 500",
    value: `+${MODEL_METRICS.alpha_vs_sp500_pp}pp`,
    detail: "Back-test outperformance",
    tooltip: METRIC_CAVEATS.alpha,
  },
]

export function ModelStrengthBanner() {
  return (
    <motion.section
      aria-labelledby="model-strength-heading"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="relative overflow-hidden rounded-card border border-success/20 bg-gradient-to-br from-success/[0.04] via-bg-surface to-[var(--accent-from)]/[0.04] p-5"
    >
      {/* accent glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-24 -right-24 h-48 w-48 rounded-full bg-[radial-gradient(ellipse,rgba(0,212,170,0.08)_0%,transparent_70%)]"
      />

      <div className="relative">
        <p className="text-[10px] font-medium uppercase tracking-wider text-success">
          Ensemble back-test · {MODEL_METRICS.test_window}
        </p>
        <h2
          id="model-strength-heading"
          className="mt-1 font-heading text-lg font-semibold text-text-primary md:text-xl"
        >
          Why this model outperforms the benchmark
        </h2>
      </div>

      <div className="relative mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.05, duration: 0.3 }}
          >
            <Tooltip>
              <TooltipTrigger
                className="group -m-1 rounded-md p-1 text-left transition-colors hover:bg-bg-elevated/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/40"
                aria-label={`${m.label}: ${m.value}. ${m.tooltip}`}
              >
                <div className="flex items-center gap-1.5">
                  <m.icon aria-hidden="true" className="size-3.5 text-success" />
                  <p className="text-[10px] uppercase tracking-wider text-text-muted">
                    {m.label}
                  </p>
                  {/* Info indicator tells the user the number has more context
                      behind it. Without it, tooltip-triggers look static —
                      hover/focus affordance was the only cue and that's
                      invisible on touch screens. */}
                  <Info
                    aria-hidden="true"
                    className="size-3 text-text-muted opacity-60 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                  />
                </div>
                <p className="mt-1 font-mono text-2xl font-medium text-text-primary tabular-nums">
                  {m.value}
                </p>
                <p className="mt-0.5 text-[11px] leading-tight text-text-muted">
                  {m.detail}
                </p>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">{m.tooltip}</TooltipContent>
            </Tooltip>
          </motion.div>
        ))}
      </div>
    </motion.section>
  )
}
