import type { Metadata } from "next";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "PredictaMarket — AI Stock Predictions",
  description: "AI-powered stock predictions for S&P 500. Temporal Fusion Transformer model with 99.5% confident signal win rate.",
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
      </body>
    </html>
  );
}
