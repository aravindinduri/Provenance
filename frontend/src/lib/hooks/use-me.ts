/**
 * src/lib/hooks/use-me.ts — TanStack Query hook for /v1/auth/me.
 *
 * Fetches the current user's backend profile (org UUID, role, persona) using
 * the Clerk session token as a Bearer credential.
 *
 * Usage:
 *   const { data: me, isLoading } = useMe();
 *   if (me?.role === "org_admin") { ... }
 */

"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { fetchMe, type MeOut } from "@/lib/api/me";

export const ME_QUERY_KEY = ["auth", "me"] as const;

export function useMe() {
  const { getToken, isSignedIn } = useAuth();

  return useQuery<MeOut, Error>({
    queryKey: ME_QUERY_KEY,
    enabled: !!isSignedIn,
    staleTime: 5 * 60 * 1000,   // 5 min — role/org rarely change mid-session
    gcTime: 10 * 60 * 1000,     // 10 min cache
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("No Clerk session token available");
      return fetchMe(token);
    },
  });
}
