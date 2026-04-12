import { io, Socket } from "socket.io-client"
import { toast } from "sonner"

let socket: Socket | null = null
let connectionCallbacks: ((connected: boolean) => void)[] = []

export function getSocket(): Socket | null {
  return socket
}

export function onConnectionChange(cb: (connected: boolean) => void) {
  connectionCallbacks.push(cb)
  return () => {
    connectionCallbacks = connectionCallbacks.filter((c) => c !== cb)
  }
}

function notifyConnection(connected: boolean) {
  connectionCallbacks.forEach((cb) => cb(connected))
}

export function initSocket(token?: string | null) {
  if (socket?.connected) return socket

  const url = process.env.NEXT_PUBLIC_WS_URL || "http://localhost:8006"

  socket = io(url, {
    query: token ? { token } : undefined,
    transports: ["websocket", "polling"],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
  })

  socket.on("connect", () => {
    notifyConnection(true)

    // Subscribe to user room if authenticated
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]))
        socket?.emit("subscribe_user", { user_id: payload.sub })
      } catch { /* invalid token */ }
    }
  })

  socket.on("disconnect", () => {
    notifyConnection(false)
    toast.error("Real-time updates paused", { duration: 3000 })
  })

  socket.on("reconnect", () => {
    notifyConnection(true)
    toast.success("Real-time updates resumed", { duration: 2000 })
  })

  // Global event handlers
  socket.on("forecast:ready", (data: { ticker: string; signal: string }) => {
    toast.success(`New forecast for ${data.ticker}: ${data.signal}`, { duration: 5000 })
  })

  socket.on("news:high_impact", (data: { title: string; tickers: string[] }) => {
    toast(data.title, { duration: 8000 })
  })

  socket.on("alert:triggered", (data: { ticker: string; message: string }) => {
    toast.warning(`Alert: ${data.message}`, { duration: 10000 })
  })

  socket.on("error", (data: { detail: string }) => {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Socket error:", data.detail)
    }
  })

  return socket
}

export function subscribeTicker(ticker: string) {
  socket?.emit("subscribe_ticker", { ticker })
}

export function unsubscribeTicker(ticker: string) {
  socket?.emit("unsubscribe_ticker", { ticker })
}

export function disconnectSocket() {
  socket?.disconnect()
  socket = null
}
