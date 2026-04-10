"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface TickerBadgeProps {
  ticker: string
  className?: string
}

export function TickerBadge({ ticker, className }: TickerBadgeProps) {
  return (
    <motion.span
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.97 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={cn(
        "inline-flex items-center rounded-chip border border-border-subtle bg-bg-elevated px-2 py-0.5 font-mono text-xs font-medium text-text-primary transition-colors duration-150 hover:border-border-hover",
        className
      )}
    >
      {ticker}
    </motion.span>
  )
}
