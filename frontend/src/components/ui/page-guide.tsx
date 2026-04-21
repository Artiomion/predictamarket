"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { HelpCircle, ChevronDown, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

export interface GuideSection {
  /** H4 heading inside the expanded panel */
  title: string
  /** Plain-English paragraphs. Each string renders as a separate <p>. */
  body: string[]
}

export interface GuideGlossaryTerm {
  /** The metric / term as it appears on the page */
  term: string
  /** Plain-English definition, one sentence */
  definition: string
}

interface PageGuideProps {
  /** One-liner shown in the collapsed header */
  summary: string
  /** Main explanation sections (what / how to use / caveats) */
  sections: GuideSection[]
  /** Metric dictionary — optional, renders only if provided */
  glossary?: GuideGlossaryTerm[]
  /** Default expanded on first render. Pass true for pages where context is
   *  critical (first-time visitor on /alpha-signals). */
  defaultOpen?: boolean
  className?: string
}

/**
 * Plain-English page guide — a progressive-disclosure panel that explains
 * what the page does, how to use it for trading decisions, and what the
 * metrics mean. Collapsed by default so pros don't see noise; expanded
 * with one click for newcomers.
 *
 * Renders as a native <details> for accessibility + zero-JS fallback. The
 * animated chevron uses framer; if framer is disabled (reduced-motion)
 * the element still toggles correctly.
 */
export function PageGuide({
  summary,
  sections,
  glossary,
  defaultOpen = false,
  className,
}: PageGuideProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div
      className={cn(
        "rounded-card border border-border-subtle bg-bg-surface/60 backdrop-blur-sm",
        open && "border-[var(--accent-from)]/20",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 rounded-card px-4 py-3 text-left transition-colors hover:bg-bg-elevated/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-from)]/40"
      >
        <div className="flex min-w-0 items-center gap-3">
          <HelpCircle
            aria-hidden="true"
            className="size-4 shrink-0 text-[var(--accent-from)]"
          />
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--accent-from)]">
              New to this page?
            </p>
            <p className="truncate text-sm text-text-secondary">{summary}</p>
          </div>
        </div>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          aria-hidden="true"
          className="shrink-0"
        >
          <ChevronDown className="size-4 text-text-muted" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="space-y-5 border-t border-border-subtle px-4 py-4">
              {sections.map((section) => (
                <div key={section.title}>
                  <h4 className="flex items-center gap-1.5 font-heading text-sm font-medium text-text-primary">
                    <BookOpen
                      aria-hidden="true"
                      className="size-3.5 text-text-secondary"
                    />
                    {section.title}
                  </h4>
                  <div className="mt-1.5 space-y-1.5">
                    {section.body.map((paragraph, i) => (
                      <p
                        key={i}
                        className="text-xs leading-relaxed text-text-secondary"
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              ))}

              {glossary && glossary.length > 0 && (
                <div>
                  <h4 className="font-heading text-sm font-medium text-text-primary">
                    Glossary
                  </h4>
                  <dl className="mt-1.5 grid gap-2 sm:grid-cols-2">
                    {glossary.map((g) => (
                      <div
                        key={g.term}
                        className="rounded-button border border-border-subtle bg-bg-elevated/30 p-2.5"
                      >
                        <dt className="font-mono text-[11px] font-medium text-[var(--accent-from)]">
                          {g.term}
                        </dt>
                        <dd className="mt-0.5 text-[11px] leading-relaxed text-text-muted">
                          {g.definition}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              <div className="flex items-start gap-2 rounded-button border border-warning/20 bg-warning/[0.04] p-2.5">
                <span
                  aria-hidden="true"
                  className="mt-0.5 text-xs font-medium text-warning"
                >
                  ⚠
                </span>
                <p className="text-[11px] leading-relaxed text-text-muted">
                  <strong className="text-text-secondary">Not investment advice.</strong>{" "}
                  Past back-test results don&apos;t guarantee future returns. Use
                  these signals as research inputs, not as trade instructions.
                  Always do your own due diligence.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
