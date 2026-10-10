/**
 * src/lib/hooks/use-me.ts — TanStack Query hook for /v1/auth/me.
 *
 * Fetches the current user's backend profile (org UUID, role, persona) using
 * the authentication session token as a Bearer credential.
 *
 * ZERO DUMMY DATA: All user and organization context is fetched directly
 * from the live backend API.
 */

"use client";

import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useQuery } from "@tanstack/react-query";
import { fetchMe, type MeOut } from "@/lib/api/me";

export const ME_QUERY_KEY = ["auth", "me"] as const;

export function useMe() {
  const { getToken, isSignedIn } = useAppAuth();

  return useQuery<MeOut | null, Error>({
    queryKey: ME_QUERY_KEY,
    enabled: !!isSignedIn,
    staleTime: 5 * 60 * 1000, // 5 min
    gcTime: 10 * 60 * 1000,
    queryFn: async () => {
      const token = await getToken();
      if (!token) return null;
      return await fetchMe(token);
    },
  });
}
