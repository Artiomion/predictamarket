"use client"

import { useEffect, useRef, useState } from "react"
import { createChart, type IChartApi, ColorType, CrosshairMode, CandlestickSeries, LineSeries, AreaSeries, LineStyle } from "lightweight-charts"
import { colors } from "@/lib/design-tokens"
import { marketApi } from "@/lib/api"
import type { Forecast, PriceBar } from "@/types"

interface ForecastChartProps {
  forecast: Forecast
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

export function ForecastChart({ forecast }: ForecastChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [history, setHistory] = useState<PriceBar[]>([])

  useEffect(() => {
    marketApi.getHistory(forecast.ticker, { period: "3m" })
      .then(({ data }) => setHistory(data))
      .catch(() => {})
  }, [forecast.ticker])

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
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: colors.bg.surface },
        horzLine: { color: "rgba(255,255,255,0.2)", labelBackgroundColor: colors.bg.surface },
      },
      rightPriceScale: { borderColor: colors.border.subtle },
      timeScale: { borderColor: colors.border.subtle, timeVisible: false },
      handleScroll: { vertTouchDrag: false },
    })

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

    const lastDate = history[history.length - 1].date
    const forecastLine = chart.addSeries(LineSeries, {
      color: colors.accent.from,
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    const forecastDates = forecast.full_curve.map((_, i) => addTradingDays(lastDate, i + 1))
    forecastLine.setData([
      { time: lastDate, value: forecast.current_close },
      ...forecast.full_curve.map((v, i) => ({ time: forecastDates[i], value: v })),
    ])

    const ci80 = chart.addSeries(AreaSeries, {
      lineWidth: 1,
      topColor: "rgba(0,212,170,0.08)",
      bottomColor: "rgba(0,212,170,0.02)",
      lineColor: "rgba(0,212,170,0.1)",
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    const ciData80 = forecastDates.map((date, i) => {
      const progress = i / (forecast.full_curve.length - 1)
      const upper = forecast.forecast["1d"].upper_80 + (forecast.forecast["1m"].upper_80 - forecast.forecast["1d"].upper_80) * progress
      return { time: date, value: upper }
    })
    ci80.setData(ciData80)

    chart.timeScale().fitContent()
    chartRef.current = chart

    const container = containerRef.current
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.resize(width, width < 640 ? 280 : 360)
      }
    })
    if (container) observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [forecast, history])

  return (
    <div className="rounded-card border border-border-subtle overflow-hidden">
      {history.length === 0 ? (
        <div className="flex h-[360px] items-center justify-center">
          <p className="text-sm text-text-muted">Loading chart...</p>
        </div>
      ) : (
        <div ref={containerRef} className="h-[360px] w-full max-sm:h-[280px]" />
      )}
    </div>
  )
}
