"use client"

import { motion } from "framer-motion"
import { TrendingUp, Info } from "lucide-react"
import { MODEL_METRICS } from "@/lib/model-metrics"

/**
 * Live-target strategy card for Top Picks. Two production strategies
 * are summarised:
 *
 *   Consensus BUY Only (Alpha Signals) — ep2-heavy weights [0.5, 0.3, 0.2]
 *   Top-20 Daily Rebalance (Top Picks) — ep5-heavy weights [0.2, 0.3, 0.5]
 *
 * Each uses the ensemble configuration empirically best for its goal
 * (conviction vs ranking). See docs/MODEL.md §6 for derivation.
 */
const STRATEGIES = {
  consensus: {
    name: "Consensus BUY Only (Alpha Signals)",
    description:
      "Long only when all 3 ensemble models place the 80% CI lower bound above current close.",
    weights: MODEL_METRICS.backtest_consensus_weights,
    live_sharpe: MODEL_METRICS.live_consensus_sharpe,
    live_win_rate: MODEL_METRICS.live_consensus_win_rate_pct,
    backtest_sharpe: MODEL_METRICS.backtest_consensus_sharpe,
    backtest_win_rate: MODEL_METRICS.backtest_consensus_win_rate_pct,
    backtest_trades: MODEL_METRICS.backtest_consensus_n_trades,
  },
  top20: {
    name: "Top-20 Daily Rebalance (Top Picks)",
    description:
      "Long top 20 tickers each day by predicted 1-day return, equal-weight, rebalanced at close.",
    weights: MODEL_METRICS.backtest_top20_weights,
    live_sharpe: MODEL_METRICS.live_top20_sharpe,
    live_alpha_pp: MODEL_METRICS.live_alpha_vs_sp500_pp,
    backtest_sharpe: MODEL_METRICS.backtest_top20_sharpe,
    backtest_return: MODEL_METRICS.backtest_top20_return_pct,
    backtest_alpha: MODEL_METRICS.backtest_alpha_vs_sp500_pp,
  },
}

export function BacktestSummary() {
  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-heading text-sm font-medium">Live targets per strategy</h3>
          <p className="mt-0.5 text-xs text-text-muted">
            Shrunk from {MODEL_METRICS.test_window} back-test ·{" "}
            {MODEL_METRICS.test_trading_days} trading days · two ensemble
            configurations, one per use case
          </p>
        </div>
        <TrendingUp className="size-5 text-success" />
      </div>

      <div className="mt-5 space-y-3">
        {/* Consensus — the premium filter */}
        <div className="rounded-button border border-success/20 bg-success/5 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex-1">
              <p className="text-xs font-medium text-success">{STRATEGIES.consensus.name}</p>
              <p className="mt-0.5 text-[11px] text-text-muted">
                {STRATEGIES.consensus.description}
              </p>
            </div>
            <span
              className="shrink-0 rounded-chip border border-success/20 bg-bg-surface/40 px-1.5 py-0.5 font-mono text-[9px] text-success/80"
              title="Ensemble weights (ep2, ep4, ep5)"
            >
              {STRATEGIES.consensus.weights}
            </span>
          </div>
          <div className="mt-3 flex gap-4 border-t border-success/10 pt-3">
            <Metric
              label="Sharpe target"
              value={`~${STRATEGIES.consensus.live_sharpe.toFixed(1)}`}
              hero
            />
            <Metric
              label="WR target"
              value={`~${STRATEGIES.consensus.live_win_rate}%`}
            />
            <div className="ml-auto border-l border-border-subtle pl-4 text-right">
              <p className="text-[9px] uppercase tracking-wider text-text-muted">
                Back-test (audit only)
              </p>
              <p className="font-mono text-[10px] text-text-muted">
                Sharpe {STRATEGIES.consensus.backtest_sharpe} · WR{" "}
                {STRATEGIES.consensus.backtest_win_rate}% · N=
                {STRATEGIES.consensus.backtest_trades}
              </p>
            </div>
          </div>
        </div>

        {/* Top-20 — diversified ranking strategy */}
        <div className="rounded-button border border-border-subtle bg-bg-elevated/40 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-text-primary">{STRATEGIES.top20.name}</p>
            <span
              className="shrink-0 rounded-chip border border-border-subtle bg-bg-surface/40 px-1.5 py-0.5 font-mono text-[9px] text-text-muted"
              title="Ensemble weights (ep2, ep4, ep5)"
            >
              {STRATEGIES.top20.weights}
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-text-muted">{STRATEGIES.top20.description}</p>
          <div className="mt-3 flex gap-4 border-t border-border-subtle pt-3">
            <Metric
              label="Sharpe target"
              value={`~${STRATEGIES.top20.live_sharpe.toFixed(1)}`}
              valueColor="text-success"
            />
            <Metric
              label="Alpha vs S&P"
              value={`~+${STRATEGIES.top20.live_alpha_pp}pp`}
              valueColor="text-success"
            />
            <div className="ml-auto border-l border-border-subtle pl-4 text-right">
              <p className="text-[9px] uppercase tracking-wider text-text-muted">
                Back-test (audit only)
              </p>
              <p className="font-mono text-[10px] text-text-muted">
                Sharpe {STRATEGIES.top20.backtest_sharpe} · Return +
                {STRATEGIES.top20.backtest_return.toFixed(1)}% · +
                {STRATEGIES.top20.backtest_alpha}pp vs S&P
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-button bg-bg-elevated/30 px-3 py-2 text-[10px] leading-relaxed text-text-muted">
        <Info className="size-3 shrink-0 mt-0.5" />
        <p>
          Live targets are the numbers we commit to delivering. They are derived by
          applying heuristic shrinkage to back-test results (accounting for small
          sample, transaction costs, overfitting, regime shift, data-snooping bias).
          Back-test raw numbers shown only for auditability — they will NOT repeat
          verbatim in live trading. Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  hero,
  valueColor,
}: {
  label: string
  value: string
  hero?: boolean
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
        } ${valueColor || "text-text-primary"}`}
      >
        {value}
      </p>
    </motion.div>
  )
}
