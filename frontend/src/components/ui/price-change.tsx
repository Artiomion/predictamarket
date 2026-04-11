"use client"

import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

interface PriceChangeProps {
  value: number | null | undefined
  prefix?: string
  className?: string
}

export function PriceChange({ value, prefix = "", className }: PriceChangeProps) {
  if (value == null) return <span className={cn("font-mono text-sm text-text-muted", className)}>—</span>
  const isPositive = value > 0
  const isZero = value === 0
  const formatted = `${isPositive ? "+" : ""}${value.toFixed(2)}%`

  return (
    <AnimatePresence mode="popLayout">
      <motion.span
        key={value}
        initial={{ opacity: 0, y: isPositive ? 4 : -4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: isPositive ? -4 : 4 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={cn(
          "font-mono text-sm font-medium tabular-nums",
          isZero && "text-text-secondary",
          isPositive && "text-[var(--success)]",
          !isPositive && !isZero && "text-[var(--danger)]",
          className
        )}
      >
        {prefix}{formatted}
      </motion.span>
    </AnimatePresence>
  )
}
