"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { CalendarDays } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { PageGuide } from "@/components/ui/page-guide"
import { formatCountdown } from "@/lib/formatters"
import { marketApi } from "@/lib/api"
import type { EarningsCalendar } from "@/types"
import { cn } from "@/lib/utils"

export default function EarningsPage() {
  const [earnings, setEarnings] = useState<EarningsCalendar[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    marketApi.getEarningsUpcoming({ days: 90 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setEarnings(list.sort((a, b) => new Date(a.report_date).getTime() - new Date(b.report_date).getTime()))
      })
      .catch(() => setEarnings([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-card" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="font-heading text-2xl font-semibold">Earnings Calendar</h1>
        <Badge variant="secondary" className="font-mono text-[10px]">
          {earnings.length} upcoming
        </Badge>
      </div>

      <PageGuide
        summary="When each company reports its quarterly earnings — and the analyst forecast."
        sections={[
          {
            title: "What this page shows",
            body: [
              "A chronological list of upcoming earnings reports for stocks in our catalog. For each company: the reporting date, the Wall Street consensus EPS estimate, and a countdown.",
              "Companies report earnings every 3 months. The numbers they announce usually move the stock price 5–15% in the first 24 hours — up if they beat, down if they miss.",
            ],
          },
          {
            title: "How to use it for trading",
            body: [
              "Day-before earnings: decide whether to hold through the announcement (\"earnings play\") or sell/hedge to avoid the volatility. Our AI doesn't specialise in earnings events — use this as a calendar warning.",
              "After earnings: check News tab to see the actual result vs. estimate. Sudden negative sentiment after a report = possible entry for contrarians, exit for momentum followers.",
              "Patterns to watch: 3 beats in a row → strong guidance reputation. 3 misses → investor patience wearing thin.",
            ],
          },
          {
            title: "Good to know",
            body: [
              "EPS Est is the Wall Street consensus. It's what analysts expect; the company reports the actual. The delta between them (\"surprise %\") is what moves the price.",
              "Reports happen either BMO (before market open, ~8am ET) or AMC (after market close, ~4:30pm ET). Check the specific time before making any trade.",
            ],
          },
        ]}
        glossary={[
          {
            term: "EPS",
            definition: "Earnings Per Share = net profit ÷ shares outstanding. Main profitability metric investors watch.",
          },
          {
            term: "EPS Estimate",
            definition: "Consensus of Wall Street analysts predicting what the company will report.",
          },
          {
            term: "Beat / Miss",
            definition: "Actual EPS > estimate = beat (stock usually rises). Actual < estimate = miss.",
          },
          {
            term: "Surprise %",
            definition: "(Actual EPS − Estimate) ÷ Estimate × 100. Bigger surprise = bigger price reaction.",
          },
        ]}
      />

      {earnings.length === 0 ? (
        <div className="flex min-h-[40vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
          <div className="text-center">
            <CalendarDays className="mx-auto size-8 text-text-muted" />
            <p className="mt-3 text-sm text-text-muted">No upcoming earnings reports</p>
          </div>
        </div>
      ) : (
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-5 py-3 text-left text-xs font-medium text-text-muted">Ticker</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Company</th>
                <th className="hidden px-4 py-3 text-left text-xs font-medium text-text-muted sm:table-cell">Report Date</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">EPS Est.</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-text-muted">Countdown</th>
              </tr>
            </thead>
            <tbody>
              {earnings.map((e, i) => {
                const countdown = formatCountdown(e.report_date)
                const isNear = countdown.variant === "danger" || countdown.variant === "warning"
                return (
                  <motion.tr
                    key={`${e.ticker}-${e.report_date}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04, duration: 0.2, ease: "easeOut" }}
                    className={cn(
                      "border-b border-border-subtle last:border-b-0 transition-colors hover:bg-bg-elevated",
                      countdown.urgent && "bg-bg-elevated",
                      isNear && "border-l-2 border-l-warning"
                    )}
                  >
                    <td className="px-5 py-3.5">
                      <Link href={`/stocks/${e.ticker}`} className="font-mono text-xs font-medium hover:text-[var(--accent-from)]">{e.ticker}</Link>
                    </td>
                    <td className="px-4 py-3.5 text-text-secondary">{e.name}</td>
                    <td className="hidden px-4 py-3.5 text-xs text-text-muted sm:table-cell">
                      {new Date(e.report_date).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-xs tabular-nums">
                      {e.eps_estimate != null ? `$${e.eps_estimate.toFixed(2)}` : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Badge variant={countdown.variant} className={cn("font-mono text-[10px]", countdown.urgent && "animate-pulse")}>
                        {countdown.label}
                      </Badge>
                    </td>
                  </motion.tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
