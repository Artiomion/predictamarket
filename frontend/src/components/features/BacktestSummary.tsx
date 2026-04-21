"use client"

import { motion } from "framer-motion"
import { TrendingUp, Info } from "lucide-react"
import { MODEL_METRICS } from "@/lib/model-metrics"

/**
 * Back-test summary for the Top-20 daily-rebalance strategy vs buy-and-hold S&P 500.
 *
 * Numbers sourced from MODEL_METRICS (the single-source-of-truth that
 * lib/model-metrics.ts exports). Presentation-only fields (period, names,
 * descriptions) live here; numeric metrics are referenced by name so a retrain
 * + one edit to MODEL_METRICS updates every surface that reads from it.
 *
 * We intentionally don't render a synthetic equity curve: without the per-day
 * return series in our production DB, any curve would be fabricated. Showing
 * just the endpoints (return, Sharpe, trades) is the honest representation.
 */
const BACKTEST = {
  period: "Nov 2025 — early Apr 2026",
  trading_days: MODEL_METRICS.test_trading_days,
  strategy: {
    name: "Top-20 Daily Rebalance",
    return_pct: MODEL_METRICS.backtest_top20_return_pct,
    sharpe: MODEL_METRICS.backtest_top20_sharpe,
    live_sharpe_target: MODEL_METRICS.live_top20_sharpe,
    description:
      "Long top 20 tickers each day by predicted 1-day return, equal-weight, rebalanced at close.",
  },
  benchmark: {
    name: "S&P 500 Buy & Hold",
    return_pct: MODEL_METRICS.backtest_sp500_return_pct,
    sharpe: 0.8,
    description: "Passive long position over the same window.",
  },
  consensus: {
    name: "Consensus BUY Only",
    sharpe: MODEL_METRICS.backtest_consensus_sharpe,
    win_rate: MODEL_METRICS.backtest_consensus_win_rate_pct,
    trades: MODEL_METRICS.backtest_consensus_n_trades,
    live_sharpe_target: MODEL_METRICS.live_consensus_sharpe,
    live_win_rate_target: MODEL_METRICS.live_consensus_win_rate_pct,
    description:
      "Long only when all 3 ensemble models place the 80% CI lower bound above current close.",
  },
}

export function BacktestSummary() {
  const outperformance = (BACKTEST.strategy.return_pct - BACKTEST.benchmark.return_pct).toFixed(2)

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-heading text-sm font-medium">Strategy Back-test</h3>
          <p className="mt-0.5 text-xs text-text-muted">
            3-model ensemble (ep2+ep4+ep5) · {BACKTEST.period} · {BACKTEST.trading_days} trading days
          </p>
        </div>
        <TrendingUp className="size-5 text-success" />
      </div>

      {/* Comparison rows */}
      <div className="mt-5 space-y-3">
        {/* Consensus strategy — the star of the show */}
        <div className="rounded-button border border-success/20 bg-success/5 p-3">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-xs font-medium text-success">{BACKTEST.consensus.name}</p>
              <p className="mt-0.5 text-[11px] text-text-muted">
                {BACKTEST.consensus.description}
              </p>
            </div>
          </div>
          <div className="mt-2 flex gap-4 border-t border-success/10 pt-2">
            <Metric label="Sharpe" value={BACKTEST.consensus.sharpe.toFixed(2)} hero />
            <Metric label="Win Rate" value={`${BACKTEST.consensus.win_rate.toFixed(0)}%`} />
            <Metric label="Trades" value={String(BACKTEST.consensus.trades)} muted />
          </div>
        </div>

        {/* Top-20 — diversified strategy */}
        <div className="rounded-button border border-border-subtle bg-bg-elevated/40 p-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-text-primary">{BACKTEST.strategy.name}</p>
            <span className="text-[10px] font-mono text-text-muted">
              vs S&P 500: <span className="text-success">+{outperformance} pp</span>
            </span>
          </div>
          <div className="mt-2 flex gap-4">
            <Metric
              label="Return"
              value={`+${BACKTEST.strategy.return_pct.toFixed(2)}%`}
              valueColor="text-success"
            />
            <Metric label="Sharpe" value={BACKTEST.strategy.sharpe.toFixed(2)} />
            <div className="ml-auto border-l border-border-subtle pl-4 text-right">
              <p className="text-[10px] text-text-muted">S&P 500 same period</p>
              <p className="font-mono text-xs text-text-secondary">
                +{BACKTEST.benchmark.return_pct.toFixed(2)}% · Sharpe {BACKTEST.benchmark.sharpe}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-button bg-bg-elevated/30 px-3 py-2 text-[10px] leading-relaxed text-text-muted">
        <Info className="size-3 shrink-0 mt-0.5" />
        <p>
          Single test window, not rolling walk-forward. Past performance on held-out
          data does not guarantee future results. Back-test assumes zero slippage
          and commissions; live performance will differ.
        </p>
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  hero,
  muted,
  valueColor,
}: {
  label: string
  value: string
  hero?: boolean
  muted?: boolean
  valueColor?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
      <p
        className={`mt-0.5 font-mono font-medium tabular-nums ${
          hero ? "text-xl text-success" : "text-sm"
        } ${muted ? "text-text-secondary" : valueColor || "text-text-primary"}`}
      >
        {value}
      </p>
    </motion.div>
  )
}
