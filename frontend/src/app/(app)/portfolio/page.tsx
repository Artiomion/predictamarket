"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Briefcase, Plus, TrendingUp, TrendingDown } from "lucide-react"
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
import { PortfolioDetail } from "@/components/features/PortfolioDetail"
import { mockPortfolios, mockPositions } from "@/lib/mock-data"
import type { Portfolio } from "@/types"

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>(mockPortfolios)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDesc, setNewDesc] = useState("")
  const [expanded, setExpanded] = useState<string | null>(portfolios[0]?.id ?? null)

  const handleCreate = () => {
    if (!newName.trim()) return
    const p: Portfolio = {
      id: crypto.randomUUID(),
      name: newName.trim(),
      description: newDesc.trim(),
      is_default: portfolios.length === 0,
      total_value: 0,
      total_pnl: 0,
      total_pnl_pct: 0,
      created_at: new Date().toISOString(),
    }
    setPortfolios([...portfolios, p])
    setNewName("")
    setNewDesc("")
    setDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">Portfolio</h1>
        {portfolios.length > 0 && (
          <Button variant="gradient" size="sm" className="gap-1.5" onClick={() => setDialogOpen(true)}>
            <Plus className="size-3.5" />
            Create Portfolio
          </Button>
        )}
      </div>

      {/* Empty state */}
      {portfolios.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex min-h-[50vh] items-center justify-center"
        >
          <div className="max-w-sm text-center">
            <Briefcase className="mx-auto size-12 text-text-muted" />
            <h2 className="mt-5 font-heading text-lg font-semibold">
              Start tracking your investments
            </h2>
            <p className="mt-2 text-sm text-text-secondary leading-relaxed">
              Create a portfolio to monitor performance, analyze sectors, and export reports.
            </p>
            <Button
              variant="gradient"
              className="mt-6 gap-1.5"
              onClick={() => setDialogOpen(true)}
            >
              <Plus className="size-4" />
              Create Portfolio
            </Button>
          </div>
        </motion.div>
      ) : (
        /* Portfolio cards */
        <div className="space-y-4">
          <AnimatePresence>
            {portfolios.map((portfolio, i) => {
              const isExpanded = expanded === portfolio.id
              const isPositive = portfolio.total_pnl >= 0

              return (
                <motion.div
                  key={portfolio.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
                  className="rounded-card border border-border-subtle bg-bg-surface transition-colors hover:border-border-hover"
                >
                  {/* Card header — clickable */}
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

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="font-mono text-base font-medium tabular-nums">
                          ${portfolio.total_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                        </p>
                        <div className="mt-0.5 flex items-center justify-end gap-1.5">
                          {isPositive ? (
                            <TrendingUp className="size-3 text-success" />
                          ) : (
                            <TrendingDown className="size-3 text-danger" />
                          )}
                          <PriceChange value={portfolio.total_pnl_pct} className="text-xs" />
                          <span className="font-mono text-xs tabular-nums text-text-muted">
                            (${Math.abs(portfolio.total_pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })})
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>

                  {/* Expanded positions */}
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
                          <PortfolioDetail initialPositions={mockPositions} />
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

      {/* Create Portfolio Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Portfolio</DialogTitle>
            <DialogDescription>
              Track your stock positions and monitor performance.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label htmlFor="portfolio-name" className="mb-1.5 block text-sm text-text-secondary">
                Name
              </label>
              <Input
                id="portfolio-name"
                placeholder="e.g. Tech Growth"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="portfolio-desc" className="mb-1.5 block text-sm text-text-secondary">
                Description
              </label>
              <Input
                id="portfolio-desc"
                placeholder="Optional description"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="gradient" onClick={handleCreate} disabled={!newName.trim()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
