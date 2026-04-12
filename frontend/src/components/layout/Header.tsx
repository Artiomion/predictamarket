"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { Menu, Search, Bell, LogOut, Settings } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useUIStore } from "@/store/ui-store"
import { useAuthStore } from "@/store/auth-store"
import { notificationApi } from "@/lib/api"
import { cn } from "@/lib/utils"

interface HeaderProps {
  title: string
  user: { name: string; tier: string; avatar: string | null }
  onMobileMenuToggle: () => void
  socketConnected?: boolean
}

export function Header({ title, user, onMobileMenuToggle, socketConnected = false }: HeaderProps) {
  const { setCommandPaletteOpen } = useUIStore()
  const logout = useAuthStore((s) => s.logout)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [alertCount, setAlertCount] = useState(0)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    notificationApi.getAlerts({ limit: 50 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setAlertCount(list.filter((a) => a.is_active && !a.is_triggered).length)
      })
      .catch(() => {})
  }, [])

  const tierColors: Record<string, string> = {
    free: "secondary",
    pro: "default",
    premium: "warning",
  }

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside)
      return () => document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [dropdownOpen])

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center border-b border-border-subtle bg-bg-primary/80 backdrop-blur-md px-4 md:px-6">
      <button
        onClick={onMobileMenuToggle}
        className="mr-3 rounded-button p-1.5 text-text-muted hover:bg-bg-surface hover:text-text-secondary md:hidden"
      >
        <Menu className="size-5" />
      </button>

      <div className="flex items-center gap-2">
        <h1 className="font-heading text-base font-medium">{title}</h1>
        <span
          className={cn(
            "size-1.5 rounded-full",
            socketConnected ? "bg-success" : "bg-danger"
          )}
          title={socketConnected ? "Real-time connected" : "Real-time disconnected"}
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="rounded-button p-2 text-text-muted transition-colors duration-150 hover:bg-bg-surface hover:text-text-secondary"
          title="Search (Cmd+K)"
        >
          <Search className="size-4" />
        </button>

        <Link href="/notifications" className="relative rounded-button p-2 text-text-muted transition-colors duration-150 hover:bg-bg-surface hover:text-text-secondary">
          <Bell className="size-4" />
          {alertCount > 0 && (
            <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-danger text-[10px] font-medium text-bg-primary">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </Link>

        {/* User avatar + dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 rounded-button px-2 py-1.5 transition-colors duration-150 hover:bg-bg-surface"
          >
            <div className={cn(
              "flex size-7 items-center justify-center rounded-full text-xs font-medium",
              user.avatar ? "" : "bg-bg-elevated text-text-secondary"
            )}>
              {user.avatar ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={user.avatar} alt={user.name} className="size-7 rounded-full" />
              ) : (
                user.name.charAt(0).toUpperCase()
              )}
            </div>
            <Badge variant={tierColors[user.tier] as "secondary" | "default" | "warning"}>
              {user.tier.toUpperCase()}
            </Badge>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 rounded-card border border-border-subtle bg-bg-surface py-1">
              <div className="border-b border-border-subtle px-3 py-2">
                <p className="text-sm font-medium">{user.name}</p>
                <p className="text-xs text-text-muted">{user.tier} plan</p>
              </div>
              <button
                onClick={() => { setDropdownOpen(false) }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-elevated"
              >
                <Settings className="size-3.5" />
                Settings
              </button>
              <button
                onClick={() => { setDropdownOpen(false); logout() }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-danger transition-colors hover:bg-bg-elevated"
              >
                <LogOut className="size-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
