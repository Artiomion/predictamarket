"use client"

import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import type { Signal, Confidence } from "@/types"

const signalConfig = {
  BUY: {
    bg: "bg-[rgba(0,255,136,0.12)]",
    text: "text-success",
    glow: "group-hover:shadow-glow-success",
  },
  SELL: {
    bg: "bg-[rgba(255,51,102,0.12)]",
    text: "text-danger",
    glow: "group-hover:shadow-glow-danger",
  },
  HOLD: {
    bg: "bg-[rgba(255,184,0,0.12)]",
    text: "text-warning",
    glow: "",
  },
} as const

interface SignalBadgeProps {
  signal: Signal
  confidence?: Confidence
  showWinRate?: boolean
  className?: string
}

export function SignalBadge({ signal, confidence, showWinRate, className }: SignalBadgeProps) {
  const config = signalConfig[signal]
  const isHighConfidence = confidence === "HIGH"

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: [0.9, 1.1, 1], opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut", times: [0, 0.5, 1] }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.97 }}
      style={{ willChange: "transform" }}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-chip px-2 py-0.5 text-xs font-medium font-mono transition-shadow duration-150",
        config.bg,
        config.text,
        config.glow,
        className
      )}
    >
      {/* Display label — "SELL" is internal signal value but we label it AVOID
          in UI because the back-tested short strategy loses money. AVOID =
          "don't buy", not "short". Same underlying data, honest framing. */}
      {signal === "BUY" ? "▲ BUY" : signal === "SELL" ? "▽ AVOID" : signal}
      {isHighConfidence && showWinRate && signal === "BUY" && (
        <span className="text-[10px] opacity-75" title="Consensus BUY back-test: 63% win rate on 27 trades (single test window)">
          63% WR
        </span>
      )}
      {confidence && (
        <span className="text-[10px] opacity-60">{confidence}</span>
      )}
    </motion.span>
  )
}
