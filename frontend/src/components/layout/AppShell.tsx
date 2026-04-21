"use client"

import { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import { motion } from "framer-motion"
import { Sidebar } from "./Sidebar"
import { Header } from "./Header"
import { CommandPalette } from "./CommandPalette"
import { useAuthStore } from "@/store/auth-store"
import { useUIStore } from "@/store/ui-store"
import { initSocket, onConnectionChange } from "@/lib/socket"
import { cn } from "@/lib/utils"

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/dashboard": "Dashboard",
  "/top-picks": "Top Picks",
  "/alpha-signals": "Alpha Signals",
  "/stocks": "Stocks",
  "/portfolio": "Portfolio",
  "/watchlist": "Watchlist",
  "/news": "News",
  "/earnings": "Earnings",
  "/notifications": "Alerts",
  "/settings": "Settings",
  "/billing": "Billing",
  "/billing/success": "Billing",
  "/billing/cancel": "Billing",
}

// Fallback: turn "/some-slug/aapl" → "Some Slug / AAPL" so header never shows
// a raw URL segment even when we add a new route and forget to register a title.
function prettifyPath(path: string): string {
  const parts = path.split("/").filter(Boolean)
  if (!parts.length) return "PredictaMarket"
  return parts
    .map((seg) => {
      // Tickers are ≤ 5 chars (longest in catalog: "CMCSA"). Using ≤5 avoids
      // collision with the 6-char "stocks" segment being rendered as "STOCKS".
      // If the segment is short AND all alphabetic/punct, treat as ticker.
      const isTicker = seg.length <= 5 && /^[a-zA-Z.-]+$/.test(seg)
      if (isTicker) return seg.toUpperCase()
      return seg
        .split("-")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(" ")
    })
    .join(" / ")
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore()
  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.token)
  const pathname = usePathname()

  // Init WebSocket
  useEffect(() => {
    initSocket(token)
    return onConnectionChange(() => {})
  }, [token])

  const title = pageTitles[pathname] || prettifyPath(pathname)

  const headerUser = {
    name: user?.full_name ?? "User",
    tier: user?.tier ?? "free",
    avatar: user?.avatar_url ?? null,
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
      />

      <div className={cn(
        "transition-[padding-left] duration-200 ease-out",
        sidebarCollapsed ? "md:pl-16" : "md:pl-60"
      )}>
        <Header
          title={title}
          user={headerUser}
          onMobileMenuToggle={() => setMobileOpen(!mobileOpen)}
        />
        <main className="p-4 md:p-6">
          <motion.div
            key={pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
          >
            {children}
          </motion.div>
        </main>
      </div>

      <CommandPalette />
    </div>
  )
}
