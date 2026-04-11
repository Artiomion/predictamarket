"use client"

import { useEffect, useRef, useState } from "react"
import { createChart, type IChartApi, type ISeriesApi, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from "lightweight-charts"
import { cn } from "@/lib/utils"
import { mockPriceHistory } from "@/lib/mock-data"

const timeframes = [
  { id: "1D", label: "1D", count: 1 },
  { id: "1W", label: "1W", count: 5 },
  { id: "1M", label: "1M", count: 22 },
  { id: "3M", label: "3M", count: 999 },
] as const

type TimeframeId = (typeof timeframes)[number]["id"]

interface TooltipData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export function StockChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const [activeTimeframe, setActiveTimeframe] = useState<TimeframeId>("3M")
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0A0A0F" },
        textColor: "#6B6B80",
        fontFamily: "'DM Sans', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.03)" },
        horzLines: { color: "rgba(255,255,255,0.03)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: "#12121A" },
        horzLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: "#12121A" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.06)",
        scaleMargins: { top: 0.05, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.06)",
        timeVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#00FF88",
      downColor: "#FF3366",
      wickUpColor: "#00FF88",
      wickDownColor: "#FF3366",
      borderVisible: false,
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    })

    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candleRef.current = candleSeries
    volumeRef.current = volumeSeries

    // Crosshair tooltip
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData.size) {
        setTooltip(null)
        return
      }
      const candle = param.seriesData.get(candleSeries)
      if (candle && "open" in candle) {
        const bar = mockPriceHistory.find((b) => b.date === param.time)
        setTooltip({
          date: param.time as string,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: bar?.volume ?? 0,
        })
      }
    })

    // Resize observer
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.resize(width, width < 640 ? 300 : 400)
      }
    })
    const container = containerRef.current
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [])

  // Update data on timeframe change
  useEffect(() => {
    if (!candleRef.current || !volumeRef.current) return

    const tf = timeframes.find((t) => t.id === activeTimeframe)
    const data = mockPriceHistory.slice(-(tf?.count ?? 999))

    candleRef.current.setData(
      data.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    )

    volumeRef.current.setData(
      data.map((d) => ({
        time: d.date,
        value: d.volume,
        color: d.close >= d.open ? "rgba(0,255,136,0.3)" : "rgba(255,51,102,0.3)",
      }))
    )

    chartRef.current?.timeScale().fitContent()
  }, [activeTimeframe])

  return (
    <div className="space-y-3">
      {/* Timeframe buttons */}
      <div className="flex items-center gap-1">
        {timeframes.map((tf) => (
          <button
            key={tf.id}
            onClick={() => setActiveTimeframe(tf.id)}
            className={cn(
              "rounded-chip px-3 py-1 text-xs font-medium transition-colors duration-150",
              activeTimeframe === tf.id
                ? "bg-bg-elevated text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            )}
          >
            {tf.label}
          </button>
        ))}
      </div>

      {/* Chart container */}
      <div className="relative rounded-card border border-border-subtle overflow-hidden">
        {/* Tooltip overlay */}
        {tooltip && (
          <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-button border border-border-subtle bg-bg-surface/90 px-3 py-2 backdrop-blur-sm">
            <p className="text-xs text-text-muted">{tooltip.date}</p>
            <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
              <span className="text-text-muted">O</span>
              <span className="font-mono tabular-nums text-text-primary">{tooltip.open.toFixed(2)}</span>
              <span className="text-text-muted">H</span>
              <span className="font-mono tabular-nums text-text-primary">{tooltip.high.toFixed(2)}</span>
              <span className="text-text-muted">L</span>
              <span className="font-mono tabular-nums text-text-primary">{tooltip.low.toFixed(2)}</span>
              <span className="text-text-muted">C</span>
              <span className="font-mono tabular-nums text-text-primary">{tooltip.close.toFixed(2)}</span>
              <span className="text-text-muted">Vol</span>
              <span className="font-mono tabular-nums text-text-primary">
                {(tooltip.volume / 1_000_000).toFixed(1)}M
              </span>
            </div>
          </div>
        )}
        <div ref={containerRef} className="h-[400px] w-full max-sm:h-[300px]" />
      </div>
    </div>
  )
}
