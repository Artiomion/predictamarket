"use client"

import { useMemo } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { SparkLine, generateSparkData } from "@/components/charts/SparkLine"
import { mockTopPicks, mockPrices } from "@/lib/mock-data"

export function TopPicks() {
  const sparkData = useMemo(
    () => mockTopPicks.map(() => generateSparkData(20)),
    []
  )

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <div className="flex items-center gap-2">
          <h2 className="font-heading text-base font-medium">Top Picks</h2>
          <Badge variant="default" className="text-[10px]">AI-Ranked</Badge>
        </div>
        <Link
          href="/top-picks"
          className="text-xs text-text-muted transition-colors hover:text-[var(--accent-from)]"
        >
          View all
        </Link>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left text-xs text-text-muted">
              <th className="px-5 py-2 font-medium">#</th>
              <th className="px-2 py-2 font-medium">Ticker</th>
              <th className="hidden px-2 py-2 font-medium sm:table-cell">Name</th>
              <th className="px-2 py-2 text-right font-medium">Price</th>
              <th className="hidden px-2 py-2 font-medium md:table-cell">7d</th>
              <th className="px-2 py-2 text-right font-medium">Return</th>
              <th className="px-5 py-2 text-right font-medium">Signal</th>
            </tr>
          </thead>
          <tbody>
            {mockTopPicks.map((pick, i) => {
              const price = mockPrices[pick.ticker]
              return (
                <motion.tr
                  key={pick.ticker}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
                  className="group border-b border-border-subtle last:border-b-0"
                >
                  <td className="px-5 py-3">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <span className="text-xs text-text-muted">{i + 1}</span>
                    </Link>
                  </td>
                  <td className="px-2 py-3">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <span className="font-mono text-xs font-medium">{pick.ticker}</span>
                    </Link>
                  </td>
                  <td className="hidden px-2 py-3 sm:table-cell">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <span className="text-text-secondary">{pick.name}</span>
                    </Link>
                  </td>
                  <td className="px-2 py-3 text-right">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <span className="font-mono text-xs tabular-nums">
                        ${price?.price.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
                      </span>
                    </Link>
                  </td>
                  <td className="hidden px-2 py-3 md:table-cell">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <SparkLine data={sparkData[i]} />
                    </Link>
                  </td>
                  <td className="px-2 py-3 text-right">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <PriceChange value={pick.predicted_return_1m} prefix="" />
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Link href={`/stocks/${pick.ticker}`} className="block">
                      <SignalBadge signal={pick.signal} confidence={pick.confidence} />
                    </Link>
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
