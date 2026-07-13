import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/Navigation";
import { publicResume } from "@/lib/content";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: `${publicResume.basics.name} | Data Science, AI, Applied Math`,
  description:
    "Static-first portfolio for data science, AI, applied mathematics, and quantitative finance work.",
  keywords: [
    "portfolio",
    "data science",
    "machine learning",
    "quantitative finance",
    "applied mathematics",
  ],
  authors: [{ name: publicResume.basics.name }],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-slate-50 text-slate-950">
          <Navigation />
          <main className="container mx-auto px-4 py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
