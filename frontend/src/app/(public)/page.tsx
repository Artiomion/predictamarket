"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"
import { LiveDemo } from "@/components/landing/LiveDemo"
import { Features } from "@/components/landing/Features"
import { Performance } from "@/components/landing/Performance"
import { Strengths } from "@/components/landing/Strengths"
import { Pricing } from "@/components/landing/Pricing"
import { Footer } from "@/components/landing/Footer"
import { MODEL_METRICS } from "@/lib/model-metrics"

// Metrics from the 3-model ensemble study (ep2+ep4+ep5 equal-weight) on the
// post-Oct-2025 test window (Nov 2025 — early Apr 2026). WR and Return are
// for the Consensus BUY subset.
// Forecasts count is live count in DB, rounded. Numbers live in
// lib/model-metrics.ts (single source of truth).
const stats = [
  { value: `${MODEL_METRICS.conflong_win_rate_pct}%`, label: "Consensus Win Rate" },
  { value: MODEL_METRICS.top20_return_display, label: "Top-20 Return" },
  { value: String(MODEL_METRICS.n_tickers), label: "S&P 500 Stocks" },
  { value: "5K+", label: "Forecasts" },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
        <div className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[800px] rounded-full bg-[radial-gradient(ellipse,rgba(0,212,170,0.08)_0%,transparent_70%)]" />

        <div className="relative z-10 mx-auto max-w-4xl text-center">
          <div className="mb-8 flex items-center justify-center gap-3">
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.8, duration: 0.3, ease: "easeOut" }}
              className="inline-flex items-center rounded-chip border border-border-subtle bg-bg-surface px-3 py-1 font-mono text-xs text-success"
            >
              {MODEL_METRICS.conflong_win_rate_pct}% Consensus Win Rate
            </motion.span>
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 1.0, duration: 0.3, ease: "easeOut" }}
              className="inline-flex items-center rounded-chip border border-border-subtle bg-bg-surface px-3 py-1 font-mono text-xs text-[var(--accent-from)]"
            >
              Sharpe {MODEL_METRICS.conflong_sharpe} Ensemble
            </motion.span>
          </div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="font-heading text-5xl font-bold leading-tight tracking-tight md:text-6xl lg:text-7xl"
          >
            <span className="bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] bg-clip-text text-transparent">
              AI-Powered
            </span>
            <br />
            Stock Predictions
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5, ease: "easeOut" }}
            className="mx-auto mt-6 max-w-xl text-lg text-text-secondary md:text-xl"
          >
            {MODEL_METRICS.n_features} data signals. {MODEL_METRICS.n_tickers} S&P 500 stocks. One prediction engine.
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5, ease: "easeOut" }}
            className="mt-10"
          >
            <Link href="/auth/register">
              <Button variant="gradient" size="lg" className="gap-2 px-8 text-base">
                Try Free Forecast
                <ArrowRight className="size-4" />
              </Button>
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2, duration: 0.5, ease: "easeOut" }}
            className="mx-auto mt-16 grid max-w-lg grid-cols-2 gap-6 md:grid-cols-4 md:max-w-2xl"
          >
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 + i * 0.1, duration: 0.4, ease: "easeOut" }}
                className="text-center"
              >
                <p className="font-mono text-2xl font-medium text-text-primary">{stat.value}</p>
                <p className="mt-1 text-xs text-text-muted">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <LiveDemo />
      <Features />
      <Performance />
      <Strengths />
      <Pricing />
      <Footer />
    </>
  )
}
