import type { components } from "./generated";

export type MeOut = components["schemas"]["MeOut"];
export type OrganizationOut = components["schemas"]["OrganizationOut"];


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
