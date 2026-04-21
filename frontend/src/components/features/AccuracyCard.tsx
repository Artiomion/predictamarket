"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Target, TrendingUp, BarChart3, Check, X } from "lucide-react"
import { FilterChip } from "@/components/ui/filter-chip"
import { Skeleton } from "@/components/ui/skeleton"
import { forecastApi } from "@/lib/api"
import { cn } from "@/lib/utils"

interface Prediction {
  date: string
  predicted: number
  actual: number | null
  error_pct: number | null
  signal: string | null
  was_correct: boolean | null
}

interface AccuracyData {
  ticker: string
  horizon: string
  period_days: number
  total_forecasts: number
  direction_accuracy: number | null
  mape: number | null
  win_rate: number | null
  predictions: Prediction[]
}

const horizonOptions = [
  { id: "1d", label: "1D" },
  { id: "1w", label: "1W" },
  { id: "1m", label: "1M" },
]

function MetricCard({ label, value, suffix, icon: Icon, color }: {
  label: string; value: number | null; suffix: string; icon: typeof Target; color: string
}) {
  return (
    <div className="rounded-card border border-border-subtle bg-bg-elevated/50 p-4">
      <div className="flex items-center gap-2">
        <Icon className={cn("size-4", color)} />
        <span className="text-xs text-text-muted">{label}</span>
      </div>
      <p className={cn("mt-2 font-mono text-2xl font-bold tabular-nums", color)}>
        {value != null ? `${value}${suffix}` : "—"}
      </p>
    </div>
  )
}

export function AccuracyCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<AccuracyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [horizon, setHorizon] = useState<string>("1d")

  useEffect(() => {
    setLoading(true)
    forecastApi.getAccuracy(ticker, { horizon, days: 90 })
      .then(({ data: d }) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [ticker, horizon])

  if (loading) {
    return (
      <div className="rounded-card border border-border-subtle bg-bg-surface p-5 space-y-4">
        <Skeleton className="h-5 w-40" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-20 rounded-card" />
          <Skeleton className="h-20 rounded-card" />
          <Skeleton className="h-20 rounded-card" />
        </div>
      </div>
    )
  }

  const isEmpty = !data || data.total_forecasts === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-card border border-border-subtle bg-bg-surface p-5"
    >
      {/* Header — always visible with horizon selector */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className={cn("size-4", isEmpty ? "text-text-muted" : "text-[var(--accent-from)]")} />
          <h3 className="font-heading text-sm font-medium">Forecast Accuracy</h3>
          {!isEmpty && <span className="text-xs text-text-muted">({data.total_forecasts} forecasts)</span>}
        </div>
        <FilterChip
          options={horizonOptions}
          value={horizon}
          onChange={setHorizon}
          label=""
        />
      </div>

      {isEmpty ? (
        <p className="text-sm text-text-muted">
          No accuracy data available yet. Forecasts need at least {horizon === "1d" ? "1 day" : horizon === "1w" ? "1 week" : "1 month"} of history to evaluate.
        </p>
      ) : (
      <>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <MetricCard
          label="Direction Accuracy"
          value={data.direction_accuracy}
          suffix="%"
          icon={Target}
          color={data.direction_accuracy && data.direction_accuracy >= 60 ? "text-success" : "text-text-primary"}
        />
        <MetricCard
          label="MAPE"
          value={data.mape}
          suffix="%"
          icon={BarChart3}
          color={data.mape && data.mape <= 5 ? "text-success" : "text-text-primary"}
        />
        <MetricCard
          label="Signal Win Rate"
          value={data.win_rate}
          suffix="%"
          icon={TrendingUp}
          color={data.win_rate && data.win_rate >= 60 ? "text-success" : "text-text-primary"}
        />
      </div>

      {/* Predictions table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left text-xs text-text-muted">
              <th className="pb-2 font-medium">Date</th>
              <th className="pb-2 text-right font-medium">Predicted</th>
              <th className="pb-2 text-right font-medium">Actual</th>
              <th className="pb-2 text-right font-medium">Error</th>
              <th className="pb-2 text-right font-medium">Signal</th>
              <th className="pb-2 text-center font-medium">Correct</th>
            </tr>
          </thead>
          <tbody>
            {data.predictions.slice(0, 15).map((p, i) => (
              <motion.tr
                key={p.date}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                className="border-b border-border-subtle last:border-b-0"
              >
                <td className="py-2 text-text-secondary">{new Date(p.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</td>
                <td className="py-2 text-right font-mono tabular-nums">${p.predicted.toFixed(2)}</td>
                <td className="py-2 text-right font-mono tabular-nums">{p.actual ? `$${p.actual.toFixed(2)}` : "—"}</td>
                <td className={cn("py-2 text-right font-mono tabular-nums", p.error_pct && Math.abs(p.error_pct) <= 3 ? "text-success" : "text-text-secondary")}>
                  {p.error_pct != null ? `${p.error_pct > 0 ? "+" : ""}${p.error_pct.toFixed(1)}%` : "—"}
                </td>
                <td className={cn("py-2 text-right font-mono text-xs", p.signal === "BUY" ? "text-success" : "text-text-secondary")}>
                  {p.signal === "BUY" ? "▲ BUY" : p.signal === "SELL" ? "▽ AVOID" : "—"}
                </td>
                <td className="py-2 text-center">
                  {p.was_correct === true && <Check className="mx-auto size-4 text-success" />}
                  {p.was_correct === false && <X className="mx-auto size-4 text-text-muted" />}
                  {p.was_correct == null && <span className="text-text-muted">—</span>}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}
    </motion.div>
  )
}
