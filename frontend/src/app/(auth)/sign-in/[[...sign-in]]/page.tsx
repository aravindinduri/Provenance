import { SignIn } from "@clerk/nextjs";

export const metadata = {
  title: "Sign In — Provenance",
};

/**
 * Clerk-hosted sign-in UI.
 * NEXT_PUBLIC_CLERK_SIGN_IN_URL must be set to /sign-in in .env.
 * After sign-in Clerk redirects to NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL (/dashboard).
 */
export default function SignInPage() {
  return <SignIn />;
}
