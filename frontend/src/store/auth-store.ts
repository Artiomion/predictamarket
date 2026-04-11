import { create } from "zustand"
import type { User } from "@/types"

function getStoredUser(): User | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem("pm_user")
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("pm_access_token")
}

function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("pm_refresh_token")
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  setUser: (user: User | null) => void
  setAuth: (token: string, refreshToken: string) => void
  logout: () => void
  hydrated: boolean
  hydrate: () => void
}

// Default mock user for development (used when no localStorage data)
const MOCK_USER: User = {
  id: "dbba3ca9-f491-48a9-a9e0-da4b7e0e5cd9",
  email: "demo@predictamarket.com",
  full_name: "Test User",
  avatar_url: null,
  tier: "free",
  is_active: true,
  is_verified: true,
  created_at: "2026-04-01T00:00:00Z",
}

export const useAuthStore = create<AuthState>((set) => ({
  user: MOCK_USER,
  token: "mock-jwt-token-for-dev",
  refreshToken: null,
  hydrated: false,

  hydrate: () => {
    const storedUser = getStoredUser()
    const storedToken = getStoredToken()
    const storedRefreshToken = getStoredRefreshToken()

    if (storedToken && storedUser) {
      set({ user: storedUser, token: storedToken, refreshToken: storedRefreshToken, hydrated: true })
    } else {
      // Keep mock user for dev mode
      set({ hydrated: true })
    }
  },

  setUser: (user) => {
    if (typeof window !== "undefined") {
      if (user) {
        localStorage.setItem("pm_user", JSON.stringify(user))
      } else {
        localStorage.removeItem("pm_user")
      }
    }
    set({ user })
  },

  setAuth: (token, refreshToken) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("pm_access_token", token)
      localStorage.setItem("pm_refresh_token", refreshToken)
    }
    set({ token, refreshToken })
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("pm_access_token")
      localStorage.removeItem("pm_refresh_token")
      localStorage.removeItem("pm_user")
      window.location.href = "/auth/login"
    }
    set({ user: null, token: null, refreshToken: null })
  },
}))
