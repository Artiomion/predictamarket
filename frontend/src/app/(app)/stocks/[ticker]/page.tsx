"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Star } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SignalBadge } from "@/components/ui/signal-badge"
import { StockChart } from "@/components/charts/StockChart"
import { ForecastTab } from "@/components/features/ForecastTab"
import { FinancialsTab } from "@/components/features/FinancialsTab"
import { NewsTab } from "@/components/features/NewsTab"
import { EarningsTab } from "@/components/features/EarningsTab"
import { InsidersTab } from "@/components/features/InsidersTab"
import { PriceChange } from "@/components/ui/price-change"
import { mockInstruments, mockPrices, mockSignals } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const tabs = [
  { id: "chart", label: "Chart" },
  { id: "forecast", label: "Forecast" },
  { id: "financials", label: "Financials" },
  { id: "news", label: "News" },
  { id: "earnings", label: "Earnings" },
  { id: "insiders", label: "Insiders" },
] as const

type TabId = (typeof tabs)[number]["id"]

export default function StockPage() {
  const params = useParams()
  const ticker = (params.ticker as string)?.toUpperCase()
  const [activeTab, setActiveTab] = useState<TabId>("chart")
  const [watchlisted, setWatchlisted] = useState(false)

  const instrument = mockInstruments.find((i) => i.ticker === ticker)
  const price = mockPrices[ticker]
  const signal = mockSignals.find((s) => s.ticker === ticker)

  if (!instrument || !price) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <h2 className="font-heading text-2xl font-semibold">Ticker not found</h2>
          <p className="mt-2 text-sm text-text-secondary">
            &quot;{ticker}&quot; is not in the S&P 500 prediction set
          </p>
        </div>
      </div>
    )
  }

  const toggleWatchlist = () => {
    setWatchlisted(!watchlisted)
    toast(watchlisted ? `${ticker} removed from watchlist` : `${ticker} added to watchlist`, {
      duration: 2000,
    })
  }

  return (
    <div className="space-y-6">
      {/* Stock Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          {/* Logo placeholder */}
          <div className="flex size-12 shrink-0 items-center justify-center rounded-card bg-bg-elevated font-heading text-lg font-semibold text-text-secondary">
            {ticker.charAt(0)}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-xl font-semibold">{ticker}</h1>
              {signal && (
                <SignalBadge signal={signal.signal} confidence={signal.confidence} />
              )}
            </div>
            <p className="mt-0.5 text-sm text-text-secondary">{instrument.name}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge variant="secondary">{instrument.sector}</Badge>
              <Badge variant="outline">{instrument.exchange}</Badge>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Price */}
          <div className="text-right">
            <p className="font-mono text-2xl font-medium tabular-nums">
              ${price.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
            <PriceChange value={price.change_pct} className="justify-end" />
          </div>

          {/* Watchlist */}
          <Button
            variant={watchlisted ? "default" : "outline"}
            size="icon"
            onClick={toggleWatchlist}
            className={cn(watchlisted && "text-warning bg-warning/10 border-warning/20")}
          >
            <Star className={cn("size-4", watchlisted && "fill-current")} />
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border-subtle">
        <div className="flex gap-0 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "relative shrink-0 px-4 py-2.5 text-sm font-medium transition-colors duration-150",
                activeTab === tab.id
                  ? "text-text-primary"
                  : "text-text-muted hover:text-text-secondary"
              )}
            >
              {tab.label}
              {activeTab === tab.id && (
                <motion.div
                  layoutId="stock-tab-indicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent-from)]"
                  transition={{ duration: 0.2, ease: "easeOut" }}
                />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
        >
          {activeTab === "chart" && <StockChart />}
          {activeTab === "forecast" && <ForecastTab ticker={ticker} />}
          {activeTab === "financials" && <FinancialsTab ticker={ticker} />}
          {activeTab === "news" && <NewsTab ticker={ticker} />}
          {activeTab === "earnings" && <EarningsTab ticker={ticker} />}
          {activeTab === "insiders" && <InsidersTab ticker={ticker} />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
