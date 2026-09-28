import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { UserStoreSync } from "@/components/providers/user-store-sync";

/**
 * Dashboard layout — all routes under (dashboard) require authentication.
 *
 * Responsibilities:
 *   1. Server-side auth guard via Clerk's auth() — unauthenticated users are
 *      redirected to /sign-in before any content is rendered.
 *   2. Mounts <UserStoreSync> which runs useMe() client-side and populates
 *      the Zustand user store with role/org data from the backend.
 *   3. Provides the application shell (nav header, main area).
 *      The nav is a stub here — it is fleshed out in Phase 5.
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
      {/* Nav shell — expanded in Phase 5 with supplier/alert links */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur px-6 py-3 flex items-center justify-between">
        <span className="font-semibold text-sm tracking-tight">Provenance</span>
        {/* UserMenu placeholder — replaced with full component in Phase 5 */}
        <span className="text-xs text-muted-foreground">v0.1</span>
      </header>

      <main className="flex-1 p-6">
        {/*
          UserStoreSync is a Client Component that runs useMe() and writes
          the result to Zustand. All client components in the tree can then
          read role/org synchronously via useUserStore().
        */}
        <UserStoreSync />
        {children}
      </main>
    </div>
  );
}
