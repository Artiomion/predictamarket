"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/store/auth-store"
import { TopPicks } from "@/components/features/TopPicks"
import { LatestSignals } from "@/components/features/LatestSignals"
import { MarketNews } from "@/components/features/MarketNews"
import { MarketStatusBanner } from "@/components/ui/market-status"
import { marketApi } from "@/lib/api"

const MARKET_TICKERS = [
  { ticker: "AAPL", label: "S&P 500" },
  { ticker: "MSFT", label: "Tech" },
  { ticker: "JPM", label: "Financials" },
  { ticker: "CVX", label: "Energy" },
]

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 18) return "Good afternoon"
  return "Good evening"
}

interface MarketItem {
  label: string
  value: number
  change: number
}

function MarketCard({ label, value, change }: MarketItem) {
  return (
    <div className="flex items-center justify-between rounded-card border border-border-subtle bg-bg-surface px-4 py-3">
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className="mt-0.5 font-mono text-sm font-medium tabular-nums">
          {value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
      </div>
      <PriceChange value={change} />
    </div>
  )
}

function MarketCardSkeleton() {
  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface px-4 py-3">
      <Skeleton className="h-3 w-16" />
      <Skeleton className="mt-2 h-4 w-24" />
    </div>
  )
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const [loading, setLoading] = useState(true)
  const [marketData, setMarketData] = useState<MarketItem[]>([])

  useEffect(() => {
    const loadPrices = async () => {
      try {
        const results = await Promise.all(
          MARKET_TICKERS.map(async ({ ticker, label }) => {
            try {
              const { data } = await marketApi.getPrice(ticker)
              return { label, value: data.price, change: data.change_pct }
            } catch {
              return null
            }
          })
        )
        setMarketData(results.filter((r): r is MarketItem => r !== null))
      } catch {
        // Fallback to empty
      } finally {
        setLoading(false)
      }
    }
    loadPrices()
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">
          {getGreeting()}, {user?.full_name?.split(" ")[0] || "there"}
        </p>
      </div>

      <MarketStatusBanner />

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Market Overview
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <MarketCardSkeleton key={i} />
              ))
            : marketData.map((item, i) => (
                <motion.div
                  key={item.label}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
                >
                  <MarketCard {...item} />
                </motion.div>
              ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
        <TopPicks />
        <LatestSignals />
      </div>

      <MarketNews />
    </div>
  )
}
