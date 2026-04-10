"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { ArrowRight, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { TickerBadge } from "@/components/ui/ticker-badge"

export function LiveDemo() {
  return (
    <section className="py-24 px-4">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            See It In Action
          </h2>
          <p className="mt-3 text-text-secondary">
            Real-time AI predictions powered by 107 data signals
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ delay: 0.2, duration: 0.5, ease: "easeOut" }}
          className="mx-auto mt-12 max-w-md"
        >
          <div className="relative rounded-card border border-border-subtle bg-bg-surface p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TickerBadge ticker="AAPL" />
                <div>
                  <p className="text-sm font-medium">Apple Inc.</p>
                  <p className="text-xs text-text-muted">Technology</p>
                </div>
              </div>
              <SignalBadge signal="BUY" confidence="HIGH" showWinRate />
            </div>

            {/* Price */}
            <div className="mt-5 flex items-baseline gap-3">
              <span className="font-mono text-3xl font-medium">$259.49</span>
              <PriceChange value={2.95} />
            </div>

            {/* Forecast preview */}
            <div className="mt-4 flex items-center gap-2 rounded-button bg-bg-elevated px-3 py-2">
              <TrendingUp className="size-4 text-success" />
              <span className="text-sm text-text-secondary">1-month forecast:</span>
              <span className="font-mono text-sm font-medium text-success">+6.7%</span>
            </div>

            {/* CTA */}
            <Link href="/auth/register" className="mt-5 block">
              <Button variant="gradient" className="w-full gap-2">
                Predict Any Stock
                <ArrowRight className="size-4" />
              </Button>
            </Link>

            {/* Watermark */}
            <p className="mt-3 text-center text-xs text-text-muted">
              Sign up for full access
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
