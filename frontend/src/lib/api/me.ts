/**
 * src/lib/api/me.ts — /v1/auth/me API types and fetcher.
 *
 * Types here mirror the backend MeOut / OrganizationOut schemas exactly.
 * When generated.ts exists (Phase 5) these will be replaced by the generated
 * types; the hook in use-me.ts is written against this interface, not generated.ts,
 * so the swap is one-file change.
 */

export interface OrganizationOut {
  id: string;
  clerk_org_id: string;
  name: string;
  slug: string;
  company_id: string | null;
  industry: string | null;
  country: string | null;
  subscription_tier: string;
  monthly_token_budget: number;
  onboarding_completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeOut {
  user_id: string;
  email: string | null;
  org_id: string | null;
  clerk_org_id: string | null;
  role: string;
  persona: string | null;
  assigned_categories: string[];
  organization: OrganizationOut | null;
}

/** Fetch the current user from the backend. Throws on non-2xx. */
export async function fetchMe(token: string): Promise<MeOut> {
  const baseUrl =
    typeof window !== "undefined"
      ? "/api/v1"
      : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000") + "/v1";

  const res = await fetch(`${baseUrl}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    // Don't cache — always get fresh role/org data
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GET /auth/me failed: ${res.status} ${body}`);
  }

  return res.json() as Promise<MeOut>;
}
