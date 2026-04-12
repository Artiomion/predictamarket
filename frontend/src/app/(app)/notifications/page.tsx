"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Bell, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { timeAgo } from "@/lib/formatters"
import { notificationApi } from "@/lib/api"
import type { Alert, Notification } from "@/types"

export default function NotificationsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [history, setHistory] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      notificationApi.getAlerts({ limit: 50 }).catch(() => ({ data: [] })),
      notificationApi.getHistory({ limit: 20 }).catch(() => ({ data: [] })),
    ]).then(([alertsRes, historyRes]) => {
      setAlerts(Array.isArray(alertsRes.data) ? alertsRes.data : [])
      setHistory(Array.isArray(historyRes.data) ? historyRes.data : [])
    }).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
    try {
      await notificationApi.deleteAlert(id)
      toast.success("Alert deleted")
    } catch {
      toast.error("Failed to delete")
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-40" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-card" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-2xl font-semibold">Notifications</h1>

      {/* Active Alerts */}
      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
          Active Alerts ({alerts.filter((a) => !a.is_triggered).length})
        </h2>

        {alerts.length === 0 ? (
          <div className="flex min-h-[30vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
            <div className="text-center">
              <Bell className="mx-auto size-8 text-text-muted" />
              <p className="mt-3 text-sm text-text-muted">No alerts set</p>
              <p className="mt-1 text-xs text-text-muted">Add alerts from any stock page using the bell button.</p>
              <Link href="/stocks">
                <Button variant="gradient" size="sm" className="mt-4">Browse Stocks</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert, i) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
                className="flex items-center justify-between rounded-card border border-border-subtle bg-bg-surface px-5 py-3"
              >
                <div className="flex items-center gap-3">
                  <Link href={`/stocks/${alert.ticker}`} className="font-mono text-sm font-medium hover:text-[var(--accent-from)]">
                    {alert.ticker}
                  </Link>
                  <Badge variant={alert.is_triggered ? "danger" : "success"} className="text-[10px]">
                    {alert.is_triggered ? "Triggered" : "Active"}
                  </Badge>
                  <span className="text-sm text-text-secondary">
                    {alert.alert_type === "price_above" ? "Price above" : alert.alert_type === "price_below" ? "Price below" : alert.alert_type.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-sm tabular-nums">${alert.condition_value}</span>
                </div>
                <button
                  onClick={() => handleDelete(alert.id)}
                  className="rounded-button p-1.5 text-text-muted transition-colors hover:bg-bg-elevated hover:text-danger"
                >
                  <Trash2 className="size-4" />
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* History */}
      {history.length > 0 && (
        <section>
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
            History
          </h2>
          <div className="space-y-2">
            {history.map((n, i) => (
              <motion.div
                key={n.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
                className="rounded-card border border-border-subtle bg-bg-surface px-5 py-3"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="mt-0.5 text-xs text-text-secondary">{n.body}</p>
                  </div>
                  <span className="text-xs text-text-muted">{timeAgo(n.created_at)}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
