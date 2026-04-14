"use client"

import { motion } from "framer-motion"
import { XCircle, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export default function BillingCancelPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-md text-center"
      >
        <XCircle className="mx-auto size-12 text-text-muted" />

        <h1 className="mt-6 font-heading text-2xl font-semibold">Checkout cancelled</h1>
        <p className="mt-2 text-sm text-text-secondary">
          No charges were made. You can upgrade anytime.
        </p>

        <Link href="/billing">
          <Button variant="outline" className="mt-6 gap-2">
            <ArrowLeft className="size-4" />
            Back to Plans
          </Button>
        </Link>
      </motion.div>
    </div>
  )
}
