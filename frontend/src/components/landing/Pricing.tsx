"use client"

import { useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Check, Sparkles, Zap, Crown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const plans = [
  {
    id: "free",
    name: "Free",
    monthlyPrice: 0,
    yearlyPrice: 0,
    icon: Sparkles,
    features: [
      "1 forecast/day",
      "Top 5 picks",
      "1 portfolio",
      "Basic charts",
    ],
    cta: "Start Free",
    popular: false,
  },
  {
    id: "pro",
    name: "Pro",
    monthlyPrice: 15,
    yearlyPrice: 150,
    icon: Zap,
    features: [
      "10 forecasts/day",
      "Top 20 picks",
      "5 portfolios",
      "SEC EDGAR",
      "All indicators",
      "Sentiment trends",
      "Push alerts",
    ],
    cta: "Upgrade to Pro",
    popular: true,
  },
  {
    id: "premium",
    name: "Premium",
    monthlyPrice: 39,
    yearlyPrice: 390,
    icon: Crown,
    features: [
      "Unlimited forecasts",
      "All Pro features",
      "API access",
      "Backtesting",
      "CSV/PDF export",
      "Priority inference",
    ],
    cta: "Upgrade to Premium",
    popular: false,
  },
] as const

export function Pricing() {
  const [annual, setAnnual] = useState(false)

  return (
    <section id="pricing" className="py-24 px-4">
      <div className="mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Upgrade Your Plan
          </h2>
          <p className="mt-3 text-text-secondary">
            Unlock more forecasts, data, and insights
          </p>

          {/* Toggle */}
          <div className="mt-8 inline-flex items-center gap-1 rounded-button border border-border-subtle bg-bg-surface p-1">
            <button
              onClick={() => setAnnual(false)}
              className={cn(
                "rounded-button px-4 py-1.5 text-sm font-medium transition-colors duration-150",
                !annual ? "bg-bg-elevated text-text-primary" : "text-text-muted hover:text-text-secondary"
              )}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={cn(
                "rounded-button px-4 py-1.5 text-sm font-medium transition-colors duration-150",
                annual ? "bg-bg-elevated text-text-primary" : "text-text-muted hover:text-text-secondary"
              )}
            >
              Annual
              <span className="ml-1.5 text-[10px] text-success">Save 17%</span>
            </button>
          </div>
        </motion.div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {plans.map((plan, i) => {
            const Icon = plan.icon
            const price = annual ? Math.round(plan.yearlyPrice / 12) : plan.monthlyPrice
            const isPopular = plan.popular

            return (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ delay: i * 0.1, duration: 0.4, ease: "easeOut" }}
                className={cn(
                  "relative flex flex-col rounded-card border p-6",
                  isPopular
                    ? "border-[var(--accent-from)]/60 bg-bg-surface shadow-[0_0_30px_rgba(0,212,170,0.12)]"
                    : "border-border-subtle bg-bg-surface"
                )}
              >
                {isPopular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge variant="default" className="bg-gradient-to-r from-accent-from to-accent-to text-bg-primary text-[10px] px-3">
                      Most Popular
                    </Badge>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Icon className={cn("size-5", isPopular ? "text-[var(--accent-from)]" : "text-text-secondary")} />
                  <h3 className="font-heading text-lg font-semibold">{plan.name}</h3>
                </div>

                <div className="mt-4">
                  {annual && plan.monthlyPrice > 0 && (
                    <span className="mr-2 font-heading text-lg font-bold tabular-nums text-text-muted line-through">
                      ${plan.monthlyPrice}
                    </span>
                  )}
                  <span className="font-heading text-3xl font-bold tabular-nums">
                    ${price}
                  </span>
                  <span className="text-sm text-text-muted">/mo</span>
                  {annual && plan.yearlyPrice > 0 && (
                    <p className="mt-0.5 text-xs text-text-muted">
                      ${plan.yearlyPrice}/year
                    </p>
                  )}
                </div>

                <ul className="mt-6 flex-1 space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                      <Check className="mt-0.5 size-3.5 shrink-0 text-success" />
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
