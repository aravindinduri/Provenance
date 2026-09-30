"use client";

import React from "react";
import Link from "next/link";
import { SignUp } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/auth/clerk-config";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Radio, ArrowRight } from "lucide-react";

export default function SignUpPage() {
  const hasClerk = isClerkConfigured();

  if (hasClerk) {
    return <SignUp />;
  }

  return (
    <Card className="w-full max-w-md border-border/80 bg-card/90 shadow-2xl backdrop-blur-xl">
      <CardHeader className="text-center space-y-2 pb-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-glow-primary mb-2">
          <Radio className="h-6 w-6 animate-pulse" />
        </div>
        <CardTitle className="text-xl font-bold tracking-tight">
          Create Account
        </CardTitle>
        <CardDescription className="text-xs">
          Local Development Mode &bull; Auto-provisioned Organization
        </CardDescription>
      </CardHeader>

      <CardContent className="text-xs text-muted-foreground">
        <p>
          In development mode, you can immediately access the dashboard without creating an external account.
        </p>
      </CardContent>

      <CardFooter className="pt-2">
        <Button asChild variant="glow" className="w-full">
          <Link href="/dashboard">
            <span>Continue to Dashboard</span>
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
