"use client";

import React, { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
    // Send to Sentry if initialized
    try {
      Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
    } catch {
      // Sentry might not be configured in local dev
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] w-full items-center justify-center p-6">
          <Card className="max-w-md border-red-500/30 bg-card/90 shadow-glow-rose">
            <CardHeader className="flex flex-row items-center gap-3 space-y-0 pb-2">
              <div className="p-2 rounded-lg bg-red-500/10 text-red-500">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <CardTitle className="text-lg">Something went wrong</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground pt-2">
              <p>
                An unexpected error occurred while rendering this component. Our
                system diagnostics have recorded the incident.
              </p>
              {this.state.error?.message && (
                <div className="p-2 rounded bg-muted font-mono text-xs text-foreground/80 break-words">
                  {this.state.error.message}
                </div>
              )}
            </CardContent>
            <CardFooter className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
              <Button variant="default" size="sm" onClick={this.handleReset}>
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                Try Again
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
