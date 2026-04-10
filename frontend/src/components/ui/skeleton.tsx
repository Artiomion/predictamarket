import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "rounded-card bg-bg-elevated animate-shimmer bg-[length:200%_100%] bg-gradient-to-r from-bg-elevated via-[#25253A] to-bg-elevated",
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
