"use client"

import { useState, useEffect } from "react"
import { Bell, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { notificationApi } from "@/lib/api"
import type { Alert } from "@/types"

const alertTypes = [
  { id: "price_above", label: "Price Above" },
  { id: "price_below", label: "Price Below" },
  { id: "forecast_change", label: "Signal Change" },
] as const

export function AlertButton({ ticker }: { ticker: string }) {
  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [alertType, setAlertType] = useState("price_above")
  const [value, setValue] = useState("")
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!open) return
    notificationApi.getAlerts({ limit: 50 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setAlerts(list.filter((a) => a.ticker === ticker))
      })
      .catch(() => {})
  }, [open, ticker])

  const handleCreate = async () => {
    const num = parseFloat(value)
    if (isNaN(num) || num <= 0) return
    setCreating(true)
    try {
      const { data } = await notificationApi.createAlert({
        ticker,
        alert_type: alertType,
        condition_value: num,
      })
      setAlerts((prev) => [...prev, data])
      setValue("")
      const symbol = alertType === "price_above" ? ">" : alertType === "price_below" ? "<" : "→"
      toast.success(`Alert set: ${ticker} ${symbol} $${num}`)
    } catch {
      toast.error("Failed to create alert")
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
    try {
      await notificationApi.deleteAlert(id)
      toast.success("Alert deleted")
    } catch {
      toast.error("Failed to delete alert")
    }
  }

  return (
    <>
      <Button variant="outline" size="icon" onClick={() => setOpen(true)} title="Set Alert">
        <Bell className="size-4" />
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Alerts for {ticker}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Alert Type</label>
              <select
                value={alertType}
                onChange={(e) => setAlertType(e.target.value)}
                className="flex h-9 w-full rounded-button border border-border-subtle bg-bg-surface px-3 py-1 text-sm text-text-primary transition-colors focus:border-[var(--accent-from)] focus:outline-none"
              >
                {alertTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-text-secondary">Value</label>
              <Input
                type="number"
                step="0.01"
                placeholder="270.00"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="gradient" onClick={handleCreate} disabled={creating || !value}>
              {creating ? "Creating..." : "Create Alert"}
            </Button>
          </DialogFooter>

          {alerts.length > 0 && (
            <div className="mt-2 border-t border-border-subtle pt-4">
              <p className="mb-2 text-xs font-medium text-text-muted">Active Alerts</p>
              <div className="space-y-2">
                {alerts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between rounded-button bg-bg-elevated px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={a.is_triggered ? "danger" : "success"} className="text-[10px]">
                        {a.is_triggered ? "Triggered" : "Active"}
                      </Badge>
                      <span className="text-xs text-text-secondary">
                        {a.alert_type === "price_above" ? ">" : a.alert_type === "price_below" ? "<" : "→"} ${a.condition_value}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="rounded-button p-1 text-text-muted hover:text-danger"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
