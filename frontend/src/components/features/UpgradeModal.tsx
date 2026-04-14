"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Lock, X, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { billingApi } from "@/lib/api"
import { toast } from "sonner"
import Link from "next/link"

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  feature?: string
}

const FREE_VS_PRO = [
  { feature: "Forecasts/day", free: "1", pro: "10" },
  { feature: "Top Picks", free: "5", pro: "20" },
  { feature: "Portfolios", free: "1", pro: "5" },
  { feature: "SEC EDGAR", free: "No", pro: "Yes" },
  { feature: "Alerts", free: "3", pro: "20" },
]

export function UpgradeModal({ open, onClose, feature }: UpgradeModalProps) {
  const [loading, setLoading] = useState(false)

  const handleUpgrade = async () => {
    setLoading(true)
    try {
      const { data } = await billingApi.createCheckout({ plan: "pro", billing: "monthly" })
      window.location.href = data.checkout_url
    } catch {
      toast.error("Failed to start checkout")
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-modal border border-border-subtle bg-bg-surface p-6 shadow-2xl"
          >
            <button
              onClick={onClose}
              className="absolute right-4 top-4 rounded-button p-1 text-text-muted hover:bg-bg-elevated hover:text-text-secondary"
            >
              <X className="size-4" />
            </button>

            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center rounded-button bg-warning/10 p-2">
                <Lock className="size-5 text-warning" />
              </div>
              <div>
                <h2 className="font-heading text-lg font-semibold">
                  {feature ? `Unlock ${feature}` : "Upgrade to Pro"}
                </h2>
                <p className="text-xs text-text-muted">This feature is available on the Pro plan</p>
              </div>
            </div>

            {/* Comparison table */}
            <div className="mt-5 rounded-card border border-border-subtle overflow-hidden">
              <div className="grid grid-cols-3 border-b border-border-subtle bg-bg-elevated/50 px-4 py-2 text-xs font-medium text-text-muted">
                <span>Feature</span>
                <span className="text-center">Free</span>
                <span className="text-center text-[var(--accent-from)]">Pro</span>
              </div>
              {FREE_VS_PRO.map((row) => (
                <div key={row.feature} className="grid grid-cols-3 border-b border-border-subtle px-4 py-2 text-sm last:border-b-0">
                  <span className="text-text-secondary">{row.feature}</span>
                  <span className="text-center text-text-muted">{row.free}</span>
                  <span className="text-center font-medium">{row.pro}</span>
                </div>
              ))}
            </div>

            <Button
              variant="gradient"
              className="mt-5 w-full gap-2"
              disabled={loading}
              onClick={handleUpgrade}
            >
              <Zap className="size-4" />
              {loading ? "Redirecting..." : "Upgrade to Pro — $15/mo"}
            </Button>

            <Link
              href="/billing"
              onClick={onClose}
              className="mt-3 block text-center text-xs text-text-muted hover:text-[var(--accent-from)]"
            >
              Compare all plans
            </Link>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
