const LOCALE = "en-US"

export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins} minutes ago`
  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString(LOCALE, { month: "short", day: "numeric", year: "numeric" })
}

export function formatCountdown(dateStr: string): { label: string; variant: "danger" | "warning" | "secondary"; urgent: boolean } {
  const diff = new Date(dateStr).getTime() - Date.now()
  const days = Math.ceil(diff / 86400000)
  if (days <= 0) return { label: "Today", variant: "danger", urgent: true }
  if (days === 1) return { label: "Tomorrow", variant: "warning", urgent: false }
  if (days <= 7) return { label: `In ${days} days`, variant: "secondary", urgent: false }
  return {
    label: new Date(dateStr).toLocaleDateString(LOCALE, { month: "short", day: "numeric" }),
    variant: "secondary",
    urgent: false,
  }
}

export function formatMarketCap(cap: number): string {
  if (cap >= 1e12) return `$${(cap / 1e12).toFixed(1)}T`
  if (cap >= 1e9) return `$${(cap / 1e9).toFixed(0)}B`
  return `$${(cap / 1e6).toFixed(0)}M`
}

export function formatValue(value: number | null | undefined): string {
  if (value == null) return "—"
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
  return `$${value.toLocaleString(LOCALE)}`
}

export function formatPrice(price: number): string {
  return price.toLocaleString(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat(LOCALE).format(n)
}

// Normalize API response field names (sentiment_label → sentiment, impact_level → impact)
export function normalizeNewsArticle<T extends { sentiment_label?: string; impact_level?: string; sentiment?: string; impact?: string }>(article: T): T {
  return {
    ...article,
    sentiment: article.sentiment || article.sentiment_label || "neutral",
    impact: article.impact || article.impact_level || "medium",
  }
}
