"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
} from "lightweight-charts"
import { Maximize2, Minimize2 } from "lucide-react"
import { colors } from "@/lib/design-tokens"
import { marketApi } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  connectFinnhub,
  subscribeFinnhub,
  unsubscribeFinnhub,
  RESOLUTION_MS,
  type CandleBar,
} from "@/lib/finnhub"
import api from "@/lib/api"
import type { PriceBar } from "@/types"

interface TimeframeConfig {
  id: string
  label: string
  period: string        // for marketApi.getHistory
  resolution: string    // for Finnhub WS aggregation
}

const timeframes: TimeframeConfig[] = [
  { id: "1w",  label: "1W",  period: "1m",  resolution: "D" },
  { id: "1m",  label: "1M",  period: "1m",  resolution: "D" },
  { id: "3m",  label: "3M",  period: "3m",  resolution: "D" },
  { id: "6m",  label: "6M",  period: "6m",  resolution: "D" },
  { id: "1y",  label: "1Y",  period: "1y",  resolution: "D" },
  { id: "5y",  label: "5Y",  period: "5y",  resolution: "W" },
]

interface TooltipData {
  date: string
  open: number
  high: number
  low: number
  close: number
}

export function LiveChart({ ticker = "AAPL" }: { ticker?: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null)
  const [activeTimeframe, setActiveTimeframe] = useState<string>("3m")
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)
  const [loading, setLoading] = useState(true)
  const [fullscreen, setFullscreen] = useState(false)
  const [history, setHistory] = useState<PriceBar[]>([])
  const [livePrice, setLivePrice] = useState<number | null>(null)

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
        })
      }
    })

    const container = containerRef.current
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        const height = fullscreen ? window.innerHeight - 120 : (width < 640 ? 300 : 450)
        chart.resize(width, height)
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch candles from our API (yfinance data)
  useEffect(() => {
    if (!ticker) return
    const tf = timeframes.find((t) => t.id === activeTimeframe)
    setLoading(true)

    marketApi.getHistory(ticker, { period: tf?.period || "3m" })
      .then(({ data }) => {
        setHistory(data)
        if (candleRef.current && volumeRef.current && data.length > 0) {
          candleRef.current.setData(
            data.map((d) => ({ time: d.date as string, open: d.open, high: d.high, low: d.low, close: d.close }))
          )
          volumeRef.current.setData(
            data.map((d) => ({
              time: d.date as string,
              value: d.volume,
              color: d.close >= d.open ? "rgba(0,255,136,0.3)" : "rgba(255,51,102,0.3)",
            }))
          )
          chartRef.current?.timeScale().fitContent()
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ticker, activeTimeframe])

  // Finnhub WebSocket for real-time tick updates
  useEffect(() => {
    if (!ticker) return

    // Fetch WS token from authenticated endpoint
    let cancelled = false
    api.get("/api/finnhub/ws-token")
      .then(({ data }) => {
        if (cancelled || !data.token) return
        connectFinnhub(data.token)

        const resMs = RESOLUTION_MS["D"] || 86400000
        subscribeFinnhub(ticker, resMs, (candle: CandleBar) => {
          setLivePrice(candle.close)

          if (candleRef.current && history.length > 0) {
            const last = history[history.length - 1]
            candleRef.current.update({
              time: last.date as string,
              open: last.open,
              high: Math.max(last.high, candle.close),
              low: Math.min(last.low, candle.close),
              close: candle.close,
            })
            volumeRef.current?.update({
              time: last.date as string,
              value: last.volume,
              color: candle.close >= last.open ? "rgba(0,255,136,0.3)" : "rgba(255,51,102,0.3)",
            })
          }
        })
      })
      .catch(() => {}) // WS optional — chart works without it

    return () => {
      cancelled = true
      unsubscribeFinnhub()
    }
  }, [ticker, history])

  const toggleFullscreen = () => {
    setFullscreen(!fullscreen)
    setTimeout(() => {
      if (containerRef.current && chartRef.current) {
        const w = containerRef.current.clientWidth
        const h = !fullscreen ? window.innerHeight - 120 : 450
        chartRef.current.resize(w, h)
        chartRef.current.timeScale().fitContent()
      }
    }, 100)
  }

  return (
    <div className={cn(
      "space-y-3",
      fullscreen && "fixed inset-0 z-50 bg-bg-primary p-4"
    )}>
      {/* Toolbar */}
      <div className="flex items-center justify-between">
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
          {livePrice && (
            <span className="ml-3 text-xs text-success font-mono tabular-nums">
              LIVE ${livePrice.toFixed(2)}
            </span>
          )}
        </div>
        <button
          onClick={toggleFullscreen}
          className="rounded-button p-1.5 text-text-muted hover:bg-bg-elevated hover:text-text-secondary"
          title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
        >
          {fullscreen ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
        </button>
      </div>

      {/* Chart */}
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
          <div className="flex h-[450px] items-center justify-center">
            <p className="text-sm text-text-muted">No price history available</p>
          </div>
        ) : (
          <div
            ref={containerRef}
            className={cn(
              "w-full",
              fullscreen ? "h-[calc(100vh-120px)]" : "h-[450px] max-sm:h-[300px]"
            )}
          />
        )}
      </div>
    </div>
  )
}
