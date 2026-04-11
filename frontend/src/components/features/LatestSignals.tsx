"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { mockSignals } from "@/lib/mock-data"

export function LatestSignals() {
  const signals = mockSignals.slice(0, 5)

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface">
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <h2 className="font-heading text-base font-medium">Latest Signals</h2>
        <Link
          href="/stocks"
          className="text-xs text-text-muted transition-colors hover:text-[var(--accent-from)]"
        >
          View all
        </Link>
      </div>

      <div className="px-3 pb-3">
        {signals.map((s, i) => (
          <motion.div
            key={s.ticker}
            initial={{ opacity: 0, x: 6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
          >
            <Link
              href={`/stocks/${s.ticker}`}
              className="flex items-center justify-between rounded-button px-2 py-2.5 transition-colors duration-150 hover:bg-bg-elevated"
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-medium w-12">{s.ticker}</span>
                <SignalBadge signal={s.signal} />
              </div>
              <PriceChange value={s.predicted_return_1m} />
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
