"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ArrowRight, Clock, Newspaper, Calendar, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { WaterfallChart } from "@/components/charts/WaterfallChart"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { mockForecasts } from "@/lib/mock-data"
import type { ForecastHorizon } from "@/types"
import { cn } from "@/lib/utils"

const horizons: { id: ForecastHorizon; label: string }[] = [
  { id: "1d", label: "1D" },
  { id: "3d", label: "3D" },
  { id: "1w", label: "1W" },
  { id: "2w", label: "2W" },
  { id: "1m", label: "1M" },
]

const buildSteps = [
  "Collecting market data...",
  "Analyzing news articles...",
  "Running TFT model...",
  "Done!",
]

interface ForecastTabProps {
  ticker: string
}

export function ForecastTab({ ticker }: ForecastTabProps) {
  const forecast = mockForecasts[ticker]
  const [built, setBuilt] = useState(false)
  const [building, setBuilding] = useState(false)
  const [step, setStep] = useState(0)
  const [activeHorizon, setActiveHorizon] = useState<ForecastHorizon>("1m")

  const startBuild = useCallback(() => {
    setBuilding(true)
    setStep(0)
  }, [])

  useEffect(() => {
    if (!building) return
    if (step >= buildSteps.length) {
      setBuilding(false)
      setBuilt(true)
      return
    }
    const timer = setTimeout(() => setStep((s) => s + 1), 1000)
    return () => clearTimeout(timer)
  }, [building, step])

  if (!forecast) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
        <p className="text-sm text-text-muted">No forecast data available for {ticker}</p>
      </div>
    )
  }

  const horizonData = forecast.forecast[activeHorizon]
  const returnKey = activeHorizon === "1d" ? "predicted_return_1d" : activeHorizon === "1w" ? "predicted_return_1w" : "predicted_return_1m"
  const predictedReturn = forecast[returnKey]

  // Build Forecast screen
  if (!built) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="max-w-sm text-center">
          <AnimatePresence mode="wait">
            {!building ? (
              <motion.div
                key="cta"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <h3 className="font-heading text-lg font-semibold">
                  Build AI Forecast
                </h3>
                <p className="mt-2 text-sm text-text-secondary">
                  Analyze {ticker} using 107 data signals and TFT model
                </p>
                <Button
                  variant="gradient"
                  size="lg"
                  className="mt-6 gap-2 px-8"
                  onClick={startBuild}
                >
                  Build Forecast
                  <ArrowRight className="size-4" />
                </Button>
              </motion.div>
            ) : (
              <motion.div
                key="progress"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                className="w-full"
              >
                {/* Progress bar */}
                <div className="mx-auto h-1.5 w-64 overflow-hidden rounded-full bg-bg-elevated">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)]"
                    initial={{ width: "0%" }}
                    animate={{ width: `${(step / buildSteps.length) * 100}%` }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                  />
                </div>

                {/* Steps */}
                <div className="mt-6 space-y-2">
                  {buildSteps.map((s, i) => (
                    <motion.p
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: i < step ? 1 : i === step ? 0.6 : 0.2, x: 0 }}
                      transition={{ delay: i * 0.1, duration: 0.3 }}
                      className={cn(
                        "text-sm",
                        i < step ? "text-success" : i === step ? "text-text-primary" : "text-text-muted"
                      )}
                    >
                      {i < step ? "✓ " : ""}{s}
                    </motion.p>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    )
  }

  // Forecast result
  return (
    <div className="space-y-6">
      {/* Chart + Signal card */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        {/* Forecast chart */}
        <ForecastChart forecast={forecast} />

        {/* Signal card */}
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.4, ease: "easeOut" }}
          className="rounded-card border border-border-subtle bg-bg-surface p-5"
        >
          {/* Signal + Confidence */}
          <div className="flex items-center justify-between">
            <SignalBadge signal={forecast.signal} confidence={forecast.confidence} showWinRate />
            <Badge variant="secondary" className="font-mono text-[10px]">
              {forecast.ticker}
            </Badge>
          </div>

          {/* Predicted return */}
          <div className="mt-4">
            <p className="text-xs text-text-muted">Predicted return</p>
            <div className="mt-1 flex items-baseline gap-2">
              <PriceChange value={predictedReturn} className="text-2xl font-medium" />
              <span className="text-xs text-text-muted">({activeHorizon})</span>
            </div>
          </div>

          {/* Horizon selector */}
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

          {/* Median + CI */}
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

          {/* Meta */}
          <div className="mt-4 space-y-1.5 border-t border-border-subtle pt-4 text-xs text-text-muted">
            <div className="flex items-center gap-1.5">
              <Clock className="size-3" />
              <span>Inference: {forecast.inference_time_s}s</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Newspaper className="size-3" />
              <span>Based on {forecast.news_articles_used} articles</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="size-3" />
              <span>{new Date(forecast.forecast_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
            </div>
            {!forecast.persisted && (
              <div className="flex items-center gap-1.5 text-warning">
                <AlertTriangle className="size-3" />
                <span>Forecast not saved</span>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Waterfall */}
      <WaterfallChart factors={forecast.variable_importance.top_factors} />
    </div>
  )
}
