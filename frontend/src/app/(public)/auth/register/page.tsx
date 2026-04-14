"use client"

import { useState } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { Eye, EyeOff } from "lucide-react"
import { toast } from "sonner"
import { GoogleButton } from "@/components/auth/GoogleButton"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { authApi } from "@/lib/api"
import { useAuthStore } from "@/store/auth-store"

export default function RegisterPage() {
  const { setUser, setAuth } = useAuthStore()
  const [googleLoading, setGoogleLoading] = useState(false)

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const validate = () => {
    const errs: Record<string, string> = {}
    if (!name.trim()) errs.name = "Name is required"
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = "Invalid email"
    if (password.length < 8) errs.password = "Password must be at least 8 characters"
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      const { data } = await authApi.register({ email, password, name })
      setAuth(data.access_token, data.refresh_token)

      // Fetch user profile
      const { data: user } = await authApi.getMe()
      setUser(user)

      window.location.href = "/dashboard"
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } }
      if (error.response?.status === 400) {
        toast.error("An account with this email already exists")
      } else if (error.response?.status === 422) {
        const detail = error.response.data?.detail
        if (typeof detail === "string") {
          setErrors({ form: detail })
        } else {
          setErrors({ form: "Please check your input" })
        }
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 pt-16">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="w-full max-w-[420px]"
      >
        <div className="rounded-modal border border-border-subtle bg-bg-surface p-8">
          <div className="flex items-center justify-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-button bg-gradient-to-br from-accent-from to-accent-to font-heading text-sm font-bold text-bg-primary">
              PM
            </span>
            <span className="font-heading text-base font-semibold">PredictaMarket</span>
          </div>

          <h1 className="mt-6 text-center font-heading text-xl font-semibold">
            Create your account
          </h1>
          <p className="mt-1.5 text-center text-sm text-text-secondary">
            Start predicting S&P 500 stocks for free
          </p>

          <GoogleButton loading={googleLoading} onLogin={async (access_token) => {
            setGoogleLoading(true)
            localStorage.removeItem("pm_access_token")
            localStorage.removeItem("pm_refresh_token")
            try {
              const { data } = await authApi.google({ access_token })
              setAuth(data.access_token, data.refresh_token)
              const { data: user } = await authApi.getMe()
              setUser(user)
              window.location.href = "/dashboard"
            } catch {
              toast.error("Google sign-in failed")
              setGoogleLoading(false)
            }
          }} />

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border-subtle" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-bg-surface px-3 text-xs text-text-muted">or</span>
            </div>
          </div>

          {errors.form && (
            <p className="mb-4 text-center text-xs text-danger">{errors.form}</p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="mb-1.5 block text-sm text-text-secondary">Name</label>
              <Input
                id="name"
                placeholder="John Doe"
                value={name}
                onChange={(e) => { setName(e.target.value); setErrors((p) => ({ ...p, name: "" })) }}
                className={errors.name ? "border-danger" : ""}
              />
              {errors.name && <p className="mt-1 text-xs text-danger">{errors.name}</p>}
            </div>

            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm text-text-secondary">Email</label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setErrors((p) => ({ ...p, email: "" })) }}
                className={errors.email ? "border-danger" : ""}
              />
              {errors.email && <p className="mt-1 text-xs text-danger">{errors.email}</p>}
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm text-text-secondary">Password</label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Min. 8 characters"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: "" })) }}
                  className={errors.password ? "border-danger pr-10" : "pr-10"}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-danger">{errors.password}</p>}
            </div>

            <Button
              type="submit"
              variant="gradient"
              className="w-full"
              disabled={loading}
            >
              {loading ? "Creating account..." : "Create Account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-text-muted">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-[var(--accent-from)] hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
