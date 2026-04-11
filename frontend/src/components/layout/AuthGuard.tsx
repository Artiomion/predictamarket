"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Skeleton } from "@/components/ui/skeleton"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/store/auth-store"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, setUser, hydrate, hydrated } = useAuthStore()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    if (!hydrated) return

    const check = async () => {
      const storedToken = typeof window !== "undefined" ? localStorage.getItem("pm_access_token") : null

      if (!storedToken) {
        router.replace("/auth/login")
        return
      }

      // If we have a token but no user, fetch profile
      if (!user) {
        try {
          const { data } = await authApi.getMe()
          setUser(data)
        } catch {
          // Token expired and refresh failed — interceptor redirects to login
          return
        }
      }

      setChecking(false)
    }

    check()
  }, [hydrated, user, router, setUser])

  if (!hydrated || checking) {
    return (
      <div className="min-h-screen bg-bg-primary p-6">
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-32" />
          <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-card" />
            ))}
          </div>
          <Skeleton className="mt-8 h-64 rounded-card" />
        </div>
      </div>
    )
  }

  return <>{children}</>
}
