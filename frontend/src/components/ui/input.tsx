import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-button border border-border-subtle bg-bg-surface px-3 py-1 text-sm text-text-primary transition-colors duration-150 file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-text-muted focus:border-[var(--accent-from)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-from)]/50 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
})
Input.displayName = "Input"

export { Input }
