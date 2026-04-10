"use client"

import { useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const plans = [
  {
    name: "Free",
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      "1 forecast per day",
      "Top 5 picks visible",
      "1 portfolio, 10 positions",
      "1 watchlist",
      "3 price alerts",
    ],
    cta: "Start Free",
    popular: false,
  },
  {
    name: "Pro",
    monthlyPrice: 15,
    yearlyPrice: 150,
    features: [
      "10 forecasts per day",
      "All 20 top picks",
      "5 portfolios, unlimited positions",
      "5 watchlists, 20 alerts",
      "SEC Edgar filings",
      "Batch forecasts",
    ],
    cta: "Upgrade to Pro",
    popular: true,
  },
  {
    name: "Premium",
    monthlyPrice: 39,
    yearlyPrice: 390,
    features: [
      "Unlimited forecasts",
      "All 20 top picks",
      "10 portfolios, unlimited positions",
      "10 watchlists, unlimited alerts",
      "SEC Edgar filings",
      "Batch forecasts",
      "CSV export",
    ],
    cta: "Go Premium",
    popular: false,
  },
] as const

export function Pricing() {
  const [annual, setAnnual] = useState(false)

  return (
    <section id="pricing" className="py-24 px-4">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Simple, Transparent Pricing
          </h2>
          <p className="mt-3 text-text-secondary">
            Start free. Upgrade when you need more.
          </p>

          {/* Toggle */}
          <div className="mt-8 inline-flex items-center gap-3 rounded-button border border-border-subtle bg-bg-surface p-1">
            <button
              onClick={() => setAnnual(false)}
              className={cn(
                "rounded-chip px-4 py-1.5 text-sm font-medium transition-colors duration-150",
                !annual ? "bg-bg-elevated text-text-primary" : "text-text-muted hover:text-text-secondary"
              )}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={cn(
                "rounded-chip px-4 py-1.5 text-sm font-medium transition-colors duration-150",
                annual ? "bg-bg-elevated text-text-primary" : "text-text-muted hover:text-text-secondary"
              )}
            >
              Annual
              <span className="ml-1.5 text-xs text-success">Save 17%</span>
            </button>
          </div>
        </motion.div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {plans.map((plan, i) => {
            const price = annual ? plan.yearlyPrice / 12 : plan.monthlyPrice
            const isPopular = plan.popular

            return (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ delay: i * 0.1, duration: 0.4, ease: "easeOut" }}
                className={cn(
                  "relative rounded-card border p-6",
                  isPopular
                    ? "border-[var(--accent-from)] bg-bg-surface"
                    : "border-border-subtle bg-bg-surface"
                )}
              >
                {isPopular && (
                  <Badge variant="default" className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                    Popular
                  </Badge>
                )}

                <h3 className="font-heading text-lg font-semibold">{plan.name}</h3>

                <div className="mt-4 flex items-baseline gap-1">
                  <span className="font-mono text-4xl font-medium">
                    ${price === 0 ? "0" : price % 1 === 0 ? price : price.toFixed(2)}
                  </span>
                  {price > 0 && (
                    <span className="text-sm text-text-muted">/mo</span>
                  )}
                </div>
                {annual && plan.yearlyPrice > 0 && (
                  <p className="mt-1 text-xs text-text-muted">
                    ${plan.yearlyPrice}/year billed annually
                  </p>
                )}

                <ul className="mt-6 space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                      <Check className="mt-0.5 size-3.5 shrink-0 text-[var(--accent-from)]" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link href="/auth/register" className="mt-6 block">
                  <Button
                    variant={isPopular ? "gradient" : "outline"}
                    className="w-full"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
