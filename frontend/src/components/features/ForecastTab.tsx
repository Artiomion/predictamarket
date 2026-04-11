"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { ArrowRight, RefreshCw, Clock, Newspaper, Calendar, AlertTriangle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import { WaterfallChart } from "@/components/charts/WaterfallChart"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { forecastApi } from "@/lib/api"
import type { Forecast, ForecastHorizon } from "@/types"
import { cn } from "@/lib/utils"

const horizons: { id: ForecastHorizon; label: string }[] = [
  { id: "1d", label: "1D" },
  { id: "3d", label: "3D" },
  { id: "1w", label: "1W" },
  { id: "2w", label: "2W" },
  { id: "1m", label: "1M" },
]

interface ForecastTabProps {
  ticker: string
}

export function ForecastTab({ ticker }: ForecastTabProps) {
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeHorizon, setActiveHorizon] = useState<ForecastHorizon>("1m")

  // Load existing forecast on mount
  useEffect(() => {
    setLoading(true)
    setError(null)
    forecastApi.getForecast(ticker)
      .then(({ data }) => setForecast(data))
      .catch(() => setForecast(null))
      .finally(() => setLoading(false))
  }, [ticker])

  // Build new forecast
  const buildForecast = async () => {
    setBuilding(true)
    setError(null)
    try {
      const { data } = await forecastApi.createForecast(ticker)
      setForecast(data)
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } }
      if (error.response?.status === 429) {
        setError("Rate limit: 1 forecast per day on Free plan. Upgrade to Pro for 10/day.")
      } else if (error.response?.status === 404) {
        setError(`${ticker} is not in the S&P 500 prediction set`)
      } else {
        setError("Forecast took too long. Try again.")
      }
    } finally {
      setBuilding(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[360px] rounded-card" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-24 rounded-card" />
          <Skeleton className="h-24 rounded-card" />
          <Skeleton className="h-24 rounded-card" />
        </div>
      </div>
    )
  }

  // No forecast yet — show Build CTA
  if (!forecast) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="max-w-sm text-center">
          {building ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <Loader2 className="mx-auto size-8 animate-spin text-[var(--accent-from)]" />
              <p className="text-sm text-text-secondary">Running TFT model on {ticker}...</p>
              <p className="text-xs text-text-muted">This may take 5-30 seconds</p>
              {/* Indeterminate progress bar */}
              <div className="mx-auto h-1.5 w-64 overflow-hidden rounded-full bg-bg-elevated">
                <motion.div
                  className="h-full w-1/3 rounded-full bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)]"
                  animate={{ x: ["-100%", "300%"] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
            >
              <h3 className="font-heading text-lg font-semibold">
                Build AI Forecast
              </h3>
              <p className="mt-2 text-sm text-text-secondary">
                Analyze {ticker} using 107 data signals and TFT model
              </p>
              {error && (
                <p className="mt-3 text-xs text-danger">{error}</p>
              )}
              <Button
                variant="gradient"
                size="lg"
                className="mt-6 gap-2 px-8"
                onClick={buildForecast}
                disabled={building}
              >
                Build Forecast
                <ArrowRight className="size-4" />
              </Button>
            </motion.div>
          )}
        </div>
      </div>
    )
  }

  // Forecast result
  const horizonData = forecast.forecast[activeHorizon]
  const returnKey = activeHorizon === "1d" ? "predicted_return_1d" : activeHorizon === "1w" ? "predicted_return_1w" : "predicted_return_1m"
  const predictedReturn = forecast[returnKey]

  return (
    <div className="space-y-6">
      {/* Not persisted warning */}
      {!forecast.persisted && (
        <div className="flex items-center gap-2 rounded-card border border-warning/20 bg-warning/5 px-4 py-2 text-xs text-warning">
          <AlertTriangle className="size-3.5 shrink-0" />
          Forecast could not be saved to database. Results are temporary.
        </div>
      )}

      {/* Chart + Signal card */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <ForecastChart forecast={forecast} />

        <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
          <div className="flex items-center justify-between">
            <SignalBadge signal={forecast.signal} confidence={forecast.confidence} showWinRate />
            <Badge variant="secondary" className="font-mono text-[10px]">
              {forecast.ticker}
            </Badge>
          </div>

          <div className="mt-4">
            <p className="text-xs text-text-muted">Predicted return</p>
            <div className="mt-1 flex items-baseline gap-2">
              <PriceChange value={predictedReturn} className="text-2xl font-medium" />
              <span className="text-xs text-text-muted">({activeHorizon})</span>
            </div>
          </div>

          <div className="mt-4 flex gap-1">
            {horizons.map((h) => (
              <button
                key={h.id}
                onClick={() => setActiveHorizon(h.id)}
                className={cn(
                  "rounded-chip px-2.5 py-1 text-xs font-medium transition-colors duration-150",
                  activeHorizon === h.id
                    ? "bg-bg-elevated text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                {h.label}
              </button>
            ))}
          </div>

          {horizonData && (
            <div className="mt-4 space-y-1.5 border-t border-border-subtle pt-4">
              <div className="flex justify-between text-xs">
                <span className="text-text-muted">Median</span>
                <span className="font-mono tabular-nums">${horizonData.median.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-text-muted">80% CI</span>
                <span className="font-mono tabular-nums text-text-secondary">
                  ${horizonData.lower_80.toFixed(0)} — ${horizonData.upper_80.toFixed(0)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-text-muted">95% CI</span>
                <span className="font-mono tabular-nums text-text-secondary">
                  ${horizonData.lower_95.toFixed(0)} — ${horizonData.upper_95.toFixed(0)}
                </span>
              </div>
            </div>
          )}

          <div className="mt-4 space-y-1.5 border-t border-border-subtle pt-4 text-xs text-text-muted">
            <div className="flex items-center gap-1.5">
              <Clock className="size-3" />
              <span>Generated in {forecast.inference_time_s}s</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Newspaper className="size-3" />
              <span>{forecast.news_articles_used > 0 ? `Based on ${forecast.news_articles_used} articles` : "No news data available"}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="size-3" />
              <span>{new Date(forecast.forecast_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
            </div>
          </div>

          {/* Refresh button */}
          <Button
            variant="outline"
            size="sm"
            className="mt-4 w-full gap-1.5"
            onClick={buildForecast}
            disabled={building}
          >
            {building ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            {building ? "Running..." : "Refresh Forecast"}
          </Button>
        </div>
      </div>

      {/* Waterfall */}
      {forecast.variable_importance?.top_factors?.length > 0 && (
        <WaterfallChart factors={forecast.variable_importance.top_factors} />
      )}
    </div>
  )
}
