"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { TickerBadge } from "@/components/ui/ticker-badge"
import { FilterChip } from "@/components/ui/filter-chip"
import { Skeleton } from "@/components/ui/skeleton"
import { timeAgo, normalizeNewsArticle } from "@/lib/formatters"
import { SENTIMENT_VARIANTS, IMPACT_STYLES } from "@/lib/constants"
import { newsApi } from "@/lib/api"
import type { NewsArticle, Sentiment, Impact } from "@/types"
import { cn } from "@/lib/utils"

const sentimentFilters: { id: Sentiment | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "positive", label: "Positive" },
  { id: "negative", label: "Negative" },
  { id: "neutral", label: "Neutral" },
]

const impactFilters: { id: Impact | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
]

const PER_PAGE = 20

export default function NewsPage() {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [sentiment, setSentiment] = useState<Sentiment | "all">("all")
  const [impact, setImpact] = useState<Impact | "all">("all")
  const [expanded, setExpanded] = useState<string | null>(null)

  const fetchNews = (pageNum: number, append: boolean) => {
    const setLoad = append ? setLoadingMore : setLoading
    setLoad(true)
    newsApi.getNews({
      sentiment: sentiment !== "all" ? sentiment : undefined,
      impact: impact !== "all" ? impact : undefined,
      per_page: PER_PAGE,
      page: pageNum,
    })
      .then(({ data }) => {
        const items = (data.data || []).map(normalizeNewsArticle)
        setArticles((prev) => append ? [...prev, ...items] : items)
        setTotal(data.total || items.length)
        setPage(pageNum)
      })
      .catch(() => { if (!append) setArticles([]) })
      .finally(() => setLoad(false))
  }

  useEffect(() => {
    fetchNews(1, false)
  }, [sentiment, impact]) // eslint-disable-line react-hooks/exhaustive-deps

  const hasMore = articles.length < total

  return (
    <div className="space-y-6">
      <div className="flex items-baseline gap-2">
        <h1 className="font-heading text-2xl font-semibold">Market News</h1>
        <span className="text-sm text-text-muted">({total})</span>
      </div>

      <div className="flex flex-wrap gap-4">
        <FilterChip options={sentimentFilters} value={sentiment} onChange={setSentiment} label="Sentiment" />
        <FilterChip options={impactFilters} value={impact} onChange={setImpact} label="Impact" />
      </div>

      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-card" />
          ))
        ) : (
          <AnimatePresence mode="popLayout">
            {articles.length === 0 ? (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex min-h-[30vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
                <p className="text-sm text-text-muted">No articles match your filters</p>
              </motion.div>
            ) : (
              articles.map((article, i) => (
                <motion.div
                  key={article.id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.3, ease: "easeOut" }}
                  className="rounded-card border border-border-subtle bg-bg-surface p-5 transition-colors hover:border-border-hover"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <a href={article.url} target="_blank" rel="noopener noreferrer" className="group inline-flex items-start gap-1.5 font-medium leading-snug hover:text-[var(--accent-from)]">
                        {article.title}
                        <ExternalLink className="mt-1 size-3 shrink-0 text-text-muted opacity-0 transition-opacity group-hover:opacity-100" />
                      </a>
                      <div className="mt-2 flex items-center gap-2 text-xs text-text-muted">
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
                        <span className="ml-1 opacity-60">{article.sentiment_score?.toFixed(2)}</span>
                      </Badge>
                    </div>
                  </div>

                  {article.tickers?.length > 0 && (
                    <div className="mt-3 flex items-center gap-1.5">
                      {article.tickers.map((t) => (
                        <Link key={t} href={`/stocks/${t}`}><TickerBadge ticker={t} /></Link>
                      ))}
                    </div>
                  )}

                  {article.summary && (
                    <>
                      <button onClick={() => setExpanded(expanded === article.id ? null : article.id)} className="mt-3 flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary">
                        {expanded === article.id ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                        {expanded === article.id ? "Hide summary" : "Show summary"}
                      </button>
                      <AnimatePresence>
                        {expanded === article.id && (
                          <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="mt-2 text-sm text-text-secondary leading-relaxed overflow-hidden">
                            {article.summary}
                          </motion.p>
                        )}
                      </AnimatePresence>
                    </>
                  )}
                </motion.div>
              ))
            )}
          </AnimatePresence>
        )}

        {!loading && hasMore && (
          <div className="flex items-center justify-center pt-2">
            <button
              onClick={() => fetchNews(page + 1, true)}
              disabled={loadingMore}
              className="rounded-button border border-border-subtle bg-bg-surface px-6 py-2.5 text-sm text-text-secondary transition-colors hover:border-border-hover hover:text-text-primary disabled:opacity-50"
            >
              {loadingMore ? "Loading..." : `Load more (${articles.length} of ${total})`}
            </button>
          </div>
        )}

        {!loading && !hasMore && articles.length > 0 && (
          <p className="pt-2 text-center text-xs text-text-muted">
            All {total} articles loaded
          </p>
        )}
      </div>
    </div>
  )
}
