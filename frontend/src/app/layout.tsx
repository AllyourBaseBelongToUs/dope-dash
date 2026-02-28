import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { FeedbackPanel } from "@/components/feedback/FeedbackPanel";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Dope Dash - Multi-Agent Control Center",
  description: "Real-time monitoring and control for AI agent fleets",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {children}
        <Toaster />
        <FeedbackPanel />
      </body>
    </html>
  );
}
