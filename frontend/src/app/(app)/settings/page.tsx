"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { User, Bell, CreditCard, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/store/auth-store"
import { authApi, billingApi } from "@/lib/api"
import { toast } from "sonner"
import Link from "next/link"
import { cn } from "@/lib/utils"

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border border-border-subtle transition-colors duration-200",
        checked ? "bg-success/30" : "bg-bg-elevated",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span className={cn(
        "pointer-events-none block size-4 rounded-full shadow-sm transition-transform duration-200",
        checked ? "translate-x-4 bg-success" : "translate-x-0 bg-text-muted",
      )} />
    </button>
  )
}

function Section({ icon: Icon, title, description, children }: {
  icon: typeof User
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="rounded-card border border-border-subtle bg-bg-surface"
    >
      <div className="border-b border-border-subtle px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center rounded-button bg-bg-elevated p-1.5">
            <Icon className="size-4 text-text-secondary" />
          </div>
          <div>
            <h2 className="font-heading text-sm font-medium">{title}</h2>
            <p className="text-xs text-text-muted">{description}</p>
          </div>
        </div>
      </div>
      <div className="px-6 py-5">{children}</div>
    </motion.div>
  )
}

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [name, setName] = useState(user?.full_name || "")
  const [saving, setSaving] = useState(false)
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [pushNotifs, setPushNotifs] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const handleSaveProfile = async () => {
    setSaving(true)
    try {
      const { data } = await authApi.updateMe({ name })
      setUser(data)
      toast.success("Profile updated")
    } catch {
      toast.error("Failed to update profile")
    } finally {
      setSaving(false)
    }
  }

  const tier = user?.tier || "free"
  const tierLabel = { free: "Free", pro: "Pro", premium: "Premium" }[tier]

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <Section icon={User} title="Profile" description="Your personal information">
        <div className="space-y-4">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm text-text-secondary">Full name</label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-text-secondary">Email address</label>
            <Input
              value={user?.email || ""}
              disabled
              className="opacity-60"
            />
            <p className="mt-1 text-[11px] text-text-muted">Email cannot be changed</p>
          </div>
          <div className="flex justify-end">
            <Button
              variant="gradient"
              size="sm"
              disabled={saving || name === (user?.full_name || "")}
              onClick={handleSaveProfile}
            >
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>
      </Section>

      {/* Notifications */}
      <Section icon={Bell} title="Notifications" description="Choose how you want to be notified">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Email alerts</p>
              <p className="text-xs text-text-muted">Price alerts, forecast updates, and earnings reminders</p>
            </div>
            <Toggle checked={emailAlerts} onChange={setEmailAlerts} />
          </div>
          <div className="border-t border-border-subtle" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Push notifications</p>
              <p className="text-xs text-text-muted">Real-time alerts in your browser</p>
            </div>
            <Toggle checked={pushNotifs} onChange={setPushNotifs} />
          </div>
        </div>
      </Section>

      {/* Subscription */}
      <Section icon={CreditCard} title="Subscription" description="Your current plan">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium">{tierLabel} plan</p>
              <Badge variant={tier === "free" ? "secondary" : tier === "pro" ? "default" : "warning"}>
                {tier === "free" ? "Current" : "Active"}
              </Badge>
            </div>
            <p className="mt-0.5 text-xs text-text-muted">
              {tier === "free"
                ? "Upgrade to unlock more forecasts, SEC data, and unlimited alerts"
                : tier === "pro"
                  ? "10 forecasts/day, 20 top picks, SEC EDGAR access"
                  : "Unlimited forecasts, alerts, and CSV export"
              }
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {tier === "free" ? (
              <Link href="/billing">
                <Button variant="gradient" size="sm">Upgrade Plan</Button>
              </Link>
            ) : (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-text-muted hover:text-text-primary"
                  onClick={async () => {
                    try {
                      const { data } = await billingApi.getPortal()
                      window.location.href = data.portal_url
                    } catch {
                      toast.error("Failed to open billing portal")
                    }
                  }}
                >
                  Manage Billing &rarr;
                </Button>
                <Link href="/billing">
                  <Button variant="gradient" size="sm" className="gap-1.5">
                    <CreditCard className="size-3.5" />
                    Change Plan
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </Section>

      {/* Danger Zone */}
      <Section icon={Trash2} title="Danger Zone" description="Irreversible actions">
        {!deleteConfirm ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Delete account</p>
              <p className="text-xs text-text-muted">Permanently remove your account and all associated data</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="border-danger/30 text-danger hover:bg-danger/10"
              onClick={() => setDeleteConfirm(true)}
            >
              Delete Account
            </Button>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-button border border-danger/30 bg-danger/5 p-4"
          >
            <p className="text-sm font-medium text-danger">Delete your account?</p>
            <p className="mt-1 text-xs text-text-secondary">
              All your portfolios, watchlists, alerts, and forecast history will be permanently deleted. This action cannot be undone.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-danger/30 bg-danger/10 text-danger hover:bg-danger/20"
                onClick={() => { toast.error("Account deletion is not available in beta"); setDeleteConfirm(false) }}
              >
                Delete my account
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteConfirm(false)}
              >
                Keep my account
              </Button>
            </div>
          </motion.div>
        )}
      </Section>
    </div>
  )
}
