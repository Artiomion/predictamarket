"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center rounded-button text-sm font-medium whitespace-nowrap transition-all duration-150 ease-out outline-none select-none focus-visible:ring-2 focus-visible:ring-[var(--accent-from)]/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--accent-from)] text-[#0A0A0F] font-semibold hover:shadow-glow-accent active:translate-y-px",
        gradient:
          "bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] text-[#0A0A0F] font-semibold border border-[var(--accent-from)]/20 hover:shadow-glow-accent active:translate-y-px",
        outline:
          "border border-border-subtle bg-transparent text-text-primary hover:border-border-hover hover:bg-bg-elevated active:translate-y-px",
        secondary:
          "bg-bg-elevated text-text-primary border border-border-subtle hover:border-border-hover active:translate-y-px",
        ghost:
          "text-text-secondary hover:text-text-primary hover:bg-bg-elevated active:translate-y-px",
        destructive:
          "bg-[var(--danger)]/10 text-[var(--danger)] border border-[var(--danger)]/20 hover:bg-[var(--danger)]/20 active:translate-y-px",
        link: "text-[var(--accent-from)] underline-offset-4 hover:underline p-0 h-auto",
      },
      size: {
        default: "h-9 gap-2 px-4",
        sm: "h-7 gap-1.5 px-3 text-xs",
        lg: "h-11 gap-2 px-6 text-base",
        icon: "size-9",
        "icon-sm": "size-7",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>
>(({ className, variant, size, ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button, buttonVariants }
