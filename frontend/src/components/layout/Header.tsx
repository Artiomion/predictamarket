"use client"

import { Menu, Search, Bell } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useUIStore } from "@/store/ui-store"
import { cn } from "@/lib/utils"

interface HeaderProps {
  title: string
  user: { name: string; tier: string; avatar: string | null }
  onMobileMenuToggle: () => void
}

export function Header({ title, user, onMobileMenuToggle }: HeaderProps) {
  const { setCommandPaletteOpen } = useUIStore()
  const tierColors: Record<string, string> = {
    free: "secondary",
    pro: "default",
    premium: "warning",
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center border-b border-border-subtle bg-bg-primary/80 backdrop-blur-md px-4 md:px-6">
      {/* Mobile menu button */}
      <button
        onClick={onMobileMenuToggle}
        className="mr-3 rounded-button p-1.5 text-text-muted hover:bg-bg-surface hover:text-text-secondary md:hidden"
      >
        <Menu className="size-5" />
      </button>

      {/* Breadcrumb / Page title */}
      <h1 className="font-heading text-base font-medium">{title}</h1>

      {/* Right section */}
      <div className="ml-auto flex items-center gap-2">
        {/* Search trigger */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="rounded-button p-2 text-text-muted transition-colors duration-150 hover:bg-bg-surface hover:text-text-secondary"
          title="Search (Cmd+K)"
        >
          <Search className="size-4" />
        </button>

        {/* Notifications */}
        <button className="relative rounded-button p-2 text-text-muted transition-colors duration-150 hover:bg-bg-surface hover:text-text-secondary">
          <Bell className="size-4" />
          <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-danger text-[10px] font-medium text-bg-primary">
            3
          </span>
        </button>

        {/* User avatar + tier */}
        <div className="flex items-center gap-2 rounded-button px-2 py-1.5 transition-colors duration-150 hover:bg-bg-surface">
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
        </div>
      </div>
    </header>
  )
}
