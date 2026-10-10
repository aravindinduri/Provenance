"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignUp as ClerkSignUp } from "@clerk/nextjs";
import { isClerkConfigured } from "@/lib/auth/clerk-config";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Radio, ArrowRight, Loader2, AlertCircle, Lock, Mail, User, Building2 } from "lucide-react";

export default function SignUpPage(): React.JSX.Element {
  const router = useRouter();
  const hasClerk = isClerkConfigured();
  const { setAuthSession } = useAppAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("Feuji Inc.");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (hasClerk) {
    return <ClerkSignUp />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password) {
      setErrorMsg("Please fill in all required fields.");
      return;
    }

    if (password.length < 6) {
      setErrorMsg("Password must be at least 6 characters.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          org_name: orgName.trim() || "Feuji Inc.",
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed. Please check details.");
      }

      const authData = await res.json();
      setAuthSession(authData.access_token, {
        id: authData.user.id,
        email: authData.user.email,
      });

      router.push("/dashboard");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to register account.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md border-border/80 bg-card/90 shadow-2xl backdrop-blur-xl">
      <CardHeader className="text-center space-y-2 pb-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-glow-primary mb-2">
          <Radio className="h-6 w-6 animate-pulse" />
        </div>
        <CardTitle className="text-xl font-bold tracking-tight">
          Create Provenance Account
        </CardTitle>
        <CardDescription className="text-xs">
          Register to monitor multi-tier supply chain risk intelligence
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-3.5 pt-1">
          {errorMsg && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-muted-foreground" />
              Full Name
            </label>
            <Input
              type="text"
              placeholder="e.g. Aravind Induri"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-muted-foreground" />
              Work Email
            </label>
            <Input
              type="email"
              placeholder="name@feuji.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              Password
            </label>
            <Input
              type="password"
              placeholder="Minimum 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
              Organization / Company
            </label>
            <Input
              type="text"
              placeholder="Feuji Inc."
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              required
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-3 pt-3">
          <Button type="submit" variant="glow" className="w-full text-xs" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Registering Account...
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Already have an account?{" "}
            <Link href="/sign-in" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
