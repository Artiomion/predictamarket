"use client"

import { motion } from "framer-motion"
import {
  TrendingUp,
  Trophy,
  PieChart,
  Newspaper,
  CalendarDays,
  Users,
} from "lucide-react"

const features = [
  {
    icon: TrendingUp,
    title: "AI Forecast",
    description: "Temporal Fusion Transformer predicts prices across 5 horizons",
  },
  {
    icon: Trophy,
    title: "Top Picks",
    description: "Ranked stocks by predicted return with confidence signals",
  },
  {
    icon: PieChart,
    title: "Portfolio Analytics",
    description: "Track P&L, sector allocation, and performance vs S&P 500",
  },
  {
    icon: Newspaper,
    title: "News Sentiment",
    description: "FinBERT-powered sentiment analysis on every headline",
  },
  {
    icon: CalendarDays,
    title: "Earnings Calendar",
    description: "Upcoming reports with EPS estimates and beat/miss history",
  },
  {
    icon: Users,
    title: "Insider Tracking",
    description: "SEC insider buys and sells with net activity trends",
  },
] as const

export function Features() {
  return (
    <section id="features" className="py-24 px-4">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Everything You Need
          </h2>
          <p className="mt-3 text-text-secondary">
            One platform for predictions, analytics, and market intelligence
          </p>
        </motion.div>

        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ delay: i * 0.08, duration: 0.4, ease: "easeOut" }}
                whileHover={{ scale: 1.02 }}
                className="group rounded-card border border-border-subtle bg-bg-surface p-6 transition-all duration-150 hover:border-border-hover hover:shadow-glow-accent"
              >
                <div className="flex size-10 items-center justify-center rounded-button bg-bg-elevated text-[var(--accent-from)]">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 font-heading text-base font-medium">
                  {feature.title}
                </h3>
                <p className="mt-1.5 text-sm text-text-secondary leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
