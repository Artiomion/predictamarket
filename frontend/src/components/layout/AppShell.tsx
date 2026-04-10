"use client"

import { useState } from "react"
import { usePathname } from "next/navigation"
import { Sidebar } from "./Sidebar"
import { Header } from "./Header"
import { CommandPalette } from "./CommandPalette"
import { useAuthStore } from "@/store/auth-store"
import { useUIStore } from "@/store/ui-store"
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
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore()
  const user = useAuthStore((s) => s.user)
  const pathname = usePathname()

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
          {children}
        </main>
      </div>

      <CommandPalette />
    </div>
  )
}
