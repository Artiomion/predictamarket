"use client"

import { motion } from "framer-motion"
import { TrendingUp, BarChart3, Zap, Trophy, Info } from "lucide-react"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { MODEL_METRICS, METRIC_CAVEATS } from "@/lib/model-metrics"

/**
 * Compact hero strip on the Dashboard. Shows *expected live* targets as
 * primary numbers — NOT raw back-test values. Each tooltip expands the
 * live number into its back-test origin and the shrinkage rationale, so
 * users can see the source if they want, but the headline promise is
 * realistic.
 *
 * Numbers live in lib/model-metrics.ts (single source of truth).
 */
const metrics = [
  {
    icon: TrendingUp,
    label: "Top-20 Sharpe target",
    value: `~${MODEL_METRICS.live_top20_sharpe.toFixed(1)}`,
    detail: "Hedge-fund-grade risk-adjusted return (live target)",
    tooltip: METRIC_CAVEATS.live_sharpe,
  },
  {
    icon: BarChart3,
    label: "Top-20 back-test return",
    value: MODEL_METRICS.backtest_top20_return_display,
    detail: `ep5-heavy ensemble · ${MODEL_METRICS.test_trading_days} trading days`,
    // Explicitly a back-test number — this card is the one place we show a
    // raw historical figure because it's the most concrete "here's what
    // the strategy did" claim. Live target is expressed via the Sharpe
    // metric next to it.
    tooltip: `Back-test ${MODEL_METRICS.test_window}: Top-20 daily rebalance returned ${MODEL_METRICS.backtest_top20_return_display} vs S&P 500 +${MODEL_METRICS.backtest_sp500_return_pct}% over the same window (+${MODEL_METRICS.backtest_alpha_vs_sp500_pp}pp alpha). Live performance will differ — this is historical hold-out data, not a forward promise.`,
  },
  {
    icon: Trophy,
    label: "Consensus win rate",
    value: `~${MODEL_METRICS.live_consensus_win_rate_pct}%`,
    detail: `3-model agreement filter · Sharpe ~${MODEL_METRICS.live_consensus_sharpe.toFixed(1)}`,
    tooltip: METRIC_CAVEATS.live_consensus_wr,
  },
  {
    icon: Zap,
    label: "Alpha vs S&P 500",
    value: `~+${MODEL_METRICS.live_alpha_vs_sp500_pp}pp`,
    detail: "Outperformance target vs buy-and-hold",
    tooltip: METRIC_CAVEATS.live_alpha,
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
          Expected live performance · hover any metric for source
        </p>
        <h2
          id="model-strength-heading"
          className="mt-1 font-heading text-lg font-semibold text-text-primary md:text-xl"
        >
          Hedge-fund-grade edge on public equity
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
