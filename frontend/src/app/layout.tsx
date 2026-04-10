import type { Metadata } from "next";
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
        {children}
      </body>
    </html>
  );
}
