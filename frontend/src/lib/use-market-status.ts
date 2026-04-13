"use client"

import { useState, useEffect } from "react"
import { getMarketStatus, formatCountdownCompact, type MarketPhase } from "./market-hours"

interface UseMarketStatusResult {
  phase: MarketPhase
  label: string
  nextEvent: string
  countdown: string
  nextEventTime: string // "Mon 9:30 AM ET"
}

export function useMarketStatus(): UseMarketStatusResult {
  const [status, setStatus] = useState<UseMarketStatusResult>(() => compute())

  function compute(): UseMarketStatusResult {
    const s = getMarketStatus()
    return {
      phase: s.phase,
      label: s.label,
      nextEvent: s.nextEvent,
      countdown: formatCountdownCompact(s.countdownMs),
      nextEventTime: s.nextEventTime.toLocaleString("en-US", {
        timeZone: "America/New_York",
        weekday: "short",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }) + " ET",
    }
  }

  useEffect(() => {
    const id = setInterval(() => setStatus(compute()), 1000)
    return () => clearInterval(id)
  }, [])

  return status
}
