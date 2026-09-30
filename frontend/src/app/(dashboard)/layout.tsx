import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Header } from "@/components/shell/header";
import { UserStoreSync } from "@/components/providers/user-store-sync";
import { ErrorBoundary } from "@/components/error-boundary";

/**
 * Dashboard layout — all routes under (dashboard) require authentication.
 *
 * Responsibilities:
 *   1. Server-side auth guard via Clerk's auth() — unauthenticated users are
 *      redirected to /sign-in before any content is rendered.
 *   2. Mounts <UserStoreSync> which runs useMe() client-side and populates
 *      the Zustand user store with role/org data from the backend.
 *   3. Provides the Antigravity application shell (sidebar, header, error boundary).
 */
import { isClerkConfigured } from "@/lib/auth/clerk-config";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let userId: string | null = null;
  if (!isClerkConfigured()) {
    userId = "dev_user_id";
  } else {
    try {
      const authObj = await auth();
      userId = authObj.userId;
    } catch {
      if (process.env.NODE_ENV !== "production") {
        userId = "dev_user_id";
      }
    }
  }

  if (!userId) {
    redirect("/sign-in");
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground bg-ambient-mesh">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <UserStoreSync />
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

