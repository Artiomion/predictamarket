"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Plus, Trash2, Download, ArrowUp, ArrowDown } from "lucide-react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PriceChange } from "@/components/ui/price-change"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { mockInstruments, mockSectors } from "@/lib/mock-data"
import type { Position } from "@/types"
import { cn } from "@/lib/utils"

const SECTOR_COLORS = ["#00D4AA", "#00A3FF", "#FFB800", "#FF3366", "#6B6B80"]

interface PortfolioDetailProps {
  initialPositions: Position[]
}

export function PortfolioDetail({ initialPositions }: PortfolioDetailProps) {
  const [positions, setPositions] = useState<Position[]>(initialPositions)
  const [addOpen, setAddOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [tickerInput, setTickerInput] = useState("")
  const [qtyInput, setQtyInput] = useState("")
  const [priceInput, setPriceInput] = useState("")

  const totalValue = positions.reduce((s, p) => s + p.current_price * p.quantity, 0)
  const totalCost = positions.reduce((s, p) => s + p.avg_buy_price * p.quantity, 0)
  const totalPnl = totalValue - totalCost
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  const best = positions.length > 0 ? positions.reduce((a, b) => a.pnl_pct > b.pnl_pct ? a : b) : null
  const worst = positions.length > 0 ? positions.reduce((a, b) => a.pnl_pct < b.pnl_pct ? a : b) : null

  const suggestions = useMemo(() => {
    if (tickerInput.length < 1) return []
    const q = tickerInput.toUpperCase()
    return mockInstruments
      .filter((i) => i.ticker.includes(q) || i.name.toUpperCase().includes(q))
      .slice(0, 5)
  }, [tickerInput])

  const handleAddPosition = () => {
    const ticker = tickerInput.toUpperCase()
    const qty = parseFloat(qtyInput)
    const price = parseFloat(priceInput)
    if (!ticker || isNaN(qty) || isNaN(price) || qty <= 0 || price <= 0) return

    const newPos: Position = {
      id: crypto.randomUUID(),
      ticker,
      quantity: qty,
      avg_buy_price: price,
      current_price: price,
      pnl: 0,
      pnl_pct: 0,
    }
    setPositions([...positions, newPos])
    setTickerInput("")
    setQtyInput("")
    setPriceInput("")
    setAddOpen(false)
  }

  const handleDelete = () => {
    if (!deleteId) return
    setPositions(positions.filter((p) => p.id !== deleteId))
    setDeleteId(null)
  }

  const exportCSV = () => {
    const headers = "Ticker,Quantity,Avg Price,Current Price,P&L,P&L %\n"
    const rows = positions.map((p) =>
      `${p.ticker},${p.quantity},${p.avg_buy_price.toFixed(2)},${p.current_price.toFixed(2)},${p.pnl.toFixed(2)},${p.pnl_pct.toFixed(2)}`
    ).join("\n")
    const blob = new Blob([headers + rows], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "portfolio_positions.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button variant="gradient" size="sm" className="gap-1.5" onClick={() => setAddOpen(true)}>
          <Plus className="size-3.5" />
          Add Position
        </Button>
        {positions.length > 0 && (
          <Button variant="outline" size="sm" className="gap-1.5" onClick={exportCSV}>
            <Download className="size-3.5" />
            Export CSV
          </Button>
        )}
      </div>

      {/* Summary cards */}
      {positions.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-card border border-border-subtle bg-bg-surface px-4 py-3">
            <p className="text-xs text-text-muted">Total Value</p>
            <p className="mt-1 font-mono text-lg font-medium tabular-nums">
              ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="rounded-card border border-border-subtle bg-bg-surface px-4 py-3">
            <p className="text-xs text-text-muted">Total P&L</p>
            <div className="mt-1 flex items-baseline gap-2">
              <span className={cn("font-mono text-lg font-medium tabular-nums", totalPnl >= 0 ? "text-success" : "text-danger")}>
                {totalPnl >= 0 ? "+" : ""}${totalPnl.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
              <PriceChange value={totalPnlPct} className="text-xs" />
            </div>
          </div>
          <div className="rounded-card border border-border-subtle bg-bg-surface px-4 py-3">
            <p className="text-xs text-text-muted">Best / Worst</p>
            <div className="mt-1 flex items-center gap-3">
              {best && (
                <span className="flex items-center gap-1 text-xs">
                  <ArrowUp className="size-3 text-success" />
                  <span className="font-mono font-medium text-success">{best.ticker}</span>
                  <span className="text-text-muted">+{best.pnl_pct.toFixed(1)}%</span>
                </span>
              )}
              {worst && (
                <span className="flex items-center gap-1 text-xs">
                  <ArrowDown className="size-3 text-danger" />
                  <span className="font-mono font-medium text-danger">{worst.ticker}</span>
                  <span className="text-text-muted">+{worst.pnl_pct.toFixed(1)}%</span>
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Positions table */}
      {positions.length > 0 ? (
        <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Ticker</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Qty</th>
                <th className="hidden px-4 py-3 text-right text-xs font-medium text-text-muted sm:table-cell">Avg Price</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Current</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">P&L ($)</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">P&L (%)</th>
                <th className="px-4 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, i) => (
                <motion.tr
                  key={pos.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03, duration: 0.2 }}
                  className="border-b border-border-subtle last:border-b-0 hover:bg-bg-elevated transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link href={`/stocks/${pos.ticker}`} className="font-mono text-xs font-medium hover:text-[var(--accent-from)]">
                      {pos.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">{pos.quantity}</td>
                  <td className="hidden px-4 py-3 text-right font-mono text-xs tabular-nums text-text-secondary sm:table-cell">
                    ${pos.avg_buy_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">${pos.current_price.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={cn("font-mono text-xs tabular-nums", pos.pnl >= 0 ? "text-success" : "text-danger")}>
                      {pos.pnl >= 0 ? "+" : ""}${pos.pnl.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <PriceChange value={pos.pnl_pct} className="text-xs" />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setDeleteId(pos.id)}
                      className="rounded-button p-1 text-text-muted transition-colors hover:bg-bg-elevated hover:text-danger"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex min-h-[20vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
          <p className="text-sm text-text-muted">No positions yet. Add stocks to track them here.</p>
        </div>
      )}

      {/* Sector Allocation */}
      {mockSectors.length > 0 && positions.length > 0 && (
        <div className="rounded-card border border-border-subtle bg-bg-surface p-5">
          <h3 className="font-heading text-sm font-medium">Sector Allocation</h3>
          <div className="mt-4 flex flex-col items-center gap-6 sm:flex-row">
            <div className="h-48 w-48 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={mockSectors}
                    dataKey="percentage"
                    nameKey="sector"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    strokeWidth={0}
                  >
                    {mockSectors.map((_, i) => (
                      <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#12121A",
                      border: "1px solid rgba(255,255,255,0.06)",
                      borderRadius: "6px",
                      fontSize: "12px",
                      color: "#E8E8ED",
                    }}
                    formatter={(value) => `${Number(value).toFixed(1)}%`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2">
              {mockSectors.map((s, i) => (
                <div key={s.sector} className="flex items-center gap-2">
                  <div className="size-2.5 rounded-full" style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                  <span className="text-xs text-text-secondary">{s.sector}</span>
                  <span className="ml-auto font-mono text-xs tabular-nums text-text-muted">{s.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Add Position Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Position</DialogTitle>
            <DialogDescription>Add a stock to your portfolio.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="relative">
              <label className="mb-1.5 block text-sm text-text-secondary">Ticker</label>
              <Input
                placeholder="e.g. AAPL"
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
              />
              {suggestions.length > 0 && tickerInput.length > 0 && (
                <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-button border border-border-subtle bg-bg-surface py-1">
                  {suggestions.map((s) => (
                    <button
                      key={s.ticker}
                      onClick={() => { setTickerInput(s.ticker); }}
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors hover:bg-bg-elevated"
                    >
                      <span className="font-mono text-xs font-medium">{s.ticker}</span>
                      <span className="text-xs text-text-muted">{s.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Quantity</label>
              <Input type="number" placeholder="10" value={qtyInput} onChange={(e) => setQtyInput(e.target.value)} />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Buy Price</label>
              <Input type="number" step="0.01" placeholder="250.00" value={priceInput} onChange={(e) => setPriceInput(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button variant="gradient" onClick={handleAddPosition} disabled={!tickerInput.trim() || !qtyInput || !priceInput}>
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Position</DialogTitle>
            <DialogDescription>
              Remove {positions.find((p) => p.id === deleteId)?.ticker} from this portfolio?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Keep</Button>
            <Button variant="destructive" onClick={handleDelete}>Remove</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
