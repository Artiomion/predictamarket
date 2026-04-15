"use client"

import { useEffect, useRef, useState, useMemo } from "react"
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
  const svgRef = useRef<SVGSVGElement>(null)
  const [inView, setInView] = useState(false)

  const isPositive = data.length >= 2 && data[data.length - 1] >= data[0]
  const strokeColor = color || (isPositive ? "#00FF88" : "#FF3366")

  const points = useMemo(() => {
    if (data.length < 2) return ""
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    const stepX = width / (data.length - 1)

    return data
      .map((value, i) => {
        const x = i * stepX
        const y = height - ((value - min) / range) * (height - 4) - 2
        return `${x},${y}`
      })
      .join(" ")
  }, [data, width, height])

  // IntersectionObserver for draw-on-scroll
  useEffect(() => {
    const el = svgRef.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          observer.disconnect()
        }
      },
      { threshold: 0.3 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Calculate path length for stroke-dashoffset animation
  const polylineRef = useRef<SVGPolylineElement>(null)
  const [pathLength, setPathLength] = useState(0)

  useEffect(() => {
    if (polylineRef.current) {
      setPathLength(polylineRef.current.getTotalLength())
    }
  }, [points])

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className={cn("shrink-0", className)}
      viewBox={`0 0 ${width} ${height}`}
    >
      <polyline
        ref={polylineRef}
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        style={
          pathLength > 0
            ? {
                strokeDasharray: pathLength,
                strokeDashoffset: inView ? 0 : pathLength,
                transition: "stroke-dashoffset 600ms ease-out",
              }
            : undefined
        }
      />
    </svg>
  )
}

export function generateSparkData(length = 20): number[] {
  const data: number[] = [100]
  for (let i = 1; i < length; i++) {
    data.push(data[i - 1] + (Math.random() - 0.48) * 3)
  }
  return data
}
