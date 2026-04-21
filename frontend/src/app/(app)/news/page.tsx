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
import { PageGuide } from "@/components/ui/page-guide"
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

      <PageGuide
        summary="Real-time financial news — every article tagged with sentiment and impact."
        sections={[
          {
            title: "What this page shows",
            body: [
              "Aggregated news from Yahoo Finance, Seeking Alpha, Reuters, and MarketWatch. Updates every 30 minutes.",
              "Each article is automatically analysed by FinBERT — a specialised AI trained on financial text. It tags each story as positive, negative, or neutral for market impact, and rates the impact as HIGH / MEDIUM / LOW.",
              "Multi-ticker stories are tagged with every affected ticker so you can filter quickly.",
            ],
          },
          {
            title: "How to use it for trading",
            body: [
              "Check the Impact: HIGH filter first — those are headlines most likely to move stocks.",
              "Filter by Sentiment: Negative if you're worried about something in your portfolio; Positive if you're scanning for momentum trades.",
              "Click the ticker badges on any article to jump to that stock's detailed page and see if there's an entry signal.",
              "Use \"Show summary\" to expand without leaving the feed. Full article link opens the original source.",
            ],
          },
          {
            title: "A note on sentiment scores",
            body: [
              "The 0.0–1.0 score is how confident FinBERT is in its classification. 0.91 negative means \"very likely negative\", 0.55 means \"probably negative but mixed signals\".",
              "Sentiment is descriptive, not prescriptive. A \"positive\" article about a stock doesn't automatically mean you should buy it — the market may have already priced it in.",
            ],
          },
        ]}
        glossary={[
          {
            term: "FinBERT",
            definition: "BERT language model fine-tuned on financial news. Industry-standard for news sentiment.",
          },
          {
            term: "Impact HIGH",
            definition: "Breaking news or major corporate event. Analyst reports, earnings releases, M&A rumours.",
          },
          {
            term: "Impact LOW",
            definition: "Routine industry commentary or recap articles. Context, not catalysts.",
          },
          {
            term: "Sentiment score",
            definition: "0 → neutral, 1 → maximally positive/negative. The colour shows direction.",
          },
        ]}
      />

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
