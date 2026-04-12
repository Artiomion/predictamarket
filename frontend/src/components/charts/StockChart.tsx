"use client"

import { useEffect, useRef, useState } from "react"
import { createChart, type IChartApi, type ISeriesApi, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from "lightweight-charts"
import { cn } from "@/lib/utils"
import { colors } from "@/lib/design-tokens"
import { marketApi } from "@/lib/api"
import { getSocket, subscribeTicker, unsubscribeTicker } from "@/lib/socket"
import type { PriceBar } from "@/types"

const timeframes = [
  { id: "1m", label: "1M", period: "1m" },
  { id: "3m", label: "3M", period: "3m" },
  { id: "6m", label: "6M", period: "6m" },
  { id: "1y", label: "1Y", period: "1y" },
  { id: "5y", label: "5Y", period: "5y" },
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

interface StockChartProps {
  ticker?: string
}

export function StockChart({ ticker = "AAPL" }: StockChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const [activeTimeframe, setActiveTimeframe] = useState<TimeframeId>("3m")
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState<PriceBar[]>([])

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return

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
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: colors.bg.surface },
        horzLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: colors.bg.surface },
      },
      rightPriceScale: {
        borderColor: colors.border.subtle,
        scaleMargins: { top: 0.05, bottom: 0.25 },
      },
      timeScale: {
        borderColor: colors.border.subtle,
        timeVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.success,
      downColor: colors.danger,
      wickUpColor: colors.success,
      wickDownColor: colors.danger,
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

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData.size) {
        setTooltip(null)
        return
      }
      const candle = param.seriesData.get(candleSeries)
      if (candle && "open" in candle) {
        setTooltip({
          date: param.time as string,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: 0,
        })
      }
    })

    const container = containerRef.current
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.resize(width, width < 640 ? 300 : 400)
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [])

  // Fetch data on ticker/timeframe change
  useEffect(() => {
    if (!ticker) return
    const tf = timeframes.find((t) => t.id === activeTimeframe)
    setLoading(true)

    marketApi.getHistory(ticker, { period: tf?.period || "3m" })
      .then(({ data }) => {
        setHistory(data)
        if (candleRef.current && volumeRef.current && data.length > 0) {
          candleRef.current.setData(
            data.map((d) => ({ time: d.date, open: d.open, high: d.high, low: d.low, close: d.close }))
          )
          volumeRef.current.setData(
            data.map((d) => ({
              time: d.date,
              value: d.volume,
              color: d.close >= d.open ? "rgba(0,255,136,0.3)" : "rgba(255,51,102,0.3)",
            }))
          )
          chartRef.current?.timeScale().fitContent()
        }
      })
      .catch(() => {
        // Keep existing data if fetch fails
      })
      .finally(() => setLoading(false))
  }, [ticker, activeTimeframe])

  // Real-time price updates via WebSocket → update last candle
  useEffect(() => {
    if (!ticker) return

    subscribeTicker(ticker)
    const socket = getSocket()
    if (!socket) return

    const handler = (data: { ticker: string; price: number }) => {
      if (data.ticker !== ticker || !candleRef.current || !volumeRef.current) return

      const last = history[history.length - 1]
      if (!last) return

      const updatedCandle = {
        time: last.date,
        open: last.open,
        high: Math.max(last.high, data.price),
        low: Math.min(last.low, data.price),
        close: data.price,
      }

      candleRef.current.update(updatedCandle)
      volumeRef.current.update({
        time: last.date,
        value: last.volume,
        color: data.price >= last.open ? "rgba(0,255,136,0.3)" : "rgba(255,51,102,0.3)",
      })
    }

    socket.on("price:update", handler)

    return () => {
      socket.off("price:update", handler)
      unsubscribeTicker(ticker)
    }
  }, [ticker, history])

  return (
    <div className="space-y-3">
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
        {loading && <span className="ml-2 text-xs text-text-muted">Loading...</span>}
      </div>

      <div className="relative rounded-card border border-border-subtle overflow-hidden">
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
            </div>
          </div>
        )}
        {history.length === 0 && !loading ? (
          <div className="flex h-[400px] items-center justify-center">
            <p className="text-sm text-text-muted">No price history available</p>
          </div>
        ) : (
          <div ref={containerRef} className="h-[400px] w-full max-sm:h-[300px]" />
        )}
      </div>
    </div>
  )
}
