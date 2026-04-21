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
import { AccuracyCard } from "@/components/features/AccuracyCard"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { WalkForwardChart } from "@/components/charts/WalkForwardChart"
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

type RankInfo = {
  total_tickers: number
  rank_1d: number | null
  rank_1w: number | null
  rank_1m: number | null
  percentile_1m: number | null
}

export function ForecastTab({ ticker }: ForecastTabProps) {
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [rank, setRank] = useState<RankInfo | null>(null)
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
    // Fetch ranking in parallel — the "what this model is actually good at"
    // context. Silent-fail: absence of rank UI shouldn't block forecast view.
    forecastApi.getTickerRank(ticker)
      .then(({ data }) => setRank(data))
      .catch(() => setRank(null))
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
                {building ? (
                  <>
                    <svg className="size-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeLinecap="round" /></svg>
                    Generating...
                  </>
                ) : (
                  <>
                    Build Forecast
                    <ArrowRight className="size-4" />
                  </>
                )}
              </Button>
            </motion.div>
          )}
        </div>
      </div>
    )
  }

  // Forecast result
  const horizonData = forecast.forecast[activeHorizon]
  // Backend only sends predicted_return_{1d,1w,1m}. For 3d/2w (and as a
  // fallback when a return field is null/stale), compute from median/current.
  const returnKey = activeHorizon === "1d" ? "predicted_return_1d"
    : activeHorizon === "1w" ? "predicted_return_1w"
    : activeHorizon === "1m" ? "predicted_return_1m"
    : null
  const rawReturn = returnKey ? forecast[returnKey] : null
  const computedReturn = horizonData && forecast.current_close
    ? ((horizonData.median / forecast.current_close) - 1) * 100
    : null
  const predictedReturn = rawReturn ?? computedReturn

  return (
    <div className="space-y-6">
      {/* Not persisted warning */}
      {forecast.persisted === false && (
        <div className="flex items-center gap-2 rounded-card border border-warning/20 bg-warning/5 px-4 py-2 text-xs text-warning">
          <AlertTriangle className="size-3.5 shrink-0" />
          Forecast could not be saved to database. Results are temporary.
        </div>
      )}

      {/* Ranking context — what the TFT is actually good at.
          Absolute price prediction has MAPE ~12% at 1M, but relative ranking
          across the 346-ticker catalog is where the model generates Sharpe 1.45.
          Showing the rank orients the user to the real signal. */}
      {rank && rank.rank_1m && (
        <RankingContext rank={rank} ticker={ticker} />
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
              <span>{forecast.news_articles_used != null && forecast.news_articles_used > 0 ? `Based on ${forecast.news_articles_used} articles` : forecast.news_articles_used === 0 ? "No news data available" : "News sentiment from database"}</span>
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

      {/* Accuracy */}
      {/* Walk-Forward */}
      <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading text-sm font-medium">Walk-Forward Analysis</h3>
            <p className="mt-0.5 text-xs text-text-muted">How the model&apos;s predictions evolved over the last 7 days</p>
          </div>
        </div>
        <WalkForwardChart ticker={ticker} />
      </div>

      {/* Accuracy */}
      <AccuracyCard ticker={ticker} />
    </div>
  )
}

/** Ranking context block — reframes the forecast tab around what the TFT
 *  actually excels at (relative ranking with Sharpe 1.45) rather than absolute
 *  price prediction (MAPE ~12% at 1M). Shown above the forecast chart. */
function RankingContext({ rank, ticker }: { rank: RankInfo; ticker: string }) {
  const r1m = rank.rank_1m!
  const total = rank.total_tickers
  const isTopDecile = r1m <= Math.ceil(total * 0.1)  // top 10%
  const isTopQuartile = r1m <= Math.ceil(total * 0.25)
  const isBottomQuartile = r1m > Math.ceil(total * 0.75)

  let tierLabel: string
  let tierColor: string
  if (isTopDecile) {
    tierLabel = "Top 10%"
    tierColor = "text-success"
  } else if (isTopQuartile) {
    tierLabel = "Top quartile"
    tierColor = "text-success"
  } else if (isBottomQuartile) {
    tierLabel = "Bottom quartile"
    tierColor = "text-danger"
  } else {
    tierLabel = "Mid-pack"
    tierColor = "text-text-secondary"
  }

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface/50 px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-text-muted">
            AI Ranking Position
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-medium text-text-primary">
              #{r1m}
            </span>
            <span className="text-sm text-text-secondary">of {total}</span>
            <span className={`ml-2 text-xs font-medium ${tierColor}`}>
              {tierLabel}
            </span>
          </div>
        </div>
        <div className="flex gap-3 text-xs">
          {rank.rank_1d && (
            <div className="text-right">
              <p className="text-text-muted">1D rank</p>
              <p className="font-mono text-text-secondary">#{rank.rank_1d}</p>
            </div>
          )}
          {rank.rank_1w && (
            <div className="text-right">
              <p className="text-text-muted">1W rank</p>
              <p className="font-mono text-text-secondary">#{rank.rank_1w}</p>
            </div>
          )}
        </div>
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-text-muted">
        <strong className="text-text-secondary">What this means:</strong> the model
        ranks {ticker} at position #{r1m} by predicted 1-month return — this is
        the metric our ensemble is strongest at (Sharpe 1.45 on Top-20 back-test).
        The dollar price forecast below is directional; 1-month median absolute
        error is ±12%, so use rank tier for conviction, not the exact target price.
      </p>
    </div>
  )
}
