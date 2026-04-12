"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { timeAgo, normalizeNewsArticle } from "@/lib/formatters"
import { SENTIMENT_VARIANTS } from "@/lib/constants"
import { newsApi } from "@/lib/api"
import type { NewsArticle } from "@/types"

export function MarketNews() {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    newsApi.getNews({ per_page: 3 })
      .then(({ data }) => {
        setArticles((data.data || []).map(normalizeNewsArticle))
      })
      .catch(() => setArticles([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface">
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <h2 className="font-heading text-base font-medium">Market News</h2>
        <Link href="/news" className="text-xs text-text-muted transition-colors hover:text-[var(--accent-from)]">
          View all
        </Link>
      </div>

      <div className="space-y-1 px-3 pb-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-2 py-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="mt-2 h-3 w-32" />
            </div>
          ))
        ) : articles.length === 0 ? (
          <p className="px-2 py-4 text-center text-xs text-text-muted">No news available</p>
        ) : (
          articles.map((article, i) => (
            <motion.a
              key={article.id}
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
              className="block rounded-button px-2 py-3 transition-colors duration-150 hover:bg-bg-elevated"
            >
              <p className="text-sm leading-snug line-clamp-1">{article.title}</p>
              <div className="mt-1.5 flex items-center gap-2">
                <span className="text-xs text-text-muted">{article.source}</span>
                <span className="text-xs text-text-muted">&middot;</span>
                <span className="text-xs text-text-muted">{timeAgo(article.published_at)}</span>
                <Badge variant={SENTIMENT_VARIANTS[article.sentiment]} className="ml-auto text-[10px]">
                  {article.sentiment}
                </Badge>
              </div>
            </motion.a>
          ))
        )}
      </div>
    </div>
  )
}
