"use client"

import { useState } from "react"
import { usePathname } from "next/navigation"
import { Sidebar } from "./Sidebar"
import { Header } from "./Header"
import { cn } from "@/lib/utils"

const mockUser = {
  name: "Test User",
  tier: "free",
  avatar: null,
}

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
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  const title = pageTitles[pathname] || pathname.split("/").pop() || "PredictaMarket"

  return (
    <div className="min-h-screen bg-bg-primary">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        collapsed={collapsed}
        onCollapsedChange={setCollapsed}
      />

      <div className={cn(
        "transition-[padding-left] duration-200 ease-out",
        collapsed ? "md:pl-16" : "md:pl-60"
      )}>
        <Header
          title={title}
          user={mockUser}
          onMobileMenuToggle={() => setMobileOpen(!mobileOpen)}
        />
        <main className="p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
