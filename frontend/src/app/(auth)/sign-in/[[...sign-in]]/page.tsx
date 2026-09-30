"use client";

import React from "react";
import Link from "next/link";
import { SignIn } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/auth/clerk-config";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Radio, ArrowRight, ShieldCheck } from "lucide-react";

export default function SignInPage() {
  const hasClerk = isClerkConfigured();

  if (hasClerk) {
    return <SignIn />;
  }

  return (
    <Card className="w-full max-w-md border-border/80 bg-card/90 shadow-2xl backdrop-blur-xl">
      <CardHeader className="text-center space-y-2 pb-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-glow-primary mb-2">
          <Radio className="h-6 w-6 animate-pulse" />
        </div>
        <CardTitle className="text-xl font-bold tracking-tight">
          Provenance Intelligence
        </CardTitle>
        <CardDescription className="text-xs">
          Local Development Mode &bull; Supply Chain Risk Platform
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3.5 space-y-1.5 text-xs text-muted-foreground">
          <div className="flex items-center gap-2 font-medium text-foreground">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Developer Session Active</span>
          </div>
          <p>
            You are running in local development mode. No external Clerk account
            setup is required to explore all features.
          </p>
        </div>

        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex justify-between py-1 border-b border-border/40">
            <span>Mock User:</span>
            <span className="font-mono text-foreground font-medium">risk.lead@provenance.internal</span>
          </div>
          <div className="flex justify-between py-1 border-b border-border/40">
            <span>Role:</span>
            <span className="font-mono text-foreground font-medium">org_admin</span>
          </div>
          <div className="flex justify-between py-1">
            <span>Tenant:</span>
            <span className="font-mono text-foreground font-medium">Acme Industrial Group</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-2">
        <Button asChild variant="glow" className="w-full">
          <Link href="/dashboard">
            <span>Enter Dashboard</span>
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
