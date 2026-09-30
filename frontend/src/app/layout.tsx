import type { Metadata } from "next";
import { ClerkProviderWrapper } from "@/lib/auth/clerk-adapter";
import { QueryProvider } from "@/components/providers/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Provenance — Supply Chain Risk Intelligence",
  description: "Monitor supply-chain risk from regulatory and geopolitical signals.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProviderWrapper>
      <html lang="en" suppressHydrationWarning>
        <body className="min-h-screen bg-background font-sans antialiased">
          <QueryProvider>{children}</QueryProvider>
        </body>
      </html>
    </ClerkProviderWrapper>
  );
}
