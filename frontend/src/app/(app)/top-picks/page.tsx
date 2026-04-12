"use client"

import { useState, useEffect, useMemo } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import { SparkLine, generateSparkData } from "@/components/charts/SparkLine"
import { forecastApi } from "@/lib/api"
import { useAuthStore } from "@/store/auth-store"
import type { TopPick } from "@/types"

export default function TopPicksPage() {
  const [picks, setPicks] = useState<TopPick[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const tier = useAuthStore((s) => s.user?.tier ?? "free")

  useEffect(() => {
    const limit = tier === "free" ? 5 : 20
    forecastApi.getTopPicks({ limit })
      .then(({ data }) => { setPicks(data); setError(false) })
      .catch(() => { setPicks([]); setError(true) })
      .finally(() => setLoading(false))
  }, [tier])

  const sparkData = useMemo(
    () => picks.map(() => generateSparkData(20)),
    [picks.length] // eslint-disable-line react-hooks/exhaustive-deps
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Top Picks</h1>
        <p className="mt-1 text-sm text-text-secondary">
          AI-ranked stocks with the highest predicted returns and confident signals
        </p>
      </div>

      <div className="rounded-card border border-border-subtle bg-bg-surface">
        <div className="flex items-center gap-2 px-5 pt-5 pb-3">
          <Badge variant="default" className="text-[10px]">AI-Ranked</Badge>
          <span className="text-xs text-text-muted">
            {tier === "free" ? "Showing top 5 (upgrade for 20)" : `Showing top ${picks.length}`}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs text-text-muted">
                <th className="px-5 py-2 font-medium">#</th>
                <th className="px-2 py-2 font-medium">Ticker</th>
                <th className="hidden px-2 py-2 font-medium sm:table-cell">Name</th>
                <th className="px-2 py-2 text-right font-medium">Price</th>
                <th className="hidden px-2 py-2 font-medium md:table-cell">7d</th>
                <th className="px-2 py-2 text-right font-medium">1m Return</th>
                <th className="px-5 py-2 text-right font-medium">Signal</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-border-subtle">
                    <td className="px-5 py-3"><Skeleton className="h-4 w-4" /></td>
                    <td className="px-2 py-3"><Skeleton className="h-4 w-12" /></td>
                    <td className="hidden px-2 py-3 sm:table-cell"><Skeleton className="h-4 w-28" /></td>
                    <td className="px-2 py-3"><Skeleton className="h-4 w-16 ml-auto" /></td>
                    <td className="hidden px-2 py-3 md:table-cell"><Skeleton className="h-4 w-20" /></td>
                    <td className="px-2 py-3"><Skeleton className="h-4 w-12 ml-auto" /></td>
                    <td className="px-5 py-3"><Skeleton className="h-4 w-14 ml-auto" /></td>
                  </tr>
                ))
              ) : error ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-sm text-danger">
                    Failed to load top picks
                  </td>
                </tr>
              ) : picks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-sm text-text-muted">
                    No top picks available yet. Forecasts need to be generated first.
                  </td>
                </tr>
              ) : (
                picks.map((pick, i) => (
                  <motion.tr
                    key={pick.ticker}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04, duration: 0.3, ease: "easeOut" }}
                    className="group border-b border-border-subtle last:border-b-0 hover:bg-bg-elevated/50 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <Link href={`/stocks/${pick.ticker}`} className="block">
                        <span className="text-xs text-text-muted">{i + 1}</span>
                      </Link>
                    </td>
                    <td className="px-2 py-3">
                      <Link href={`/stocks/${pick.ticker}`} className="block font-mono text-xs font-medium">
                        {pick.ticker}
                      </Link>
                    </td>
                    <td className="hidden px-2 py-3 sm:table-cell">
                      <Link href={`/stocks/${pick.ticker}`} className="block text-text-secondary">
                        {pick.name}
                      </Link>
                    </td>
                    <td className="px-2 py-3 text-right">
                      <Link href={`/stocks/${pick.ticker}`} className="block font-mono text-xs tabular-nums">
                        ${pick.current_close?.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
                      </Link>
                    </td>
                    <td className="hidden px-2 py-3 md:table-cell">
                      <Link href={`/stocks/${pick.ticker}`} className="block">
                        {sparkData[i] && <SparkLine data={sparkData[i]} />}
                      </Link>
                    </td>
                    <td className="px-2 py-3 text-right">
                      <Link href={`/stocks/${pick.ticker}`} className="block">
                        <PriceChange value={pick.predicted_return_1m} />
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link href={`/stocks/${pick.ticker}`} className="block">
                        <SignalBadge signal={pick.signal} confidence={pick.confidence} />
                      </Link>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
