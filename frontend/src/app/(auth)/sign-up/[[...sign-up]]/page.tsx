import { SignUp } from "@clerk/nextjs";

export const metadata = {
  title: "Sign Up — Provenance",
};

/**
 * Clerk-hosted sign-up UI.
 * NEXT_PUBLIC_CLERK_SIGN_UP_URL must be set to /sign-up in .env.
 * After sign-up Clerk redirects to NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL (/dashboard).
 */
export default function SignUpPage() {
  return <SignUp />;
}
