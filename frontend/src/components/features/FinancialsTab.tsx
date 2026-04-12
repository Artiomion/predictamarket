"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/store/auth-store"
import { edgarApi } from "@/lib/api"
import { formatValue } from "@/lib/formatters"
import { cn } from "@/lib/utils"

const subTabs = ["Income Statement", "Balance Sheet", "Cash Flow"] as const

export function FinancialsTab({ ticker }: { ticker: string }) {
  const tier = useAuthStore((s) => s.user?.tier ?? "free")
  const [activeSubTab, setActiveSubTab] = useState<(typeof subTabs)[number]>("Income Statement")
  const [data, setData] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (tier === "free") return
    setLoading(true)
    const fetcher = activeSubTab === "Income Statement"
      ? edgarApi.getIncome(ticker, { limit: 8 })
      : activeSubTab === "Balance Sheet"
        ? edgarApi.getBalance(ticker, { limit: 8 })
        : edgarApi.getCashFlow(ticker, { limit: 8 })

    fetcher
      .then(({ data: d }) => setData(Array.isArray(d) ? d : []))
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [ticker, activeSubTab, tier])

  if (tier === "free") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="max-w-sm rounded-card border border-border-subtle bg-bg-surface p-8 text-center">
          <Lock className="mx-auto size-8 text-text-muted" />
          <h3 className="mt-4 font-heading text-base font-medium">SEC EDGAR Reports</h3>
          <p className="mt-2 text-sm text-text-secondary">
            Income statements, balance sheets, and cash flows from SEC filings are available on Pro and Premium plans.
          </p>
          <Link href="/auth/register" className="mt-5 block">
            <Button variant="gradient" className="w-full">Upgrade to Pro</Button>
          </Link>
        </div>
      </div>
    )
  }

  const columns = data.length > 0 ? Object.keys(data[0]).filter((k) => k !== "id" && k !== "ticker") : []

  return (
    <div className="space-y-4">
      <div className="flex gap-1">
        {subTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveSubTab(tab)}
            className={cn(
              "rounded-chip px-3 py-1.5 text-xs font-medium transition-colors duration-150",
              activeSubTab === tab ? "bg-bg-elevated text-text-primary" : "text-text-muted hover:text-text-secondary"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 rounded-card" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="flex min-h-[20vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
          <p className="text-sm text-text-muted">No {activeSubTab.toLowerCase()} data available for {ticker}</p>
        </div>
      ) : (
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                {columns.map((col) => (
                  <th key={col} className="px-4 py-3 text-left text-xs font-medium text-text-muted whitespace-nowrap">
                    {col.replace(/_/g, " ")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle last:border-b-0">
                  {columns.map((col) => {
                    const val = row[col]
                    const isNum = typeof val === "number"
                    return (
                      <td key={col} className="px-4 py-2.5 whitespace-nowrap">
                        <span className={cn("text-xs", isNum ? "font-mono tabular-nums" : "text-text-secondary")}>
                          {isNum ? formatValue(val as number) : String(val ?? "—")}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
