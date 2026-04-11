"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { timeAgo } from "@/lib/formatters"
import { SENTIMENT_VARIANTS } from "@/lib/constants"
import { mockNews } from "@/lib/mock-data"

export function MarketNews() {
  const articles = mockNews.slice(0, 3)

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface">
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <h2 className="font-heading text-base font-medium">Market News</h2>
        <Link
          href="/news"
          className="text-xs text-text-muted transition-colors hover:text-[var(--accent-from)]"
        >
          View all
        </Link>
      </div>

      <div className="space-y-1 px-3 pb-3">
        {articles.map((article, i) => (
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
        ))}
      </div>
    </div>
  )
}
