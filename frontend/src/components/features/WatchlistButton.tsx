"use client"

import { useState, useEffect } from "react"
import { Star } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { portfolioApi } from "@/lib/api"
import { cn } from "@/lib/utils"

interface WatchlistButtonProps {
  ticker: string
}

export function WatchlistButton({ ticker }: WatchlistButtonProps) {
  const [watchlisted, setWatchlisted] = useState(false)
  const [watchlistId, setWatchlistId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    portfolioApi.getWatchlists()
      .then(async ({ data }) => {
        const lists = Array.isArray(data) ? data : []
        if (lists.length > 0) {
          const { data: detail } = await portfolioApi.getWatchlist(lists[0].id)
          setWatchlistId(detail.id)
          setWatchlisted(detail.items?.some((i) => i.ticker === ticker) ?? false)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ticker])

  const toggle = async () => {
    try {
      let wlId = watchlistId
      if (!wlId) {
        const { data } = await portfolioApi.createWatchlist({ name: "My Watchlist" })
        wlId = data.id
        setWatchlistId(wlId)
      }

      if (watchlisted) {
        await portfolioApi.removeWatchlistItem(wlId, ticker)
        setWatchlisted(false)
        toast.success(`${ticker} removed from watchlist`)
      } else {
        await portfolioApi.addWatchlistItem(wlId, ticker)
        setWatchlisted(true)
        toast.success(`${ticker} added to watchlist`)
      }
    } catch {
      toast.error("Failed to update watchlist")
    }
  }

  if (loading) return null

  return (
    <Button
      variant={watchlisted ? "default" : "outline"}
      size="icon"
      onClick={toggle}
      className={cn(watchlisted && "text-warning bg-warning/10 border-warning/20")}
    >
      <Star className={cn("size-4", watchlisted && "fill-current")} />
    </Button>
  )
}
