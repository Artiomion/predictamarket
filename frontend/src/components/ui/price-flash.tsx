"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

interface PriceFlashProps {
  flash: "up" | "down" | null
  children: React.ReactNode
  className?: string
}

export function PriceFlash({ flash, children, className }: PriceFlashProps) {
  const [activeFlash, setActiveFlash] = useState<"up" | "down" | null>(null)

  useEffect(() => {
    if (flash) {
      setActiveFlash(flash)
      const timer = setTimeout(() => setActiveFlash(null), 300)
      return () => clearTimeout(timer)
    }
  }, [flash])

  return (
    <span className={cn("relative inline-flex", className)}>
      <AnimatePresence>
        {activeFlash && (
          <motion.span
            initial={{ opacity: 0.2 }}
            animate={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className={cn(
              "absolute inset-0 rounded-chip",
              activeFlash === "up" ? "bg-success" : "bg-danger",
            )}
          />
        )}
      </AnimatePresence>
      {children}
    </span>
  )
}
