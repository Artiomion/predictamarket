"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { Badge } from "@/components/ui/badge"
import { FilterChip } from "@/components/ui/filter-chip"
import { Skeleton } from "@/components/ui/skeleton"
import { timeAgo, normalizeNewsArticle } from "@/lib/formatters"
import { SENTIMENT_VARIANTS, IMPACT_STYLES } from "@/lib/constants"
import { newsApi } from "@/lib/api"
import type { NewsArticle, Sentiment } from "@/types"
import { cn } from "@/lib/utils"

const filters: { id: Sentiment | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "positive", label: "Positive" },
  { id: "negative", label: "Negative" },
  { id: "neutral", label: "Neutral" },
]

interface SentimentPoint {
  date: string
  avg_sentiment: number
  news_count: number
}

function getSentimentColor(avg: number): string {
  if (avg > 0.6) return "#00FF88"
  if (avg < 0.4) return "#FF3366"
  return "#FFB800"
}

export function NewsTab({ ticker }: { ticker: string }) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Sentiment | "all">("all")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [isGeneral, setIsGeneral] = useState(false)
  const [sentimentData, setSentimentData] = useState<SentimentPoint[]>([])
  const [sentimentLoading, setSentimentLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setSentimentLoading(true)

    // Load news
    newsApi.getNewsByTicker(ticker, { per_page: 10 })
      .then(({ data }) => {
        const items = (data.data || []).map(normalizeNewsArticle)
        if (items.length > 0) {
          setArticles(items)
          setIsGeneral(false)
        } else {
          return newsApi.getNews({ per_page: 5 }).then(({ data: general }) => {
            setArticles((general.data || []).map(normalizeNewsArticle))
            setIsGeneral(true)
          })
        }
      })
      .catch(() => setArticles([]))
      .finally(() => setLoading(false))

    // Load sentiment trend
    newsApi.getTickerSentiment(ticker, { days: 7 })
      .then(({ data }) => {
        setSentimentData(Array.isArray(data) ? data : [])
      })
      .catch(() => setSentimentData([]))
      .finally(() => setSentimentLoading(false))
  }, [ticker])

  const filtered = filter === "all" ? articles : articles.filter((a) => a.sentiment === filter)

  const avgSentiment = sentimentData.length > 0
    ? sentimentData.reduce((s, d) => s + d.avg_sentiment, 0) / sentimentData.length
    : 0.5
  const lineColor = getSentimentColor(avgSentiment)

  if (loading && sentimentLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-[150px] rounded-card" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-card" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FilterChip options={filters} value={filter} onChange={setFilter} label="Sentiment" />
        {isGeneral && <span className="text-xs text-text-muted">Showing general market news</span>}
      </div>

      {/* Sentiment Trend Chart */}
      {sentimentLoading ? (
        <Skeleton className="h-[150px] rounded-card max-sm:h-[120px]" />
      ) : sentimentData.length > 0 && (
        <div className="rounded-card border border-border-subtle bg-bg-surface p-4">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">
            Sentiment Trend (7d)
          </h3>
          <div className="h-[120px] sm:h-[150px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sentimentData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "#6B6B80" }}
                  tickFormatter={(d: string) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  stroke="rgba(255,255,255,0.06)"
                />
                <YAxis
                  domain={[0, 1]}
                  tick={{ fontSize: 10, fill: "#6B6B80" }}
                  stroke="rgba(255,255,255,0.06)"
                  tickFormatter={(v: number) => v.toFixed(1)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#12121A",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "#E8E8ED",
                  }}
                  formatter={(value) => [Number(value).toFixed(2), "Sentiment"]}
                  labelFormatter={(label) => new Date(String(label)).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                />
                <Area
                  type="monotone"
                  dataKey="avg_sentiment"
                  stroke={lineColor}
                  strokeWidth={2}
                  fill={lineColor}
                  fillOpacity={0.1}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Articles */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="flex min-h-[20vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
            <p className="text-sm text-text-muted">No {filter !== "all" ? filter : ""} news found</p>
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
                  <a href={article.url} target="_blank" rel="noopener noreferrer" className="group flex items-start gap-1.5 text-sm font-medium leading-snug hover:text-[var(--accent-from)]">
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
                    <Badge variant="outline" className={cn("text-[10px]", IMPACT_STYLES.high)}>HIGH</Badge>
                  )}
                  <Badge variant={SENTIMENT_VARIANTS[article.sentiment]} className="text-[10px]">
                    {article.sentiment}
                  </Badge>
                </div>
              </div>

              {article.summary && (
                <>
                  <button onClick={() => setExpanded(expanded === article.id ? null : article.id)} className="mt-2 flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary">
                    {expanded === article.id ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                    {expanded === article.id ? "Hide summary" : "Show summary"}
                  </button>
                  {expanded === article.id && (
                    <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-2 text-xs text-text-secondary leading-relaxed">
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
