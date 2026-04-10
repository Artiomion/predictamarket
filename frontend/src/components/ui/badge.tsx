import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-chip border px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[rgba(0,212,170,0.12)] text-[var(--accent-from)]",
        secondary:
          "border-border-subtle bg-bg-elevated text-text-secondary",
        success:
          "border-transparent bg-[rgba(0,255,136,0.12)] text-success",
        danger:
          "border-transparent bg-[rgba(255,51,102,0.12)] text-danger",
        warning:
          "border-transparent bg-[rgba(255,184,0,0.12)] text-warning",
        outline:
          "border-border-subtle text-text-secondary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const Badge = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>
>(({ className, variant, ...props }, ref) => (
  <span
    ref={ref}
    className={cn(badgeVariants({ variant }), className)}
    {...props}
  />
))
Badge.displayName = "Badge"

export { Badge, badgeVariants }
