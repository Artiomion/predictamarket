"use client"

import { useEffect, useRef, useState } from "react"
import { createChart, type IChartApi, ColorType, CrosshairMode, CandlestickSeries, LineSeries } from "lightweight-charts"
import { colors } from "@/lib/design-tokens"
import { marketApi, forecastApi } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import type { PriceBar } from "@/types"

interface WalkForwardForecast {
  forecast_date: string
  current_close: number | null
  signal: string
  confidence: string
  full_curve: number[]
}

function addTradingDays(dateStr: string, days: number): string {
  const date = new Date(dateStr)
  let added = 0
  while (added < days) {
    date.setDate(date.getDate() + 1)
    const dow = date.getDay()
    if (dow !== 0 && dow !== 6) added++
  }
  return date.toISOString().split("T")[0]
}

// Accent color with varying opacity
function accentWithOpacity(index: number, total: number): string {
  const opacity = 1 - (index / total) * 0.7 // newest=1.0, oldest=0.3
  return `rgba(0, 212, 170, ${opacity})`
}

export function WalkForwardChart({ ticker }: { ticker: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [loading, setLoading] = useState(true)
  const [forecasts, setForecasts] = useState<WalkForwardForecast[]>([])
  const [history, setHistory] = useState<PriceBar[]>([])

  // Fetch data
  useEffect(() => {
    setLoading(true)
    Promise.all([
      marketApi.getHistory(ticker, { period: "3m" }),
      forecastApi.getWalkForward(ticker, { limit: 7 }),
    ])
      .then(([histRes, wfRes]) => {
        setHistory(histRes.data)
        setForecasts(wfRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ticker])

  // Render chart
  useEffect(() => {
    if (!containerRef.current || history.length === 0) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.bg.primary },
        textColor: colors.text.secondary,
        fontFamily: "'DM Sans', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.03)" },
        horzLines: { color: "rgba(255,255,255,0.03)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: colors.border.subtle,
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: { borderColor: colors.border.subtle },
      handleScroll: { vertTouchDrag: false },
    })

    chartRef.current = chart

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.success,
      downColor: colors.danger,
      wickUpColor: colors.success,
      wickDownColor: colors.danger,
      borderVisible: false,
    })

    candleSeries.setData(
      history.map((d) => ({ time: d.date, open: d.open, high: d.high, low: d.low, close: d.close }))
    )

    // Walk-forward forecast lines (oldest first so newest renders on top)
    const reversed = [...forecasts].reverse()
    reversed.forEach((fc, idx) => {
      if (!fc.full_curve || fc.full_curve.length === 0) return

      const lineColor = accentWithOpacity(reversed.length - 1 - idx, reversed.length)
      const isNewest = idx === reversed.length - 1

      const line = chart.addSeries(LineSeries, {
        color: lineColor,
        lineWidth: isNewest ? 2 : 1,
        lineStyle: 2, // dashed
        crosshairMarkerVisible: false,
        priceLineVisible: false,
        lastValueVisible: isNewest,
      })

      const startDate = fc.forecast_date
      const lineData = [
        { time: startDate, value: fc.current_close || fc.full_curve[0] },
        ...fc.full_curve.map((v, i) => ({
          time: addTradingDays(startDate, i + 1),
          value: v,
        })),
      ]

      line.setData(lineData)
    })

    chart.timeScale().fitContent()

    const container = containerRef.current
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.resize(entry.contentRect.width, 350)
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [history, forecasts])

  if (loading) {
    return <Skeleton className="h-[350px] rounded-card" />
  }

  if (forecasts.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-card border border-border-subtle bg-bg-surface">
        <p className="text-sm text-text-muted">Not enough forecast history for walk-forward view</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="h-[350px] w-full rounded-card border border-border-subtle overflow-hidden" />
      <div className="flex items-center gap-3 text-[10px] text-text-muted">
        {forecasts.slice(0, 5).map((fc, i) => (
          <div key={fc.forecast_date} className="flex items-center gap-1">
            <span
              className="inline-block size-2 rounded-full"
              style={{ backgroundColor: accentWithOpacity(i, forecasts.length) }}
            />
            <span>{new Date(fc.forecast_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
