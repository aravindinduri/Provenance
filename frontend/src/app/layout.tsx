import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { QueryProvider } from "@/components/providers/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Provenance — Supply Chain Risk Intelligence",
  description: "Monitor supply-chain risk from regulatory and geopolitical signals.",
};

/**
 * Root layout — wraps the entire app in:
 *   1. ClerkProvider  (auth session, JWT)
 *   2. QueryProvider  (TanStack Query client)
 *
 * Both are required on all routes, so they live here at the root.
 * ClerkProvider must be the outermost wrapper per Clerk docs.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <body className="min-h-screen bg-background font-sans antialiased">
          <QueryProvider>{children}</QueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
