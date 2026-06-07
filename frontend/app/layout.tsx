import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "TradeSense — Behavioral Analytics for Investors",
    template: "%s | TradeSense",
  },
  description:
    "Turn your trading history into behavioral intelligence. Detect disposition effect, overtrading, concentration risk, and get personalized coaching.",
  keywords: ["behavioral finance", "trading analytics", "investor behavior", "portfolio analysis"],
  authors: [{ name: "TradeSense" }],
  openGraph: {
    title: "TradeSense — Behavioral Analytics for Investors",
    description: "Turn Trading History Into Behavioral Intelligence.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-slate-900 text-slate-100 font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
