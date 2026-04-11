"use client"

import { cn } from "@/lib/utils"

interface FilterChipProps<T extends string> {
  options: { id: T; label: string }[]
  value: T
  onChange: (value: T) => void
  label?: string
}

export function FilterChip<T extends string>({ options, value, onChange, label }: FilterChipProps<T>) {
  return (
    <div className="flex items-center gap-1">
      {label && <span className="mr-1 shrink-0 text-xs text-text-muted">{label}:</span>}
      {options.map((opt) => (
        <button
          key={opt.id}
          onClick={() => onChange(opt.id)}
          className={cn(
            "shrink-0 rounded-chip px-2.5 py-1 text-xs font-medium transition-colors duration-150",
            value === opt.id
              ? "bg-bg-elevated text-text-primary"
              : "text-text-muted hover:text-text-secondary"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
