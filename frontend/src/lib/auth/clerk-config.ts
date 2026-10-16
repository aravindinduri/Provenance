/**
 * Shared Clerk configuration check.
 * Safe to import from both Server Components and Client Components.
 */
export const isClerkConfigured = (): boolean => {
  // If explicitly requested to use Clerk cloud authentication
  if (process.env.NEXT_PUBLIC_AUTH_PROVIDER === "clerk") {
    const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
    if (!key) return false;
    if (key.includes("placeholder") || key.includes("cHJvdmVuYW5jZS1kZXY") || key.includes("cXVhbGl0eS1tb25hcmNo")) return false;
    return key.startsWith("pk_");
  }

  // In local development, default to native database authentication
  // so accounts stored in PostgreSQL (aravind@feuji.com) can log in seamlessly
  return false;
};
