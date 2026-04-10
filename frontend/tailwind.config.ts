import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "var(--bg-primary)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
        },
        accent: {
          from: "var(--accent-from)",
          to: "var(--accent-to)",
        },
        success: "var(--success)",
        danger: "var(--danger)",
        warning: "var(--warning)",
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        border: {
          subtle: "var(--border-subtle)",
          hover: "var(--border-hover)",
        },
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
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
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
