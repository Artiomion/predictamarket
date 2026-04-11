"use client"

import { motion } from "framer-motion"
import { Users } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { formatValue } from "@/lib/formatters"
import { mockInsiderTransactions } from "@/lib/mock-data"

export function InsidersTab({ ticker }: { ticker: string }) {
  const transactions = mockInsiderTransactions
    .filter((t) => t.ticker === ticker)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  if (transactions.length === 0) {
    return (
      <div className="flex min-h-[30vh] items-center justify-center rounded-card border border-dashed border-border-subtle">
        <div className="text-center">
          <Users className="mx-auto size-5 text-text-muted" />
          <p className="mt-3 text-sm text-text-muted">No insider transactions found for {ticker}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-card border border-border-subtle bg-bg-surface overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-subtle">
            <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Name</th>
            <th className="hidden px-4 py-3 text-left text-xs font-medium text-text-muted sm:table-cell">Title</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-text-muted">Type</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Shares</th>
            <th className="hidden px-4 py-3 text-right text-xs font-medium text-text-muted md:table-cell">Price</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Value</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-text-muted">Date</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t, i) => (
            <motion.tr
              key={`${t.insider_name}-${t.date}`}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3, ease: "easeOut" }}
              className="border-b border-border-subtle last:border-b-0"
            >
              <td className="px-4 py-3 font-medium">{t.insider_name}</td>
              <td className="hidden px-4 py-3 text-text-secondary sm:table-cell">{t.title}</td>
              <td className="px-4 py-3">
                <Badge variant={t.transaction_type === "buy" ? "success" : "danger"} className="text-[10px]">
                  {t.transaction_type.toUpperCase()}
                </Badge>
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">
                {t.shares.toLocaleString("en-US")}
              </td>
              <td className="hidden px-4 py-3 text-right font-mono text-xs tabular-nums text-text-secondary md:table-cell">
                ${t.price.toFixed(2)}
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">
                {formatValue(t.total_value)}
              </td>
              <td className="px-4 py-3 text-right text-xs text-text-muted">
                {new Date(t.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
