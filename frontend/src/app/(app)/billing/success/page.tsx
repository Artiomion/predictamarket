"use client"

import { useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { CheckCircle2, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/store/auth-store"
import { authApi } from "@/lib/api"

export default function BillingSuccessPage() {
  const { setUser } = useAuthStore()
  const confettiDone = useRef(false)

  useEffect(() => {
    // Refresh user data to get new tier
    authApi.getMe()
      .then(({ data }) => setUser(data))
      .catch(() => {})

    // Confetti
    if (!confettiDone.current) {
      confettiDone.current = true
      import("canvas-confetti").then(({ default: confetti }) => {
        const end = Date.now() + 3000
        const fire = () => {
          confetti({
            particleCount: 3,
            angle: 60,
            spread: 55,
            origin: { x: 0 },
            colors: ["#00D4AA", "#00A3FF", "#00FF88"],
          })
          confetti({
            particleCount: 3,
            angle: 120,
            spread: 55,
            origin: { x: 1 },
            colors: ["#00D4AA", "#00A3FF", "#00FF88"],
          })
          if (Date.now() < end) requestAnimationFrame(fire)
        }
        fire()
      }).catch(() => {})
    }
  }, [setUser])

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="max-w-md text-center"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200, damping: 15 }}
        >
          <CheckCircle2 className="mx-auto size-16 text-success" />
        </motion.div>

        <h1 className="mt-6 font-heading text-3xl font-bold">Welcome aboard!</h1>
        <p className="mt-3 text-text-secondary">
          Your account has been upgraded. All premium features are now unlocked.
        </p>

        <Button
          variant="gradient"
          size="lg"
          className="mt-8 gap-2"
          onClick={() => { window.location.href = "/dashboard" }}
        >
          Go to Dashboard
          <ArrowRight className="size-4" />
        </Button>
      </motion.div>
    </div>
  )
}
