"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    try {
      Sentry.captureException(error);
    } catch {
      // Local dev fallback
    }
    console.error("Global root error caught:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-4 rounded-2xl border border-red-500/20 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10 text-red-500">
            <AlertOctagon className="h-7 w-7" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">System Critical Failure</h1>
          <p className="text-xs text-slate-400">
            A fatal exception prevented the application shell from mounting.
            Diagnostics have been collected.
          </p>
          {error.digest && (
            <p className="font-mono text-[10px] text-slate-500">
              Digest: {error.digest}
            </p>
          )}
          <div className="pt-2">
            <Button
              variant="default"
              size="sm"
              onClick={() => reset()}
              className="bg-red-600 hover:bg-red-500 text-white"
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Reload Application
            </Button>
          </div>
        </div>
      </body>
    </html>
  );
}
