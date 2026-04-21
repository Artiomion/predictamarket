"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { motion } from "framer-motion"
import { RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { WatchlistButton } from "@/components/features/WatchlistButton"
import { AlertButton } from "@/components/features/AlertButton"
import { Skeleton } from "@/components/ui/skeleton"
import { usePriceUpdate } from "@/lib/use-price-update"
import { PriceChange } from "@/components/ui/price-change"
import { NumberTransition } from "@/components/ui/number-transition"
import { PriceFlash } from "@/components/ui/price-flash"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { PageGuide } from "@/components/ui/page-guide"
import { MODEL_METRICS, METRIC_CAVEATS } from "@/lib/model-metrics"
import { LiveChart } from "@/components/charts/LiveChart"
import { ForecastTab } from "@/components/features/ForecastTab"
import { FinancialsTab } from "@/components/features/FinancialsTab"
import { NewsTab } from "@/components/features/NewsTab"
import { EarningsTab } from "@/components/features/EarningsTab"
import { InsidersTab } from "@/components/features/InsidersTab"
import { marketApi } from "@/lib/api"
import type { Instrument, TickerPrice } from "@/types"
import { cn } from "@/lib/utils"

function LivePrice({ ticker, initialPrice, initialChangePct }: { ticker: string; initialPrice?: number; initialChangePct?: number }) {
  const { price, changePct, flash } = usePriceUpdate(ticker, initialPrice, initialChangePct)
  if (!price) return null
  return (
    <div className="text-right">
      <PriceFlash flash={flash}>
        <NumberTransition
          value={price}
          format="price"
          className={cn(
            "text-2xl font-medium transition-colors duration-300",
            flash === "up" && "text-success",
            flash === "down" && "text-danger",
          )}
        />
      </PriceFlash>
      <PriceChange value={changePct} className="justify-end" />
    </div>
  )
}

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

  const [instrument, setInstrument] = useState<Instrument | null>(null)
  const [price, setPrice] = useState<TickerPrice | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!ticker) return
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const [instrRes, priceRes] = await Promise.all([
          marketApi.getInstrument(ticker),
          marketApi.getPrice(ticker).catch(() => null),
        ])
        setInstrument(instrRes.data)
        if (priceRes) setPrice(priceRes.data)
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } }).response?.status
        if (status === 429) {
          setError("Rate limit exceeded. Please wait a moment and try again.")
        } else if (status === 404) {
          setError("Ticker not found")
        } else {
          setError("Failed to load ticker data")
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [ticker])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-start gap-4">
          <Skeleton className="size-12 rounded-card" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-4 w-40" />
            <div className="flex gap-2"><Skeleton className="h-5 w-20" /><Skeleton className="h-5 w-16" /></div>
          </div>
          <div className="ml-auto space-y-2 text-right">
            <Skeleton className="h-8 w-28 ml-auto" />
            <Skeleton className="h-4 w-16 ml-auto" />
          </div>
        </div>
        <Skeleton className="h-[400px] rounded-card" />
      </div>
    )
  }

  if (error || !instrument) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <h2 className="font-heading text-2xl font-semibold">{error || "Ticker not found"}</h2>
          <p className="mt-2 text-sm text-text-secondary">
            {error?.includes("Rate limit") ? "You're browsing too fast" : `"${ticker}" is not in the S&P 500 prediction set`}
          </p>
          <Button variant="outline" size="sm" className="mt-4 gap-1.5" onClick={() => window.location.reload()}>
            <RefreshCw className="size-3.5" /> Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-text-muted">
        <Link href="/dashboard" className="hover:text-text-secondary">Dashboard</Link>
        <span>/</span>
        <Link href="/stocks" className="hover:text-text-secondary">Stocks</Link>
        <span>/</span>
        <span className="text-text-primary font-medium">{ticker}</span>
      </nav>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-card bg-bg-elevated font-heading text-lg font-semibold text-text-secondary">
            {ticker.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <motion.h1 layoutId={`ticker-${ticker}`} className="font-mono text-xl font-semibold">{ticker}</motion.h1>
            </div>
            <p className="mt-0.5 text-sm text-text-secondary">{instrument.name}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{instrument.sector}</Badge>
              <Badge variant="outline">{instrument.exchange}</Badge>
              <Tooltip>
                <TooltipTrigger
                  type="button"
                  aria-label={`Model strength. ${METRIC_CAVEATS.ticker_chip}`}
                  className="hidden items-center gap-1.5 rounded-chip border border-success/20 bg-success/[0.06] px-2 py-0.5 font-mono text-[10px] font-medium text-success transition-colors hover:bg-success/[0.12] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success/40 md:inline-flex"
                >
                  <span
                    aria-hidden="true"
                    className="inline-block size-1.5 rounded-full bg-success"
                  />
                  Model · {MODEL_METRICS.diracc_22d_pct}% 1m DirAcc · Sharpe{" "}
                  {MODEL_METRICS.top20_sharpe.toFixed(2)}
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  {METRIC_CAVEATS.ticker_chip}
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <LivePrice ticker={ticker} initialPrice={price?.price} initialChangePct={price?.change_pct} />
          <AlertButton ticker={ticker} />
          <WatchlistButton ticker={ticker} />
        </div>
      </div>

      <PageGuide
        summary={`Everything about ${ticker} in one place — chart, AI forecast, fundamentals, news, earnings, insider trading.`}
        sections={[
          {
            title: "What this page shows",
            body: [
              "Six tabs, each answering a different question about this stock. Chart = what the price has been doing. Forecast = what the AI thinks it will do. Financials = how healthy the business is. News = what's happening right now. Earnings = when and how the company reports profits. Insiders = whether company executives are buying or selling.",
              "The green chip in the header (\"Model · 68% 1m DirAcc · Sharpe 1.45\") is the AI's overall track record — not specific to this stock.",
            ],
          },
          {
            title: "How to use it for trading",
            body: [
              "If you're new: open the Forecast tab first. Look at the AI's rank position (e.g., #280 of 346) and the predicted 1-month return. That's the headline.",
              "Want confidence? Check the 80% and 95% confidence intervals. If the lower bound is above today's price, that's a strong BUY signal.",
              "Check News for anything that might explain the prediction (earnings beat? regulatory trouble?). Cross-reference with Insider trading — heavy insider selling is a warning flag.",
              "Still unsure? Add to Watchlist with the star icon and check back in a week.",
            ],
          },
          {
            title: "Tab-by-tab quick guide",
            body: [
              "Chart — live candlesticks with volume. Good for spotting technical patterns.",
              "Forecast — AI's prediction for the next 22 trading days with uncertainty bands.",
              "Financials — income statement and balance sheet. Revenue, earnings, debt.",
              "News — recent articles tagged with this ticker, coloured by AI-analysed sentiment.",
              "Earnings — upcoming and past earnings reports. Beat/miss history.",
              "Insiders — SEC-filed insider buys and sells. Read as a sentiment signal.",
            ],
          },
        ]}
        glossary={[
          {
            term: "Rank #N / 346",
            definition: "Where this stock ranks among all 346 by predicted 1-month return. Lower = better.",
          },
          {
            term: "Median forecast",
            definition: "The AI's best guess. 50% chance the actual price will be above this, 50% below.",
          },
          {
            term: "80% CI",
            definition: "80% confidence interval — range the AI believes the price will fall within with 80% probability.",
          },
          {
            term: "Bottom quartile",
            definition: "This stock is in the worst 25% of the catalog by expected return. Don't buy.",
          },
        ]}
      />

      <div className="border-b border-border-subtle">
        <div className="flex gap-0 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "relative shrink-0 px-4 py-2.5 text-sm font-medium transition-colors duration-150",
                activeTab === tab.id ? "text-text-primary" : "text-text-muted hover:text-text-secondary"
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

      <div>
        {activeTab === "chart" && <LiveChart ticker={ticker} />}
        {activeTab === "forecast" && <ForecastTab ticker={ticker} />}
        {activeTab === "financials" && <FinancialsTab ticker={ticker} />}
        {activeTab === "news" && <NewsTab ticker={ticker} />}
        {activeTab === "earnings" && <EarningsTab ticker={ticker} />}
        {activeTab === "insiders" && <InsidersTab ticker={ticker} />}
      </div>
    </div>
  )
}
