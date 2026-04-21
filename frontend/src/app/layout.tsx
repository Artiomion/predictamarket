import type { Metadata } from "next";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "PredictaMarket — AI Stock Predictions",
  description: "AI-powered stock predictions for 346 S&P 500 stocks. Temporal Fusion Transformer with 3-model ensemble consensus — 63% win rate on high-conviction signals.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <TooltipProvider>{children}</TooltipProvider>
          <Toaster
            theme="dark"
            toastOptions={{
              style: {
                background: "#12121A",
                border: "1px solid rgba(255,255,255,0.06)",
                color: "#E8E8ED",
                fontFamily: "'DM Sans', sans-serif",
              },
            }}
          />
      </body>
    </html>
  );
}
