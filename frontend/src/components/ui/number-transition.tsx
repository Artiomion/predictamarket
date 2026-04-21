"use client"

import { useEffect, useRef } from "react"
import { useMotionValue, useTransform, animate } from "framer-motion"
import { cn } from "@/lib/utils"

interface NumberTransitionProps {
  value: number
  format?: "price" | "percent" | "number"
  duration?: number
  className?: string
}

function formatValue(n: number, format: string): string {
  if (format === "price") {
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  if (format === "percent") {
    const sign = n >= 0 ? "+" : ""
    return sign + n.toFixed(2) + "%"
  }
  return n.toLocaleString("en-US", { maximumFractionDigits: 2 })
}

export function NumberTransition({
  value,
  format = "number",
  duration = 0.3,
  className,
}: NumberTransitionProps) {
  const motionValue = useMotionValue(value)
  const displayed = useTransform(motionValue, (v) => formatValue(v, format))
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration,
      ease: "easeOut",
    })
    return controls.stop
  }, [value, motionValue, duration])

  useEffect(() => {
    const unsub = displayed.on("change", (v) => {
      if (ref.current) ref.current.textContent = v
    })
    return unsub
  }, [displayed])

  return (
    <span
      ref={ref}
      className={cn("font-mono tabular-nums", className)}
    >
      {formatValue(value, format)}
    </span>
  )
}
