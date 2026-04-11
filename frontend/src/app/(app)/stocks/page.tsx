"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Search, ArrowUpDown, ChevronUp, ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { FilterChip } from "@/components/ui/filter-chip"
import { formatMarketCap } from "@/lib/formatters"
import { mockInstruments, mockPrices, mockSignals } from "@/lib/mock-data"
import type { Signal } from "@/types"
import { cn } from "@/lib/utils"

type SortField = "ticker" | "name" | "price" | "change" | "signal" | "sector" | "market_cap"
type SortDir = "asc" | "desc"

const signalFilter: { id: Signal | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "BUY", label: "BUY" },
  { id: "SELL", label: "SELL" },
  { id: "HOLD", label: "HOLD" },
]

const columns: { id: SortField; label: string; align?: "right"; hideMobile?: boolean }[] = [
  { id: "ticker", label: "Ticker" },
  { id: "name", label: "Name", hideMobile: true },
  { id: "price", label: "Price", align: "right" },
  { id: "change", label: "Change", align: "right" },
  { id: "signal", label: "Signal" },
  { id: "sector", label: "Sector", hideMobile: true },
  { id: "market_cap", label: "Mkt Cap", align: "right", hideMobile: true },
]

export default function StocksPage() {
  const [search, setSearch] = useState("")
  const [signalFilterVal, setSignalFilterVal] = useState<Signal | "all">("all")
  const [sectorFilter, setSectorFilter] = useState("all")
  const [sortField, setSortField] = useState<SortField>("market_cap")
  const [sortDir, setSortDir] = useState<SortDir>("desc")

  const sectors = useMemo(() => {
    const s = new Set(mockInstruments.map((i) => i.sector))
    return ["all", ...Array.from(s).sort()]
  }, [])

  const signalMap = useMemo(() => {
    const m: Record<string, (typeof mockSignals)[number]> = {}
    mockSignals.forEach((s) => { m[s.ticker] = s })
    return m
  }, [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    return mockInstruments
      .filter((i) => {
        if (q && !i.ticker.toLowerCase().includes(q) && !i.name.toLowerCase().includes(q)) return false
        if (signalFilterVal !== "all") {
          const sig = signalMap[i.ticker]
          if (!sig || sig.signal !== signalFilterVal) return false
        }
        if (sectorFilter !== "all" && i.sector !== sectorFilter) return false
        return true
      })
      .sort((a, b) => {
        const dir = sortDir === "asc" ? 1 : -1
        switch (sortField) {
          case "ticker": return a.ticker.localeCompare(b.ticker) * dir
          case "name": return a.name.localeCompare(b.name) * dir
          case "price": return ((mockPrices[a.ticker]?.price ?? 0) - (mockPrices[b.ticker]?.price ?? 0)) * dir
          case "change": return ((mockPrices[a.ticker]?.change_pct ?? 0) - (mockPrices[b.ticker]?.change_pct ?? 0)) * dir
          case "signal": return ((signalMap[a.ticker]?.signal ?? "").localeCompare(signalMap[b.ticker]?.signal ?? "")) * dir
          case "sector": return a.sector.localeCompare(b.sector) * dir
          case "market_cap": return (a.market_cap - b.market_cap) * dir
          default: return 0
        }
      })
  }, [search, signalFilterVal, sectorFilter, sortField, sortDir, signalMap])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDir("desc")
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-baseline gap-2">
          <h1 className="font-heading text-2xl font-semibold">S&P 500 Stocks</h1>
          <span className="text-sm text-text-muted">({filtered.length})</span>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="space-y-3">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search by ticker or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex flex-wrap gap-4">
          <FilterChip options={signalFilter} value={signalFilterVal} onChange={setSignalFilterVal} label="Signal" />
          <div className="flex items-center gap-1 overflow-x-auto">
            <FilterChip
              options={sectors.map((s) => ({ id: s, label: s === "all" ? "All" : s }))}
              value={sectorFilter}
              onChange={setSectorFilter}
              label="Sector"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle">
              {columns.map((col) => (
                <th
                  key={col.id}
                  onClick={() => toggleSort(col.id)}
                  className={cn(
                    "cursor-pointer px-4 py-3 text-xs font-medium text-text-muted transition-colors hover:text-text-secondary select-none",
                    col.align === "right" ? "text-right" : "text-left",
                    col.hideMobile && "hidden md:table-cell"
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {sortField === col.id ? (
                      sortDir === "asc" ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />
                    ) : (
                      <ArrowUpDown className="size-3 opacity-30" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence mode="popLayout">
              {filtered.length === 0 ? (
                <motion.tr
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <td colSpan={columns.length} className="px-4 py-16 text-center text-sm text-text-muted">
                    {search ? `No stocks match "${search}"` : `No stocks with ${signalFilterVal} signal`}
                  </td>
                </motion.tr>
              ) : (
                filtered.map((instrument, i) => {
                  const price = mockPrices[instrument.ticker]
                  const signal = signalMap[instrument.ticker]

                  return (
                    <motion.tr
                      key={instrument.ticker}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ delay: i * 0.03, duration: 0.2, ease: "easeOut" }}
                      className="group border-b border-border-subtle last:border-b-0 transition-colors hover:bg-bg-elevated"
                    >
                      <td className="px-4 py-3">
                        <Link href={`/stocks/${instrument.ticker}`} className="block font-mono text-xs font-medium">
                          {instrument.ticker}
                        </Link>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        <Link href={`/stocks/${instrument.ticker}`} className="block text-text-secondary">
                          {instrument.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/stocks/${instrument.ticker}`} className="block font-mono text-xs tabular-nums">
                          ${price?.price.toLocaleString("en-US", { minimumFractionDigits: 2 }) ?? "—"}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/stocks/${instrument.ticker}`} className="block">
                          {price && <PriceChange value={price.change_pct} />}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Link href={`/stocks/${instrument.ticker}`} className="block">
                          {signal ? <SignalBadge signal={signal.signal} /> : <span className="text-xs text-text-muted">—</span>}
                        </Link>
                      </td>
                      <td className="hidden px-4 py-3 text-text-secondary md:table-cell">
                        <Link href={`/stocks/${instrument.ticker}`} className="block text-xs">
                          {instrument.sector}
                        </Link>
                      </td>
                      <td className="hidden px-4 py-3 text-right md:table-cell">
                        <Link href={`/stocks/${instrument.ticker}`} className="block font-mono text-xs tabular-nums text-text-secondary">
                          {formatMarketCap(instrument.market_cap)}
                        </Link>
                      </td>
                    </motion.tr>
                  )
                })
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  )
}
