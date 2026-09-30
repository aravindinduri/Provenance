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

import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useQuery } from "@tanstack/react-query";
import { fetchMe, type MeOut } from "@/lib/api/me";

export const ME_QUERY_KEY = ["auth", "me"] as const;

export const MOCK_DEV_ME: MeOut = {
  user_id: "usr_dev_risk_lead",
  email: "risk.lead@provenance.internal",
  org_id: "org_dev_acme_corp",
  clerk_org_id: null,
  role: "org_admin",
  persona: "risk_manager",
  assigned_categories: ["electronics", "optics", "rare_earths"],
  organization: {
    id: "org_dev_acme_corp",
    clerk_org_id: "org_dev_clerk_123",
    name: "Acme Industrial Group",
    slug: "acme-industrial",
    company_id: null,
    industry: "High-Tech Manufacturing",
    country: "US",
    subscription_tier: "enterprise",
    monthly_token_budget: 500000,
    onboarding_completed_at: "2026-09-01T00:00:00Z",
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
  },
};

export function useMe() {
  const { getToken, isSignedIn } = useAppAuth();

  return useQuery<MeOut, Error>({
    queryKey: ME_QUERY_KEY,
    enabled: !!isSignedIn,
    staleTime: 5 * 60 * 1000, // 5 min
    gcTime: 10 * 60 * 1000,
    queryFn: async () => {
      try {
        const token = await getToken();
        if (!token) return MOCK_DEV_ME;
        return await fetchMe(token);
      } catch (err) {
        if (process.env.NODE_ENV !== "production") {
          console.info("Using mock dev user in development:", err);
          return MOCK_DEV_ME;
        }
        throw err;
      }
    },
  });
}

