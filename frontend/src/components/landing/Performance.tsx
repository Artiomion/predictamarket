"use client"

import { useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"

const metrics = [
  { end: 99.5, suffix: "%", label: "Win Rate", decimals: 1 },
  { end: 77.7, suffix: "%", label: "Avg Return", decimals: 1 },
  { end: 94, suffix: "", label: "S&P 500 Stocks", decimals: 0 },
  { end: 107, suffix: "", label: "Data Signals", decimals: 0 },
] as const

function CountUp({ end, suffix, decimals, started }: { end: number; suffix: string; decimals: number; started: boolean }) {
  const [value, setValue] = useState(0)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    if (!started) return
    const duration = 1500
    const startTime = performance.now()

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(eased * end)
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [started, end])

  return (
    <span className="font-mono text-4xl font-medium tabular-nums md:text-5xl">
      {value.toFixed(decimals)}{suffix}
    </span>
  )
}

export function Performance() {
  const ref = useRef<HTMLDivElement>(null)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true)
          observer.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <section className="py-24 px-4">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center"
        >
          <h2 className="font-heading text-3xl font-semibold md:text-4xl">
            Model Performance
          </h2>
          <p className="mt-3 text-text-secondary">
            Backtested on S&P 500 data from Nov 2024 — Apr 2026
          </p>
        </motion.div>

        <div
          ref={ref}
          className="mt-16 grid grid-cols-2 gap-8 md:grid-cols-4"
        >
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4, ease: "easeOut" }}
              className="text-center"
            >
              <CountUp end={m.end} suffix={m.suffix} decimals={m.decimals} started={started} />
              <p className="mt-2 text-sm text-text-muted">{m.label}</p>
            </motion.div>
          ))}
        </div>

        <p className="mt-12 text-center text-xs text-text-muted">
          Past performance does not guarantee future results. Single test period, not rolling.
        </p>
      </div>
    </section>
  )
}
