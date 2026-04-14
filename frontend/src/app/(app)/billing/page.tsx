"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Check, Sparkles, Zap, Crown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/store/auth-store"
import { billingApi } from "@/lib/api"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

interface Plan {
  id: string
  name: string
  price_monthly: number
  price_annual: number
  popular?: boolean
  features: string[]
  limits: Record<string, number>
}

const planIcons: Record<string, typeof Sparkles> = {
  free: Sparkles,
  pro: Zap,
  premium: Crown,
}

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [billing, setBilling] = useState<"monthly" | "annual">("monthly")
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)
  const [subscription, setSubscription] = useState<{ plan: string; status: string | null; current_period_end?: number; cancel_at_period_end?: boolean } | null>(null)
  const tier = useAuthStore((s) => s.user?.tier ?? "free")

  useEffect(() => {
    Promise.all([
      billingApi.getPlans().then(({ data }) => setPlans(data)),
      billingApi.getSubscription().then(({ data }) => setSubscription(data)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const handleCheckout = async (planId: string) => {
    setCheckoutLoading(planId)
    try {
      const { data } = await billingApi.createCheckout({ plan: planId, billing })
      window.location.href = data.checkout_url
    } catch {
      toast.error("Failed to start checkout")
      setCheckoutLoading(null)
    }
  }

  const handleManage = async () => {
    try {
      const { data } = await billingApi.getPortal()
      window.location.href = data.portal_url
    } catch {
      toast.error("Failed to open billing portal")
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-96 rounded-card" />)}
        </div>
      </div>
    )
  }

  // Active subscriber view
  if (tier !== "free" && subscription?.status === "active") {
    const currentPlan = plans.find((p) => p.id === tier)
    const periodEnd = subscription.current_period_end
      ? new Date(subscription.current_period_end * 1000).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
      : null

    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="font-heading text-2xl font-semibold">Your Subscription</h1>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-card border border-border-subtle bg-bg-surface p-6"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center rounded-button bg-gradient-to-br from-accent-from to-accent-to p-2">
                {tier === "pro" ? <Zap className="size-5 text-bg-primary" /> : <Crown className="size-5 text-bg-primary" />}
              </div>
              <div>
                <p className="font-heading text-lg font-semibold">{currentPlan?.name} Plan</p>
                <p className="text-sm text-text-muted">${currentPlan?.price_monthly}/month</p>
              </div>
            </div>
            <Badge variant="default">Active</Badge>
          </div>

          {periodEnd && (
            <p className="mt-4 text-sm text-text-secondary">
              {subscription.cancel_at_period_end
                ? `Your subscription ends on ${periodEnd}`
                : `Next billing date: ${periodEnd}`
              }
            </p>
          )}

          <div className="mt-4 border-t border-border-subtle pt-4">
            <ul className="space-y-2">
              {currentPlan?.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-text-secondary">
                  <Check className="size-3.5 shrink-0 text-success" />
                  {f}
                </li>
              ))}
            </ul>
          </div>

          <Button variant="outline" className="mt-6 w-full" onClick={handleManage}>
            Manage Subscription
          </Button>
        </motion.div>
      </div>
    )
  }

  // Free tier → upgrade view
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold">Upgrade Your Plan</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Unlock more forecasts, data, and insights
        </p>
      </div>

      {/* Billing toggle */}
      <div className="flex items-center justify-center gap-3">
        <button
          onClick={() => setBilling("monthly")}
          className={cn("rounded-button px-4 py-1.5 text-sm transition-colors", billing === "monthly" ? "bg-bg-elevated text-text-primary" : "text-text-muted")}
        >
          Monthly
        </button>
        <button
          onClick={() => setBilling("annual")}
          className={cn("rounded-button px-4 py-1.5 text-sm transition-colors", billing === "annual" ? "bg-bg-elevated text-text-primary" : "text-text-muted")}
        >
          Annual
          <span className="ml-1.5 text-[10px] text-success">Save 17%</span>
        </button>
      </div>

      {/* Plan cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan, i) => {
          const Icon = planIcons[plan.id] || Sparkles
          const isCurrent = plan.id === tier
          const price = billing === "monthly" ? plan.price_monthly : Math.round(plan.price_annual / 12)
          const isPopular = plan.popular

          return (
            <motion.div
              key={plan.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.3 }}
              className={cn(
                "relative flex flex-col rounded-card border p-6",
                isPopular
                  ? "border-[var(--accent-from)]/60 bg-bg-surface shadow-[0_0_30px_rgba(0,212,170,0.12)]"
                  : "border-border-subtle bg-bg-surface",
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
                <h2 className="font-heading text-lg font-semibold">{plan.name}</h2>
              </div>

              <div className="mt-4">
                {billing === "annual" && plan.price_monthly > 0 && (
                  <span className="mr-2 font-heading text-lg font-bold tabular-nums text-text-muted line-through">
                    ${plan.price_monthly}
                  </span>
                )}
                <span className="font-heading text-3xl font-bold tabular-nums">
                  ${price}
                </span>
                <span className="text-sm text-text-muted">/mo</span>
                {billing === "annual" && plan.price_annual > 0 && (
                  <p className="mt-0.5 text-xs text-text-muted">
                    ${plan.price_annual}/year
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

              <div className="mt-6">
                {isCurrent ? (
                  <Button variant="outline" className="w-full" disabled>
                    Current Plan
                  </Button>
                ) : plan.id === "free" ? (
                  <Button variant="outline" className="w-full" disabled>
                    Free Forever
                  </Button>
                ) : (
                  <Button
                    variant={isPopular ? "gradient" : "outline"}
                    className="w-full"
                    disabled={!!checkoutLoading}
                    onClick={() => handleCheckout(plan.id)}
                  >
                    {checkoutLoading === plan.id ? "Redirecting..." : `Upgrade to ${plan.name}`}
                  </Button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
