"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Briefcase, Plus, TrendingUp, TrendingDown, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PriceChange } from "@/components/ui/price-change"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { PortfolioDetail } from "@/components/features/PortfolioDetail"
import { PageGuide } from "@/components/ui/page-guide"
import { portfolioApi } from "@/lib/api"
import type { Portfolio } from "@/types"

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDesc, setNewDesc] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    portfolioApi.getPortfolios()
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setPortfolios(list)
        if (list.length > 0) setExpanded(list[0].id)
      })
      .catch(() => setPortfolios([]))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      const { data } = await portfolioApi.createPortfolio({ name: newName.trim(), description: newDesc.trim() || undefined })
      setPortfolios([...portfolios, data])
      setExpanded(data.id)
      setNewName("")
      setNewDesc("")
      setDialogOpen(false)
      toast.success(`Portfolio "${data.name}" created`)
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } }
      if (error.response?.status === 403) {
        toast.error("Upgrade to Pro to create more portfolios")
      }
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setDeleting(true)
    try {
      await portfolioApi.deletePortfolio(deleteId)
      setPortfolios(portfolios.filter((p) => p.id !== deleteId))
      if (expanded === deleteId) setExpanded(null)
      toast.success("Portfolio deleted")
    } catch {
      toast.error("Failed to delete portfolio")
    } finally {
      setDeleting(false)
      setDeleteId(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-8 w-36" />
        </div>
        <Skeleton className="h-24 rounded-card" />
        <Skeleton className="h-24 rounded-card" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">Portfolio</h1>
        {portfolios.length > 0 && (
          <Button variant="gradient" size="sm" className="gap-1.5" onClick={() => setDialogOpen(true)}>
            <Plus className="size-3.5" />
            Create Portfolio
          </Button>
        )}
      </div>

      <PageGuide
        summary="Track what you own and how it's performing."
        sections={[
          {
            title: "What this page shows",
            body: [
              "Your own portfolio — stocks you own, at what price you bought them, and the current unrealized profit or loss. Track multiple portfolios (e.g., \"Long-term\", \"Speculative\", \"401k\") separately.",
              "Nothing is shared with the AI training pipeline. Your holdings are private, server-side only.",
            ],
          },
          {
            title: "How to use it",
            body: [
              "Create a portfolio → add positions (ticker + quantity + buy price) → the system computes P&L using live prices. No broker integration; you enter everything manually.",
              "Use this to see which of your positions the AI currently flags as BUY, AVOID, or HOLD. It's a reality-check against your own convictions.",
              "You can also log transactions (buys/sells) over time to build a real track record.",
            ],
          },
          {
            title: "Tier limits",
            body: [
              "Free: 1 portfolio, 10 positions max. Pro: 5 portfolios, unlimited positions. Premium: 10 portfolios + CSV export.",
            ],
          },
        ]}
        glossary={[
          {
            term: "Unrealized P&L",
            definition: "Profit/loss if you sold everything right now. \"Paper\" gain or loss.",
          },
          {
            term: "Realized P&L",
            definition: "Profit/loss from positions you've already closed. Actual money made or lost.",
          },
          {
            term: "Sector allocation",
            definition: "% of your portfolio in each sector. Helps spot concentration risk.",
          },
        ]}
      />

      {portfolios.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex min-h-[50vh] items-center justify-center"
        >
          <div className="max-w-sm text-center">
            <Briefcase className="mx-auto size-12 text-text-muted" />
            <h2 className="mt-5 font-heading text-lg font-semibold">Start tracking your investments</h2>
            <p className="mt-2 text-sm text-text-secondary leading-relaxed">
              Create a portfolio to monitor performance, analyze sectors, and export reports.
            </p>
            <Button variant="gradient" className="mt-6 gap-1.5" onClick={() => setDialogOpen(true)}>
              <Plus className="size-4" /> Create Portfolio
            </Button>
          </div>
        </motion.div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence>
            {portfolios.map((portfolio, i) => {
              const isExpanded = expanded === portfolio.id
              const isPositive = (portfolio.total_pnl ?? 0) >= 0

              return (
                <motion.div
                  key={portfolio.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
                  className="group rounded-card border border-border-subtle bg-bg-surface transition-colors hover:border-border-hover"
                >
                  <button
                    onClick={() => setExpanded(isExpanded ? null : portfolio.id)}
                    className="flex w-full items-center justify-between px-5 py-4 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex size-9 items-center justify-center rounded-button bg-bg-elevated">
                        <Briefcase className="size-4 text-text-muted" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{portfolio.name}</p>
                        {portfolio.description && (
                          <p className="mt-0.5 text-xs text-text-muted">{portfolio.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="font-mono text-base font-medium tabular-nums">
                          ${(portfolio.total_value ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </p>
                        <div className="mt-0.5 flex items-center justify-end gap-1.5">
                          {isPositive ? <TrendingUp className="size-3 text-success" /> : <TrendingDown className="size-3 text-danger" />}
                          <PriceChange value={portfolio.total_pnl_pct} className="text-xs" />
                        </div>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteId(portfolio.id) }}
                        className="rounded-button p-1.5 text-text-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-danger/10 hover:text-danger"
                        title="Delete portfolio"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  </button>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2, ease: "easeOut" }}
                        className="overflow-hidden border-t border-border-subtle"
                      >
                        <div className="px-5 py-4">
                          <PortfolioDetail portfolioId={portfolio.id} />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Portfolio</DialogTitle>
            <DialogDescription>Track your stock positions and monitor performance.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label htmlFor="portfolio-name" className="mb-1.5 block text-sm text-text-secondary">Name</label>
              <Input id="portfolio-name" placeholder="e.g. Tech Growth" value={newName} onChange={(e) => setNewName(e.target.value)} />
            </div>
            <div>
              <label htmlFor="portfolio-desc" className="mb-1.5 block text-sm text-text-secondary">Description</label>
              <Input id="portfolio-desc" placeholder="Optional description" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button variant="gradient" onClick={handleCreate} disabled={!newName.trim()}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteId} onOpenChange={(open) => { if (!open) setDeleteId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete portfolio?</DialogTitle>
            <DialogDescription>
              All positions in this portfolio will be permanently deleted. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Keep portfolio</Button>
            <Button
              variant="outline"
              className="border-danger/30 text-danger hover:bg-danger/10"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete portfolio"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
