"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Command } from "cmdk"
import { motion, AnimatePresence } from "framer-motion"
import {
  BarChart3,
  LayoutDashboard,
  Briefcase,
  Star,
  Search,
} from "lucide-react"
import { useUIStore } from "@/store/ui-store"

const mockTickers = [
  { ticker: "AAPL", name: "Apple Inc." },
  { ticker: "MSFT", name: "Microsoft Corporation" },
  { ticker: "GOOGL", name: "Alphabet Inc." },
  { ticker: "AMZN", name: "Amazon.com Inc." },
  { ticker: "NVDA", name: "NVIDIA Corporation" },
  { ticker: "TSLA", name: "Tesla Inc." },
  { ticker: "META", name: "Meta Platforms Inc." },
  { ticker: "JPM", name: "JPMorgan Chase & Co." },
  { ticker: "V", name: "Visa Inc." },
  { ticker: "JNJ", name: "Johnson & Johnson" },
] as const

const pages = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/watchlist", label: "Watchlist", icon: Star },
] as const

export function CommandPalette() {
  const router = useRouter()
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  const navigateTo = (href: string) => {
    setCommandPaletteOpen(false)
    router.push(href)
  }

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={() => setCommandPaletteOpen(false)}
          />
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="w-full max-w-lg"
            >
              <Command
                className="rounded-modal border border-border-subtle bg-bg-surface text-text-primary overflow-hidden"
                label="Command Palette"
              >
                <div className="flex items-center gap-2 border-b border-border-subtle px-4">
                  <Search className="size-4 shrink-0 text-text-muted" />
                  <Command.Input
                    placeholder="Search tickers, pages..."
                    className="h-12 w-full bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
                  />
                  <kbd className="hidden shrink-0 rounded-chip border border-border-subtle bg-bg-elevated px-1.5 py-0.5 font-mono text-[10px] text-text-muted sm:inline-block">
                    ESC
                  </kbd>
                </div>

                <Command.List className="max-h-72 overflow-y-auto p-2">
                  <Command.Empty className="py-6 text-center text-sm text-text-muted">
                    No results found.
                  </Command.Empty>

                  <Command.Group
                    heading="Stocks"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-muted"
                  >
                    {mockTickers.map((t) => (
                      <Command.Item
                        key={t.ticker}
                        value={`${t.ticker} ${t.name}`}
                        onSelect={() => navigateTo(`/stocks/${t.ticker}`)}
                        className="flex cursor-pointer items-center gap-3 rounded-button px-2 py-2 text-sm text-text-secondary transition-colors duration-100 aria-selected:bg-bg-elevated aria-selected:text-text-primary"
                      >
                        <BarChart3 className="size-4 shrink-0 text-text-muted" />
                        <span className="font-mono text-xs text-text-primary">{t.ticker}</span>
                        <span className="text-text-secondary">{t.name}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>

                  <Command.Separator className="my-2 h-px bg-border-subtle" />

                  <Command.Group
                    heading="Pages"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-muted"
                  >
                    {pages.map((p) => {
                      const Icon = p.icon
                      return (
                        <Command.Item
                          key={p.href}
                          value={p.label}
                          onSelect={() => navigateTo(p.href)}
                          className="flex cursor-pointer items-center gap-3 rounded-button px-2 py-2 text-sm text-text-secondary transition-colors duration-100 aria-selected:bg-bg-elevated aria-selected:text-text-primary"
                        >
                          <Icon className="size-4 shrink-0 text-text-muted" />
                          <span>{p.label}</span>
                        </Command.Item>
                      )
                    })}
                  </Command.Group>
                </Command.List>
              </Command>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
