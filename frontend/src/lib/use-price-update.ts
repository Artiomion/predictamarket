"use client"

import { useState, useEffect, useRef } from "react"
import { getSocket, subscribeTicker, unsubscribeTicker } from "./socket"

interface PriceUpdate {
  ticker: string
  price: number
  change: number
  change_pct: number
}

export function usePriceUpdate(ticker: string, initialPrice?: number, initialChangePct?: number) {
  const [price, setPrice] = useState(initialPrice ?? 0)
  const [changePct, setChangePct] = useState(initialChangePct ?? 0)
  const [flash, setFlash] = useState<"up" | "down" | null>(null)
  const prevPrice = useRef(initialPrice ?? 0)

  useEffect(() => {
    if (initialPrice != null) {
      setPrice(initialPrice)
      prevPrice.current = initialPrice
    }
    if (initialChangePct != null) setChangePct(initialChangePct)
  }, [initialPrice, initialChangePct])

  useEffect(() => {
    subscribeTicker(ticker)

    const socket = getSocket()
    if (!socket) return

    const handler = (data: PriceUpdate) => {
      if (data.ticker !== ticker) return

      const direction = data.price > prevPrice.current ? "up" : data.price < prevPrice.current ? "down" : null
      prevPrice.current = data.price
      setPrice(data.price)
      setChangePct(data.change_pct)

      if (direction) {
        setFlash(direction)
        setTimeout(() => setFlash(null), 300)
      }
    }

    socket.on("price:update", handler)

    return () => {
      socket.off("price:update", handler)
      unsubscribeTicker(ticker)
    }
  }, [ticker])

  return { price, changePct, flash }
}
