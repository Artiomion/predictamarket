"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Star, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { SparkLine, generateSparkData } from "@/components/charts/SparkLine"
import { mockWatchlists, mockPrices, mockSignals, mockInstruments } from "@/lib/mock-data"

export default function WatchlistPage() {
  const [items, setItems] = useState(mockWatchlists[0]?.items ?? [])
  const [tickerInput, setTickerInput] = useState("")

  const signalMap = useMemo(() => {
    const m: Record<string, (typeof mockSignals)[number]> = {}
    mockSignals.forEach((s) => { m[s.ticker] = s })
    return m
  }, [])

  const sparkMap = useMemo(
    () => Object.fromEntries(items.map((i) => [i.ticker, generateSparkData(20)])),
    [items.length] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const suggestions = useMemo(() => {
    if (tickerInput.length < 1) return []
    const q = tickerInput.toUpperCase()
    return mockInstruments
      .filter((i) => (i.ticker.includes(q) || i.name.toUpperCase().includes(q)) && !items.some((w) => w.ticker === i.ticker))
      .slice(0, 5)
  }, [tickerInput, items])

  const addTicker = (ticker: string) => {
    if (items.some((i) => i.ticker === ticker)) return
    setItems([...items, { ticker, added_at: new Date().toISOString() }])
    setTickerInput("")
    toast(`${ticker} added to watchlist`)
  }

  const removeTicker = (ticker: string) => {
    setItems(items.filter((i) => i.ticker !== ticker))
    toast(`${ticker} removed from watchlist`)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && suggestions.length > 0) {
      addTicker(suggestions[0].ticker)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-2xl font-semibold">Watchlist</h1>

      {/* Add ticker */}
      <div className="relative max-w-sm">
        <Input
          placeholder="Add ticker (e.g. AAPL)..."
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {suggestions.length > 0 && tickerInput.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-button border border-border-subtle bg-bg-surface py-1">
            {suggestions.map((s) => (
              <button
                key={s.ticker}
                onClick={() => addTicker(s.ticker)}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-bg-elevated"
              >
                <span className="font-mono text-xs font-medium">{s.ticker}</span>
                <span className="text-xs text-text-muted">{s.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Empty state */}
      {items.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex min-h-[40vh] items-center justify-center"
        >
          <div className="max-w-sm text-center">
            <Star className="mx-auto size-12 text-text-muted" />
            <h2 className="mt-5 font-heading text-lg font-semibold">
              Track stocks you&apos;re interested in
            </h2>
            <p className="mt-2 text-sm text-text-secondary leading-relaxed">
              Add stocks to your watchlist from any stock page using the &#9733; button.
            </p>
            <Link href="/stocks">
              <Button variant="gradient" className="mt-6">
                Browse Stocks
              </Button>
            </Link>
          </div>
        </motion.div>
      ) : (
        /* Watchlist table */
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Ticker</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Price</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Change</th>
                <th className="hidden px-4 py-3 text-xs font-medium text-text-muted sm:table-cell">7d</th>
                <th className="px-4 py-3 text-xs font-medium text-text-muted">Signal</th>
                <th className="px-4 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence mode="popLayout">
                {items.map((item, i) => {
                  const price = mockPrices[item.ticker]
                  const signal = signalMap[item.ticker]

                  return (
                    <motion.tr
                      key={item.ticker}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease: "easeOut" }}
                      className="group border-b border-border-subtle last:border-b-0 transition-colors hover:bg-bg-elevated"
                    >
                      <td className="px-4 py-3">
                        <Link href={`/stocks/${item.ticker}`} className="font-mono text-xs font-medium hover:text-[var(--accent-from)]">
                          {item.ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">
                        ${price?.price.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {price && <PriceChange value={price.change_pct} />}
                      </td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        {sparkMap[item.ticker] && <SparkLine data={sparkMap[item.ticker]} />}
                      </td>
                      <td className="px-4 py-3">
                        {signal ? <SignalBadge signal={signal.signal} /> : <span className="text-xs text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => removeTicker(item.ticker)}
                          className="rounded-button p-1 text-text-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-bg-elevated hover:text-danger"
                        >
                          <X className="size-3.5" />
                        </button>
                      </td>
                    </motion.tr>
                  )
                })}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
