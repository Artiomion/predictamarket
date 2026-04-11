"use client"

import { motion } from "framer-motion"
import type { ForecastFactor } from "@/types"
import { cn } from "@/lib/utils"

interface WaterfallChartProps {
  factors: ForecastFactor[]
}

export function WaterfallChart({ factors }: WaterfallChartProps) {
  const maxWeight = Math.max(...factors.map((f) => f.weight))

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
      <h3 className="font-heading text-sm font-medium">What Moved the Prediction</h3>

      <div className="mt-4 space-y-2.5">
        {factors.map((factor, i) => {
          const pct = (factor.weight / maxWeight) * 100
          const isBullish = factor.direction === "bullish"

          return (
            <motion.div
              key={factor.name}
              initial={{ opacity: 0, x: isBullish ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1, duration: 0.3, ease: "easeOut" }}
              className="flex items-center gap-3"
            >
              {/* Label */}
              <div className="w-28 shrink-0 text-right">
                <span
                  className={cn(
                    "font-mono text-xs",
                    factor.is_estimated ? "text-text-muted" : "text-text-secondary"
                  )}
                >
                  {factor.name}
                  {factor.is_estimated && (
                    <span className="ml-1 text-[10px] opacity-60">(est.)</span>
                  )}
                </span>
              </div>

              {/* Bar */}
              <div className="flex flex-1 items-center">
                {/* Bearish bars extend left from center */}
                <div className="flex w-1/2 justify-end">
                  {!isBullish && (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: i * 0.1 + 0.2, duration: 0.4, ease: "easeOut" }}
                      className="h-5 rounded-sm bg-danger/60"
                    />
                  )}
                </div>
                {/* Center line */}
                <div className="mx-0.5 h-5 w-px bg-border-subtle" />
                {/* Bullish bars extend right from center */}
                <div className="flex w-1/2">
                  {isBullish && (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: i * 0.1 + 0.2, duration: 0.4, ease: "easeOut" }}
                      className="h-5 rounded-sm bg-success/60"
                    />
                  )}
                </div>
              </div>

              {/* Weight */}
              <span className="w-12 shrink-0 font-mono text-[10px] tabular-nums text-text-muted">
                {(factor.weight * 100).toFixed(1)}%
              </span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
