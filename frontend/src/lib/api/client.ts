/**
 * Typed API client generated from FastAPI's OpenAPI schema.
 *
 * DO NOT hand-edit this file's fetch calls — run `npm run generate:api`
 * to regenerate `generated.ts` from the live schema, then import from here.
 *
 * Phase 1: base client setup only. Endpoints are added as modules ship.
 */

import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./generated";

export type { paths } from "./generated";

const apiBaseUrl =
  typeof window !== "undefined"
    ? "/api/v1" // browser: use Next.js rewrite proxy
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000") + "/v1"; // SSR

export const apiClient = createClient<paths>({ baseUrl: apiBaseUrl });

export function createAuthenticatedClient(token?: string | null) {
  const client = createClient<paths>({ baseUrl: apiBaseUrl });
  if (token) {
    const authMiddleware: Middleware = {
      async onRequest({ request }) {
        request.headers.set("Authorization", `Bearer ${token}`);
        return request;
      },
    };
    client.use(authMiddleware);
  }
  return client;
}

