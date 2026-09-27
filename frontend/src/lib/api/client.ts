/**
 * Typed API client generated from FastAPI's OpenAPI schema.
 *
 * DO NOT hand-edit this file's fetch calls — run `npm run generate:api`
 * to regenerate `generated.ts` from the live schema, then import from here.
 *
 * Phase 1: base client setup only. Endpoints are added as modules ship.
 */

import createClient from "openapi-fetch";
// `generated.ts` is produced by: npm run generate:api
// It does not exist yet in Phase 1 — the CI drift check will catch any mismatch.
// import type { paths } from "./generated";

const apiBaseUrl =
  typeof window !== "undefined"
    ? "/api/v1"                                    // browser: use Next.js rewrite proxy
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000") + "/v1";  // SSR

// ponytail: typed as `any` until generated.ts exists; tightened in Phase 5.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const apiClient = createClient<any>({ baseUrl: apiBaseUrl });
