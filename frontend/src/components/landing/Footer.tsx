import Link from "next/link"

const navColumns = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "Pricing", href: "#pricing" },
      { label: "API Docs", href: "#" },
      { label: "Blog", href: "#" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Contact", href: "#" },
      { label: "Careers", href: "#" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "#" },
      { label: "Terms of Service", href: "#" },
      { label: "Disclaimer", href: "#" },
    ],
  },
] as const

export function Footer() {
  return (
    <footer className="border-t border-border-subtle bg-bg-primary px-4 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-button bg-gradient-to-br from-accent-from to-accent-to font-heading text-xs font-bold text-bg-primary">
                PM
              </span>
              <span className="font-heading text-sm font-semibold">PredictaMarket</span>
            </Link>
            <p className="mt-3 text-xs text-text-muted leading-relaxed max-w-xs">
              AI-powered stock predictions for S&P 500 using Temporal Fusion Transformer.
            </p>
          </div>

          {/* Nav columns */}
          {navColumns.map((col) => (
            <div key={col.title}>
              <h4 className="text-xs font-medium uppercase tracking-wider text-text-muted">
                {col.title}
              </h4>
              <ul className="mt-3 space-y-2">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="mt-12 border-t border-border-subtle pt-6 flex flex-col items-center gap-2 md:flex-row md:justify-between">
          <p className="text-xs text-text-muted">
            &copy; 2026 PredictaMarket. All rights reserved.
          </p>
          <p className="text-xs text-text-muted text-center md:text-right max-w-md">
            Past performance does not guarantee future results. This is not investment advice.
          </p>
        </div>
      </div>
    </footer>
  )
}
