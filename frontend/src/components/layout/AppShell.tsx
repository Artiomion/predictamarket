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
  "/stocks": "Stocks",
  "/portfolio": "Portfolio",
  "/watchlist": "Watchlist",
  "/news": "News",
  "/earnings": "Earnings",
  "/notifications": "Notifications",
  "/settings": "Settings",
  "/billing": "Billing",
  "/billing/success": "Billing",
  "/billing/cancel": "Billing",
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

  const title = pageTitles[pathname] || pathname.split("/").pop() || "PredictaMarket"

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
