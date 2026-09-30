/**
 * Shared Clerk configuration check.
 * Safe to import from both Server Components and Client Components.
 */
export const isClerkConfigured = (): boolean => {
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key) return false;
  if (key.includes("placeholder") || key.includes("cHJvdmVuYW5jZS1kZXY")) return false;
  return key.startsWith("pk_");
};
