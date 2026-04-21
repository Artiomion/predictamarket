"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Search, ArrowUpDown, ChevronUp, ChevronDown, RefreshCw } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { FilterChip } from "@/components/ui/filter-chip"
import { Skeleton } from "@/components/ui/skeleton"
import { PriceChange } from "@/components/ui/price-change"
import { formatMarketCap } from "@/lib/formatters"
import { marketApi } from "@/lib/api"
import type { Instrument, TickerPrice } from "@/types"
import { cn } from "@/lib/utils"

type SortField = "ticker" | "name" | "market_cap" | "sector"
type SortDir = "asc" | "desc"

const columns: { id: SortField | "price" | "change"; label: string; align?: "right"; hideMobile?: boolean; sortable?: boolean }[] = [
  { id: "ticker", label: "Ticker", sortable: true },
  { id: "name", label: "Name", hideMobile: true, sortable: true },
  { id: "price", label: "Price", align: "right" },
  { id: "change", label: "Change", align: "right" },
  { id: "sector", label: "Sector", hideMobile: true, sortable: true },
  { id: "market_cap", label: "Mkt Cap", align: "right", hideMobile: true, sortable: true },
]

const SECTORS = [
  "all", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical",
  "Communication Services", "Industrials", "Consumer Defensive", "Energy",
  "Utilities", "Real Estate", "Basic Materials",
]

export default function StocksPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [total, setTotal] = useState(0)
  const [prices, setPrices] = useState<Record<string, TickerPrice>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [sectorFilter, setSectorFilter] = useState("all")
  const [sortField, setSortField] = useState<SortField>("market_cap")
  const [sortDir, setSortDir] = useState<SortDir>("desc")

  const fetchInstruments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Catalog covers ~347 S&P 500 tickers supported by the model. We render
      // them all in one scroll (virtualised below); filters/search fold client-side.
      const { data } = await marketApi.getInstruments({
        per_page: 500,
        search: search || undefined,
        sector: sectorFilter !== "all" ? sectorFilter : undefined,
        sort_by: sortField,
        order: sortDir,
      })
      setInstruments(data.data)
      setTotal(data.total)
    } catch {
      setError("Failed to load instruments")
    } finally {
      setLoading(false)
    }
  }, [search, sectorFilter, sortField, sortDir])

  useEffect(() => {
    const debounce = setTimeout(fetchInstruments, search ? 300 : 0)
    return () => clearTimeout(debounce)
  }, [fetchInstruments, search])

  // Fetch prices for visible instruments
  useEffect(() => {
    if (instruments.length === 0) return
    const fetchPrices = async () => {
      const priceMap: Record<string, TickerPrice> = {}
      await Promise.all(
        instruments.map(async (i) => {
          try {
            const { data } = await marketApi.getPrice(i.ticker)
            priceMap[i.ticker] = data
          } catch { /* skip */ }
        })
      )
      setPrices(priceMap)
    }
    fetchPrices()
  }, [instruments])

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
      <div>
        <div className="flex items-baseline gap-2">
          <h1 className="font-heading text-2xl font-semibold">S&P 500 Stocks</h1>
          <span className="text-sm text-text-muted">({total})</span>
        </div>
      </div>

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
          <div className="flex items-center gap-1 overflow-x-auto">
            <FilterChip
              options={SECTORS.map((s) => ({ id: s, label: s === "all" ? "All" : s }))}
              value={sectorFilter}
              onChange={setSectorFilter}
              label="Sector"
            />
          </div>
        </div>
      </div>

      {error ? (
        <div className="flex min-h-[40vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
          <div className="text-center">
            <p className="text-sm text-danger">{error}</p>
            <Button variant="outline" size="sm" className="mt-3 gap-1.5" onClick={fetchInstruments}>
              <RefreshCw className="size-3.5" /> Retry
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                {columns.map((col) => (
                  <th
                    key={col.id}
                    onClick={() => col.sortable && toggleSort(col.id as SortField)}
                    className={cn(
                      "px-4 py-3 text-xs font-medium text-text-muted transition-colors select-none",
                      col.sortable && "cursor-pointer hover:text-text-secondary",
                      col.align === "right" ? "text-right" : "text-left",
                      col.hideMobile && "hidden md:table-cell"
                    )}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && (
                        sortField === col.id ? (
                          sortDir === "asc" ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />
                        ) : (
                          <ArrowUpDown className="size-3 opacity-30" />
                        )
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-border-subtle">
                    <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                    <td className="hidden px-4 py-3 md:table-cell"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16 ml-auto" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-14 ml-auto" /></td>
                    <td className="hidden px-4 py-3 md:table-cell"><Skeleton className="h-4 w-20" /></td>
                    <td className="hidden px-4 py-3 md:table-cell"><Skeleton className="h-4 w-14 ml-auto" /></td>
                  </tr>
                ))
              ) : instruments.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-16 text-center text-sm text-text-muted">
                    {search ? `No stocks match "${search}"` : "No stocks found"}
                  </td>
                </tr>
              ) : (
                <AnimatePresence mode="popLayout">
                  {instruments.map((instrument, i) => (
                    <motion.tr
                      key={instrument.ticker}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ delay: i * 0.02, duration: 0.2, ease: "easeOut" }}
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
                          {prices[instrument.ticker] ? `$${prices[instrument.ticker].price.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—"}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/stocks/${instrument.ticker}`} className="block">
                          {prices[instrument.ticker] ? <PriceChange value={prices[instrument.ticker].change_pct} /> : <span className="text-xs text-text-muted">—</span>}
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
                  ))}
                </AnimatePresence>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
