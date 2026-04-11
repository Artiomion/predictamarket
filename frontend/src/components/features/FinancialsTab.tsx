"use client"

import { useState } from "react"
import Link from "next/link"
import { Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/store/auth-store"
import { cn } from "@/lib/utils"

const subTabs = ["Income Statement", "Balance Sheet", "Cash Flow"] as const

const placeholderColumns: Record<string, string[]> = {
  "Income Statement": ["Period", "Revenue", "Cost of Revenue", "Gross Profit", "Operating Income", "Net Income"],
  "Balance Sheet": ["Period", "Total Assets", "Total Liabilities", "Stockholders Equity", "Cash & Equivalents"],
  "Cash Flow": ["Period", "Operating", "Investing", "Financing", "Net Change"],
}

export function FinancialsTab({ ticker }: { ticker: string }) {
  const tier = useAuthStore((s) => s.user?.tier ?? "free")
  const [activeSubTab, setActiveSubTab] = useState<(typeof subTabs)[number]>("Income Statement")

  if (tier === "free") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="max-w-sm rounded-card border border-border-subtle bg-bg-surface p-8 text-center">
          <Lock className="mx-auto size-8 text-text-muted" />
          <h3 className="mt-4 font-heading text-base font-medium">
            SEC EDGAR Reports
          </h3>
          <p className="mt-2 text-sm text-text-secondary">
            Income statements, balance sheets, and cash flows from SEC filings are available on Pro and Premium plans.
          </p>
          <Link href="/auth/register" className="mt-5 block">
            <Button variant="gradient" className="w-full">
              Upgrade to Pro
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const columns = placeholderColumns[activeSubTab]

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex gap-1">
        {subTabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveSubTab(tab)}
            className={cn(
              "rounded-chip px-3 py-1.5 text-xs font-medium transition-colors duration-150",
              activeSubTab === tab
                ? "bg-bg-elevated text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Placeholder table */}
      <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle">
              {columns.map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-medium text-text-muted">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-text-muted">
                {ticker} financial data will load from API
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
