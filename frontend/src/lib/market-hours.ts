/**
 * US stock market hours utility.
 * All calculations in America/New_York (ET) timezone.
 */

export type MarketPhase = "open" | "pre-market" | "after-hours" | "closed"

export interface MarketStatus {
  phase: MarketPhase
  label: string
  nextEvent: string          // "Market Opens" | "Market Closes" | "Pre-Market Opens" | etc.
  nextEventTime: Date
  countdownMs: number
}

// ET market schedule (minutes from midnight)
const PRE_MARKET_OPEN = 4 * 60           // 04:00
const MARKET_OPEN = 9 * 60 + 30          // 09:30
const MARKET_CLOSE = 16 * 60             // 16:00
const AFTER_HOURS_CLOSE = 20 * 60        // 20:00

function toET(date: Date): { hours: number; minutes: number; dayOfWeek: number; minuteOfDay: number } {
  const et = new Date(date.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const hours = et.getHours()
  const minutes = et.getMinutes()
  return {
    hours,
    minutes,
    dayOfWeek: et.getDay(), // 0=Sun, 6=Sat
    minuteOfDay: hours * 60 + minutes,
  }
}

function nextWeekdayET(now: Date, targetDay: number, targetMinute: number): Date {
  const et = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const currentDay = et.getDay()
  let daysAhead = targetDay - currentDay
  if (daysAhead <= 0) daysAhead += 7

  const target = new Date(et)
  target.setDate(target.getDate() + daysAhead)
  target.setHours(Math.floor(targetMinute / 60), targetMinute % 60, 0, 0)

  // Convert back: difference in ms from ET target to ET now, apply to real now
  const etNow = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const diffMs = target.getTime() - etNow.getTime()
  return new Date(now.getTime() + diffMs)
}

function todayET(now: Date, targetMinute: number): Date {
  const et = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const target = new Date(et)
  target.setHours(Math.floor(targetMinute / 60), targetMinute % 60, 0, 0)
  const diffMs = target.getTime() - et.getTime()
  return new Date(now.getTime() + diffMs)
}

function tomorrowET(now: Date, targetMinute: number): Date {
  const et = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))
  const target = new Date(et)
  target.setDate(target.getDate() + 1)
  target.setHours(Math.floor(targetMinute / 60), targetMinute % 60, 0, 0)
  const diffMs = target.getTime() - et.getTime()
  return new Date(now.getTime() + diffMs)
}

export function getMarketStatus(now: Date = new Date()): MarketStatus {
  const { minuteOfDay, dayOfWeek } = toET(now)
  const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5

  // Weekend
  if (!isWeekday) {
    const nextOpen = nextWeekdayET(now, 1, MARKET_OPEN) // Next Monday 9:30
    return {
      phase: "closed",
      label: "Market Closed",
      nextEvent: "Opens Monday",
      nextEventTime: nextOpen,
      countdownMs: nextOpen.getTime() - now.getTime(),
    }
  }

  // Weekday: before pre-market (00:00 - 04:00)
  if (minuteOfDay < PRE_MARKET_OPEN) {
    const nextOpen = todayET(now, PRE_MARKET_OPEN)
    return {
      phase: "closed",
      label: "Market Closed",
      nextEvent: "Pre-Market Opens",
      nextEventTime: nextOpen,
      countdownMs: nextOpen.getTime() - now.getTime(),
    }
  }

  // Pre-market (04:00 - 09:30)
  if (minuteOfDay < MARKET_OPEN) {
    const nextOpen = todayET(now, MARKET_OPEN)
    return {
      phase: "pre-market",
      label: "Pre-Market",
      nextEvent: "Market Opens",
      nextEventTime: nextOpen,
      countdownMs: nextOpen.getTime() - now.getTime(),
    }
  }

  // Regular hours (09:30 - 16:00)
  if (minuteOfDay < MARKET_CLOSE) {
    const close = todayET(now, MARKET_CLOSE)
    return {
      phase: "open",
      label: "Market Open",
      nextEvent: "Closes",
      nextEventTime: close,
      countdownMs: close.getTime() - now.getTime(),
    }
  }

  // After-hours (16:00 - 20:00)
  if (minuteOfDay < AFTER_HOURS_CLOSE) {
    const ahClose = todayET(now, AFTER_HOURS_CLOSE)
    return {
      phase: "after-hours",
      label: "After-Hours",
      nextEvent: "Session Ends",
      nextEventTime: ahClose,
      countdownMs: ahClose.getTime() - now.getTime(),
    }
  }

  // After after-hours (20:00 - 23:59), weekday
  if (dayOfWeek === 5) {
    // Friday evening → Monday
    const nextOpen = nextWeekdayET(now, 1, MARKET_OPEN)
    return {
      phase: "closed",
      label: "Market Closed",
      nextEvent: "Opens Monday",
      nextEventTime: nextOpen,
      countdownMs: nextOpen.getTime() - now.getTime(),
    }
  }

  const nextPre = tomorrowET(now, PRE_MARKET_OPEN)
  return {
    phase: "closed",
    label: "Market Closed",
    nextEvent: "Pre-Market Opens",
    nextEventTime: nextPre,
    countdownMs: nextPre.getTime() - now.getTime(),
  }
}

export function formatCountdownCompact(ms: number): string {
  if (ms <= 0) return "now"
  const totalSec = Math.floor(ms / 1000)
  const days = Math.floor(totalSec / 86400)
  const hours = Math.floor((totalSec % 86400) / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m ${seconds}s`
}
