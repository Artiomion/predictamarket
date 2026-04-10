import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // shadcn semantic colors (mapped to our CSS vars)
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: { DEFAULT: "var(--card)", foreground: "var(--card-foreground)" },
        popover: { DEFAULT: "var(--popover)", foreground: "var(--popover-foreground)" },
        primary: { DEFAULT: "var(--primary)", foreground: "var(--primary-foreground)" },
        secondary: { DEFAULT: "var(--secondary)", foreground: "var(--secondary-foreground)" },
        muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-foreground)" },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
          from: "var(--accent-from)",
          to: "var(--accent-to)",
        },
        destructive: "var(--destructive)",
        border: {
          DEFAULT: "var(--border)",
          subtle: "var(--border-subtle)",
          hover: "var(--border-hover)",
        },
        input: "var(--input)",
        ring: "var(--ring)",

        // PredictaMarket custom
        bg: {
          primary: "var(--bg-primary)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
        },
        success: "var(--success)",
        danger: "var(--danger)",
        warning: "var(--warning)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        chip: "var(--radius-chip)",
        button: "var(--radius-button)",
        card: "var(--radius-card)",
        modal: "var(--radius-modal)",
      },
      boxShadow: {
        "glow-accent": "0 0 20px rgba(0, 212, 170, 0.15)",
        "glow-success": "0 0 20px rgba(0, 255, 136, 0.15)",
        "glow-danger": "0 0 20px rgba(255, 51, 102, 0.15)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s ease-in-out infinite",
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
