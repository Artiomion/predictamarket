import { create } from "zustand"
import type { User } from "@/types"

interface AuthState {
  user: User | null
  token: string | null
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: {
    id: "dbba3ca9-f491-48a9-a9e0-da4b7e0e5cd9",
    email: "demo@predictamarket.com",
    full_name: "Test User",
    avatar_url: null,
    tier: "free",
    is_active: true,
    is_verified: true,
    created_at: "2026-04-01T00:00:00Z",
  },
  token: "mock-jwt-token-for-dev",
  setUser: (user) => set({ user }),
  setToken: (token) => set({ token }),
  logout: () => set({ user: null, token: null }),
}))
