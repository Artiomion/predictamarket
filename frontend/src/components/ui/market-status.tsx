"use client"

import { motion } from "framer-motion"
import { Clock, TrendingUp, Moon, Sun } from "lucide-react"
import { useMarketStatus } from "@/lib/use-market-status"
import { cn } from "@/lib/utils"
import type { MarketPhase } from "@/lib/market-hours"

const phaseConfig: Record<MarketPhase, {
  dotColor: string
  textColor: string
  bgColor: string
  borderColor: string
  icon: typeof Clock
  pulse: boolean
}> = {
  open: {
    dotColor: "bg-success",
    textColor: "text-success",
    bgColor: "bg-success/5",
    borderColor: "border-success/20",
    icon: TrendingUp,
    pulse: true,
  },
  "pre-market": {
    dotColor: "bg-warning",
    textColor: "text-warning",
    bgColor: "bg-warning/5",
    borderColor: "border-warning/20",
    icon: Sun,
    pulse: false,
  },
  "after-hours": {
    dotColor: "bg-warning",
    textColor: "text-warning",
    bgColor: "bg-warning/5",
    borderColor: "border-warning/20",
    icon: Moon,
    pulse: false,
  },
  closed: {
    dotColor: "bg-danger",
    textColor: "text-danger",
    bgColor: "bg-danger/5",
    borderColor: "border-danger/20",
    icon: Clock,
    pulse: false,
  },
}

/**
 * Compact badge for Header — dot + label + countdown.
 */
export function MarketStatusBadge() {
  const { phase, label, nextEvent, countdown } = useMarketStatus()
  const config = phaseConfig[phase]

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className="relative flex size-2">
        <span className={cn("absolute inline-flex h-full w-full rounded-full", config.dotColor, config.pulse && "animate-ping opacity-75")} />
        <span className={cn("relative inline-flex size-2 rounded-full", config.dotColor)} />
      </span>
      <span className={cn("font-medium", config.textColor)}>{label}</span>
      {phase !== "open" && (
        <span className="text-text-muted">
          {" "}· {nextEvent} in {countdown}
        </span>
      )}
      {phase === "open" && (
        <span className="text-text-muted">
          {" "}· {nextEvent} in {countdown}
        </span>
      )}
    </div>
  )
}

/**
 * Full banner for Dashboard — card with icon, status, countdown, next event time.
 */
export function MarketStatusBanner() {
  const { phase, label, nextEvent, countdown, nextEventTime } = useMarketStatus()
  const config = phaseConfig[phase]
  const Icon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "flex items-center justify-between rounded-card border px-5 py-3",
        config.bgColor,
        config.borderColor,
      )}
    >
      <div className="flex items-center gap-3">
        <div className={cn("flex items-center justify-center rounded-button p-1.5", config.bgColor)}>
          <Icon className={cn("size-4", config.textColor)} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className={cn("absolute inline-flex h-full w-full rounded-full", config.dotColor, config.pulse && "animate-ping opacity-75")} />
              <span className={cn("relative inline-flex size-2 rounded-full", config.dotColor)} />
            </span>
            <span className={cn("text-sm font-medium", config.textColor)}>{label}</span>
          </div>
          <p className="mt-0.5 text-xs text-text-muted">
            {nextEvent} · {nextEventTime}
          </p>
        </div>
      </div>

      <div className="text-right">
        <p className={cn("font-mono text-lg font-semibold tabular-nums", config.textColor)}>
          {countdown}
        </p>
        <p className="text-[10px] text-text-muted uppercase tracking-wider">
          {phase === "open" ? "until close" : "until " + nextEvent.toLowerCase()}
        </p>
      </div>
    </motion.div>
  )
}
