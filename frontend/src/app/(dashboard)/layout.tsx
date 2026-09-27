import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

/**
 * Dashboard layout — all routes under (dashboard) require authentication.
 * Clerk's auth() returns null if unauthenticated; we redirect to sign-in.
 */
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* Nav shell — fleshed out in Phase 5 */}
      <header className="border-b px-6 py-3 flex items-center justify-between">
        <span className="font-semibold text-sm tracking-tight">Provenance</span>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
