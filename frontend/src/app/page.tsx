import { redirect } from "next/navigation";

/**
 * Root route: redirect to the dashboard.
 * Auth is enforced by the (dashboard) layout via Clerk middleware.
 */
export default function RootPage() {
  redirect("/dashboard");
}
