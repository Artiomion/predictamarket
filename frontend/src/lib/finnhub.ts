/**
 * Finnhub WebSocket client for real-time trade data.
 * Aggregates ticks into OHLCV candles at the specified resolution.
 */

const FINNHUB_WS_URL = "wss://ws.finnhub.io"

export interface FinnhubTrade {
  s: string   // symbol
  p: number   // price
  t: number   // timestamp ms
  v: number   // volume
}

export interface CandleBar {
  time: number  // unix seconds
  open: number
  high: number
  low: number
  close: number
  volume: number
}

type OnCandleUpdate = (candle: CandleBar) => void

let ws: WebSocket | null = null
let subscribedSymbol: string | null = null
let onUpdate: OnCandleUpdate | null = null
let currentResolutionMs: number = 60000  // 1 minute default
let currentCandle: CandleBar | null = null

function getCandleStart(timestampMs: number, resMs: number): number {
  return Math.floor(timestampMs / resMs) * Math.floor(resMs / 1000)
}

function processTrade(trade: FinnhubTrade) {
  if (!onUpdate) return

  const candleStartSec = getCandleStart(trade.t, currentResolutionMs)

  if (!currentCandle || currentCandle.time !== candleStartSec) {
    // New candle period
    currentCandle = {
      time: candleStartSec,
      open: trade.p,
      high: trade.p,
      low: trade.p,
      close: trade.p,
      volume: trade.v,
    }
  } else {
    // Update existing candle
    currentCandle.high = Math.max(currentCandle.high, trade.p)
    currentCandle.low = Math.min(currentCandle.low, trade.p)
    currentCandle.close = trade.p
    currentCandle.volume += trade.v
  }

  onUpdate({ ...currentCandle })
}

export function connectFinnhub(token: string) {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  ws = new WebSocket(`${FINNHUB_WS_URL}?token=${token}`)

  ws.onopen = () => {
    if (subscribedSymbol && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "subscribe", symbol: subscribedSymbol }))
    }
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === "trade" && msg.data) {
        for (const trade of msg.data) {
          if (trade.s === subscribedSymbol) {
            processTrade(trade)
          }
        }
      }
    } catch { /* ignore parse errors */ }
  }

  ws.onclose = () => {
    // Reconnect after 3 seconds
    setTimeout(() => {
      if (subscribedSymbol) connectFinnhub(token)
    }, 3000)
  }
}

export function subscribeFinnhub(
  symbol: string,
  resolutionMs: number,
  callback: OnCandleUpdate,
) {
  // Unsubscribe previous
  if (subscribedSymbol && ws?.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify({ type: "unsubscribe", symbol: subscribedSymbol })) } catch { /* ignore */ }
  }

  subscribedSymbol = symbol.toUpperCase()
  currentResolutionMs = resolutionMs
  currentCandle = null
  onUpdate = callback

  if (ws?.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify({ type: "subscribe", symbol: subscribedSymbol })) } catch { /* ignore */ }
  }
}

export function unsubscribeFinnhub() {
  if (subscribedSymbol && ws?.readyState === WebSocket.OPEN) {
    try { ws.send(JSON.stringify({ type: "unsubscribe", symbol: subscribedSymbol })) } catch { /* ignore */ }
  }
  subscribedSymbol = null
  onUpdate = null
  currentCandle = null
}

export function disconnectFinnhub() {
  unsubscribeFinnhub()
  ws?.close()
  ws = null
}

// Resolution label → milliseconds for candle aggregation
export const RESOLUTION_MS: Record<string, number> = {
  "1": 60_000,
  "5": 300_000,
  "15": 900_000,
  "30": 1_800_000,
  "60": 3_600_000,
  "D": 86_400_000,
  "W": 604_800_000,
}
