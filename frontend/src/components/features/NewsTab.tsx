"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { mockNews } from "@/lib/mock-data"
import type { Sentiment } from "@/types"
import { cn } from "@/lib/utils"

const sentimentVariant: Record<string, "success" | "danger" | "secondary"> = {
  positive: "success",
  negative: "danger",
  neutral: "secondary",
}

const impactColors: Record<string, string> = {
  high: "border-danger text-danger",
  medium: "border-border-subtle text-text-muted",
  low: "border-border-subtle text-text-muted",
}

const filters: { id: Sentiment | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "positive", label: "Positive" },
  { id: "negative", label: "Negative" },
  { id: "neutral", label: "Neutral" },
]

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return "Just now"
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function NewsTab({ ticker }: { ticker: string }) {
  const [filter, setFilter] = useState<Sentiment | "all">("all")
  const [expanded, setExpanded] = useState<string | null>(null)

  const tickerNews = mockNews.filter((a) => a.tickers.includes(ticker))
  const articles = tickerNews.length > 0 ? tickerNews : mockNews
  const isGeneral = tickerNews.length === 0

  const filtered = filter === "all" ? articles : articles.filter((a) => a.sentiment === filter)

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-1">
        {filters.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "rounded-chip px-3 py-1 text-xs font-medium transition-colors duration-150",
              filter === f.id
                ? "bg-bg-elevated text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            {f.label}
          </button>
        ))}
        {isGeneral && (
          <span className="ml-2 text-xs text-text-muted">Showing general market news</span>
        )}
      </div>

      {/* Articles */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="flex min-h-[20vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
            <p className="text-sm text-text-muted">No {filter} news found</p>
          </div>
        ) : (
          filtered.map((article, i) => (
            <motion.div
              key={article.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
              className="rounded-card border border-border-subtle bg-bg-surface p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-start gap-1.5 text-sm font-medium leading-snug hover:text-[var(--accent-from)]"
                  >
                    {article.title}
                    <ExternalLink className="mt-0.5 size-3 shrink-0 text-text-muted opacity-0 transition-opacity group-hover:opacity-100" />
                  </a>
                  <div className="mt-1.5 flex items-center gap-2 text-xs text-text-muted">
                    <span>{article.source}</span>
                    <span>&middot;</span>
                    <span>{timeAgo(article.published_at)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {article.impact === "high" && (
                    <Badge variant="outline" className={cn("text-[10px]", impactColors.high)}>
                      HIGH
                    </Badge>
                  )}
                  <Badge variant={sentimentVariant[article.sentiment]} className="text-[10px]">
                    {article.sentiment}
                  </Badge>
                </div>
              </div>

              {/* Expandable summary */}
              {article.summary && (
                <>
                  <button
                    onClick={() => setExpanded(expanded === article.id ? null : article.id)}
                    className="mt-2 flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary"
                  >
                    {expanded === article.id ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                    {expanded === article.id ? "Hide summary" : "Show summary"}
                  </button>
                  {expanded === article.id && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-2 text-xs text-text-secondary leading-relaxed"
                    >
                      {article.summary}
                    </motion.p>
                  )}
                </>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
