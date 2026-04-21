"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/store/auth-store"
import { TopPicks } from "@/components/features/TopPicks"
import { LatestSignals } from "@/components/features/LatestSignals"
import { MarketNews } from "@/components/features/MarketNews"
import { ModelStrengthBanner } from "@/components/features/ModelStrengthBanner"
import { MarketStatusBanner } from "@/components/ui/market-status"
import { PageGuide } from "@/components/ui/page-guide"
import { marketApi } from "@/lib/api"

// Sector proxies — each ticker must exist in our 346-ticker S&P 500 subset.
// JPM/BAC/C/V aren't in the trained set; GS is the Financials proxy.
const MARKET_TICKERS = [
  { ticker: "AAPL", label: "Mega-cap" },
  { ticker: "MSFT", label: "Tech" },
  { ticker: "GS",   label: "Financials" },
  { ticker: "CVX",  label: "Energy" },
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
    // Dashboard sector cards rely on hardcoded tickers (see MARKET_TICKERS above).
    // If any are missing from the 346-ticker catalog, they silently drop out —
    // we'd rather show 3 working cards than fail the whole dashboard.
    // If a ticker IS dropped, a dev-mode warning in the console calls it out.
    const loadPrices = async () => {
      const results = await Promise.all(
        MARKET_TICKERS.map(async ({ ticker, label }) => {
          try {
            const { data } = await marketApi.getPrice(ticker)
            return { ticker, label, value: data.price, change: data.change_pct }
          } catch {
            if (process.env.NODE_ENV !== "production") {
              console.warn(`[dashboard] ticker ${ticker} missing from catalog — update MARKET_TICKERS`)
            }
            return null
          }
        })
      )
      const valid = results.filter((r): r is MarketItem & { ticker: string } => r !== null)
      setMarketData(valid)
      setLoading(false)
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

      <PageGuide
        summary="Your daily starting point — AI-ranked stocks, market snapshot, and fresh news."
        sections={[
          {
            title: "What this page shows",
            body: [
              "The Dashboard is your home base. It combines three data streams: the AI's top stock picks for the day, a snapshot of how major sectors (tech, financials, energy, etc.) are performing right now, and the latest financial news with AI-analysed sentiment.",
              "Everything on this page refreshes automatically as fresh prices and news come in — no need to reload.",
            ],
          },
          {
            title: "How to use it for trading",
            body: [
              "Start each morning here. The Top Picks list on the left shows 5 stocks the AI thinks have the highest chance of going up over the next month. Click any ticker to see the full forecast.",
              "Use the Market Overview cards to check whether the market is up or down overall — if tech is red but your Top Pick is NVDA, that's important context.",
              "Scroll down to Market News to see what's moving the market right now, coloured by sentiment (green = positive, red = negative).",
            ],
          },
          {
            title: "What to do next",
            body: [
              "1. Scan the Top Picks → click the ticker that interests you. 2. Open the Forecast tab to see the AI's detailed prediction. 3. Check News for catalyst events. 4. Add to Watchlist to track it over time.",
            ],
          },
        ]}
        glossary={[
          {
            term: "Sharpe Ratio",
            definition: "Measures return relative to risk. Above 1.0 is good; above 2.0 is excellent; our back-test is 1.45.",
          },
          {
            term: "1m Return",
            definition: "Predicted percentage change in the stock's price over the next ~22 trading days (one month).",
          },
          {
            term: "BUY / AVOID / HOLD",
            definition: "BUY = AI expects price to rise. AVOID = expects drop (we don't recommend shorting). HOLD = no strong signal.",
          },
          {
            term: "HIGH / MEDIUM / LOW",
            definition: "Confidence in the signal. HIGH = the AI's 80% confidence interval is fully above/below the current price.",
          },
        ]}
      />

      <ModelStrengthBanner />

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
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4 }}>
          <TopPicks />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4 }}>
          <LatestSignals />
        </motion.div>
      </div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4 }}>
        <MarketNews />
      </motion.div>
    </div>
  )
}
