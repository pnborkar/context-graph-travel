import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Provider } from "@/components/Provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "Expedia Context Graph",
  description: "GraphRAG-powered customer service intelligence for flight disruptions and refunds",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
