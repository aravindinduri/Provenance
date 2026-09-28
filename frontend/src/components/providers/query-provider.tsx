"use client";

/**
 * src/components/providers/query-provider.tsx
 *
 * Wraps the app in TanStack Query's QueryClientProvider.
 * Must be a Client Component because QueryClient uses browser APIs.
 * Placed here rather than in layout.tsx to keep layouts as Server Components.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useRef } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  // useRef ensures we get one QueryClient per component instance, not one
  // shared across the module — important for SSR/test isolation.
  const clientRef = useRef<QueryClient | null>(null);
  if (clientRef.current === null) {
    clientRef.current = new QueryClient({
      defaultOptions: {
        queries: {
          // Don't refetch on window focus for data-heavy views
          refetchOnWindowFocus: false,
          // Retry once on failure before showing an error
          retry: 1,
        },
      },
    });
  }

  return (
    <QueryClientProvider client={clientRef.current}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
