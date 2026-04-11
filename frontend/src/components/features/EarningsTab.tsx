"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Calendar } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCountdown } from "@/lib/formatters"
import { marketApi } from "@/lib/api"
import type { EarningsCalendar } from "@/types"

export function EarningsTab({ ticker }: { ticker: string }) {
  const [upcoming, setUpcoming] = useState<EarningsCalendar[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    marketApi.getEarningsUpcoming({ days: 90 })
      .then(({ data }) => {
        setUpcoming(data.filter((e) => e.ticker === ticker))
      })
      .catch(() => setUpcoming([]))
      .finally(() => setLoading(false))
  }, [ticker])

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-card" />
        ))}
      </div>
    )
  }

  if (upcoming.length === 0) {
    return (
      <div className="flex min-h-[30vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
        <div className="text-center">
          <Calendar className="mx-auto size-5 text-text-muted" />
          <p className="mt-3 text-sm text-text-muted">No earnings data available for {ticker}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Upcoming Earnings
        </h3>
        <div className="space-y-3">
          {upcoming.map((e, i) => {
            const countdown = formatCountdown(e.report_date)
            return (
              <motion.div
                key={`${e.ticker}-${e.report_date}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
                className="flex items-center justify-between rounded-card border border-border-subtle bg-bg-surface px-5 py-4"
              >
                <div className="flex items-center gap-4">
                  <div className="flex size-10 items-center justify-center rounded-button bg-bg-elevated">
                    <Calendar className="size-4 text-text-muted" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{e.name}</p>
                    <p className="mt-0.5 text-xs text-text-muted">
                      {new Date(e.report_date).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {e.eps_estimate !== null && (
                    <div className="text-right">
                      <p className="text-xs text-text-muted">EPS Estimate</p>
                      <p className="mt-0.5 font-mono text-sm font-medium tabular-nums">
                        ${e.eps_estimate.toFixed(2)}
                      </p>
                    </div>
                  )}
                  <Badge variant={countdown.variant} className="font-mono text-[10px]">
                    {countdown.label}
                  </Badge>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
