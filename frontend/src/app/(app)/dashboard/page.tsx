"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/store/auth-store"

const marketOverview = [
  { label: "S&P 500", value: 5842.01, change: 1.23 },
  { label: "VIX", value: 17.82, change: -3.45 },
  { label: "Gold", value: 2385.60, change: 0.67 },
  { label: "Oil (WTI)", value: 78.42, change: -1.12 },
] as const

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 18) return "Good afternoon"
  return "Good evening"
}

function MarketCard({ label, value, change }: { label: string; value: number; change: number }) {
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

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl font-semibold">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">
          {getGreeting()}, {user?.full_name?.split(" ")[0] || "there"}
        </p>
      </div>

      {/* Market Overview */}
      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Market Overview
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <MarketCardSkeleton key={i} />
              ))
            : marketOverview.map((item, i) => (
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

      {/* Placeholder for upcoming sections */}
      <section className="flex min-h-[40vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
        <div className="text-center">
          <p className="text-sm text-text-muted">Top Picks, Signals & News</p>
          <p className="mt-1 text-xs text-text-muted">Coming in next steps</p>
        </div>
      </section>
    </div>
  )
}
