"use client"

import { motion } from "framer-motion"
import { Calendar } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { formatCountdown } from "@/lib/formatters"
import { mockUpcomingEarnings } from "@/lib/mock-data"

export function EarningsTab({ ticker }: { ticker: string }) {
  const upcoming = mockUpcomingEarnings.filter((e) => e.ticker === ticker)

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
      {/* Upcoming */}
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Upcoming Earnings
        </h3>
        <div className="space-y-3">
          {upcoming.map((e, i) => (
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
                <div className="text-right">
                  <p className="text-xs text-text-muted">EPS Estimate</p>
                  <p className="mt-0.5 font-mono text-sm font-medium tabular-nums">
                    ${e.eps_estimate.toFixed(2)}
                  </p>
                </div>
                <Badge variant={formatCountdown(e.report_date).variant} className="font-mono text-[10px]">
                  {formatCountdown(e.report_date).label}
                </Badge>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* History placeholder */}
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Earnings History
        </h3>
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Date</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">EPS Actual</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">EPS Est.</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Surprise</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Result</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-text-muted">
                  Historical earnings data will load from API
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
