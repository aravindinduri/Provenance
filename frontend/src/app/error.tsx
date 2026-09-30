"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function RootError({
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
    console.error("Route error boundary captured:", error);
  }, [error]);

  return (
    <div className="flex min-h-[500px] w-full flex-col items-center justify-center p-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive mb-4 shadow-glow-rose">
        <AlertCircle className="h-8 w-8" />
      </div>
      <h2 className="text-2xl font-bold tracking-tight">Application Error</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        We encountered an issue loading this section. Our telemetry has logged
        this event for automated analysis.
      </p>
      {error.digest && (
        <span className="mt-2 font-mono text-xs text-muted-foreground">
          Incident Digest: {error.digest}
        </span>
      )}
      <div className="mt-6 flex gap-3">
        <Button variant="outline" onClick={() => window.location.href = "/dashboard"}>
          Return to Dashboard
        </Button>
        <Button variant="default" onClick={() => reset()}>
          <RotateCcw className="mr-1.5 h-4 w-4" />
          Try Again
        </Button>
      </div>
    </div>
  );
}
