"use client"

import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { SignalBadge } from "@/components/ui/signal-badge"
import { PriceChange } from "@/components/ui/price-change"
import { TickerBadge } from "@/components/ui/ticker-badge"

export default function Home() {
  return (
    <main className="min-h-screen p-8 md:p-16 space-y-12">
      {/* Header */}
      <div>
        <h1 className="font-heading text-4xl font-bold tracking-tight">
          PredictaMarket
        </h1>
        <p className="mt-2 text-text-secondary">
          Design System — Component Showcase
        </p>
      </div>

      {/* Typography */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Typography</h2>
        <div className="space-y-2">
          <h1 className="font-heading text-4xl font-bold">Space Grotesk — Heading 1</h1>
          <h2 className="font-heading text-2xl font-semibold">Space Grotesk — Heading 2</h2>
          <h3 className="font-heading text-xl font-medium">Space Grotesk — Heading 3</h3>
          <p className="font-body text-text-primary">DM Sans — Body text primary</p>
          <p className="font-body text-text-secondary">DM Sans — Body text secondary</p>
          <p className="font-body text-text-muted">DM Sans — Body text muted</p>
          <p className="font-mono text-sm">JetBrains Mono — $1,234.56 +5.23% AAPL</p>
        </div>
      </section>

      {/* Buttons */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Buttons</h2>
        <div className="flex flex-wrap gap-3">
          <Button variant="default">Default</Button>
          <Button variant="gradient">Gradient CTA</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="link">Link</Button>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button variant="gradient" size="sm">Small</Button>
          <Button variant="gradient" size="default">Default</Button>
          <Button variant="gradient" size="lg">Large</Button>
        </div>
      </section>

      {/* Badges */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Badges</h2>
        <div className="flex flex-wrap gap-3">
          <Badge variant="default">Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="danger">Danger</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="outline">Outline</Badge>
        </div>
      </section>

      {/* Signal Badges */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Signal Badges</h2>
        <div className="flex flex-wrap gap-3 items-center">
          <SignalBadge signal="BUY" confidence="HIGH" showWinRate />
          <SignalBadge signal="BUY" confidence="MEDIUM" />
          <SignalBadge signal="SELL" confidence="HIGH" />
          <SignalBadge signal="SELL" confidence="MEDIUM" />
          <SignalBadge signal="HOLD" confidence="LOW" />
        </div>
      </section>

      {/* Price & Ticker */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Price & Ticker</h2>
        <div className="flex flex-wrap gap-6 items-center">
          <div className="flex items-center gap-3">
            <TickerBadge ticker="AAPL" />
            <span className="font-mono text-lg">$260.49</span>
            <PriceChange value={-0.38} />
          </div>
          <div className="flex items-center gap-3">
            <TickerBadge ticker="NVDA" />
            <span className="font-mono text-lg">$188.85</span>
            <PriceChange value={2.95} />
          </div>
          <div className="flex items-center gap-3">
            <TickerBadge ticker="MSFT" />
            <span className="font-mono text-lg">$371.14</span>
            <PriceChange value={0.87} />
          </div>
        </div>
      </section>

      {/* Cards */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Cards</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>AAPL — Apple Inc.</CardTitle>
              <CardDescription>Technology / Consumer Electronics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl">$260.49</span>
                <PriceChange value={-0.38} />
              </div>
              <div className="mt-3">
                <SignalBadge signal="SELL" confidence="MEDIUM" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>NVDA — NVIDIA Corp.</CardTitle>
              <CardDescription>Technology / Semiconductors</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl">$188.85</span>
                <PriceChange value={2.95} />
              </div>
              <div className="mt-3">
                <SignalBadge signal="BUY" confidence="HIGH" showWinRate />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>JPM — JPMorgan Chase</CardTitle>
              <CardDescription>Financial Services / Banks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl">$248.50</span>
                <PriceChange value={0.71} />
              </div>
              <div className="mt-3">
                <SignalBadge signal="BUY" confidence="MEDIUM" />
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Input */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Input</h2>
        <div className="max-w-sm space-y-3">
          <Input placeholder="Search tickers... (e.g. AAPL)" />
          <Input placeholder="Email address" type="email" />
        </div>
      </section>

      {/* Skeleton */}
      <section className="space-y-4">
        <h2 className="font-heading text-2xl font-semibold">Skeleton Loading</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-24" />
              <Skeleton className="mt-3 h-5 w-16" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-36" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-28" />
              <Skeleton className="mt-3 h-5 w-20" />
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
