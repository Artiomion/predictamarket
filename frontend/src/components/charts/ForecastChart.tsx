"use client"

import { useEffect, useRef } from "react"
import { createChart, type IChartApi, ColorType, CrosshairMode, CandlestickSeries, LineSeries, AreaSeries, LineStyle } from "lightweight-charts"
import { mockPriceHistory } from "@/lib/mock-data"
import type { Forecast } from "@/types"

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
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.06)",
        timeVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    })

    // Candlestick series (historical data)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#00FF88",
      downColor: "#FF3366",
      wickUpColor: "#00FF88",
      wickDownColor: "#FF3366",
      borderVisible: false,
    })

    candleSeries.setData(
      mockPriceHistory.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    )

    // Forecast line (dashed, starts from last candle)
    const lastDate = mockPriceHistory[mockPriceHistory.length - 1].date
    const forecastLine = chart.addSeries(LineSeries, {
      color: "#00D4AA",
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

    // 80% CI band
    const ci80 = chart.addSeries(AreaSeries, {
      lineWidth: 1,
      topColor: "rgba(0,212,170,0.08)",
      bottomColor: "rgba(0,212,170,0.02)",
      lineColor: "rgba(0,212,170,0.1)",
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    })

    // Simple CI approximation: interpolate between forecast points
    const ciData80 = forecastDates.map((date, i) => {
      const progress = i / (forecast.full_curve.length - 1)
      const lower = forecast.forecast["1d"].lower_80 + (forecast.forecast["1m"].lower_80 - forecast.forecast["1d"].lower_80) * progress
      const upper = forecast.forecast["1d"].upper_80 + (forecast.forecast["1m"].upper_80 - forecast.forecast["1d"].upper_80) * progress
      return { time: date, value: upper, lower }
    })

    ci80.setData(ciData80.map((d) => ({ time: d.time, value: d.value })))

    chart.timeScale().fitContent()
    chartRef.current = chart

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        chart.resize(width, width < 640 ? 280 : 360)
      }
    })
    const container = containerRef.current
    if (container) observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
    }
  }, [forecast])

  return (
    <div className="rounded-card border border-border-subtle overflow-hidden">
      <div ref={containerRef} className="h-[360px] w-full max-sm:h-[280px]" />
    </div>
  )
}
