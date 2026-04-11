"use client"

import { useEffect, useRef } from "react"
import { cn } from "@/lib/utils"

interface SparkLineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
  color?: string
}

export function SparkLine({
  data,
  width = 80,
  height = 24,
  className,
  color,
}: SparkLineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const isPositive = data.length >= 2 && data[data.length - 1] >= data[0]
  const strokeColor = color || (isPositive ? "#00FF88" : "#FF3366")

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || data.length < 2) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    const stepX = width / (data.length - 1)

    ctx.clearRect(0, 0, width, height)
    ctx.beginPath()
    ctx.strokeStyle = strokeColor
    ctx.lineWidth = 1.5
    ctx.lineJoin = "round"
    ctx.lineCap = "round"

    data.forEach((value, i) => {
      const x = i * stepX
      const y = height - ((value - min) / range) * (height - 4) - 2
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })

    ctx.stroke()
  }, [data, width, height, strokeColor])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={cn("shrink-0", className)}
      style={{ width, height }}
    />
  )
}

export function generateSparkData(length = 20): number[] {
  const data: number[] = [100]
  for (let i = 1; i < length; i++) {
    data.push(data[i - 1] + (Math.random() - 0.48) * 3)
  }
  return data
}
