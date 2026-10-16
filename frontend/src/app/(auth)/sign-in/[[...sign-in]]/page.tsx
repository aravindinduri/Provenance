"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignIn as ClerkSignIn } from "@clerk/nextjs";
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
import { Radio, ArrowRight, Loader2, AlertCircle, Lock, Mail, ShieldCheck } from "lucide-react";

export default function SignInPage(): React.JSX.Element {
  const router = useRouter();
  const hasClerk = isClerkConfigured();
  const { setAuthSession } = useAppAuth();

  const [authMode, setAuthMode] = useState<"platform" | "clerk">("platform");
  const [email, setEmail] = useState("aravind@feuji.com");
  const [password, setPassword] = useState("Password123!");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (hasClerk && authMode === "clerk") {
    return (
      <div className="flex flex-col items-center gap-3 w-full max-w-md">
        <ClerkSignIn />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAuthMode("platform")}
          className="text-xs text-neutral-500 hover:text-neutral-900"
        >
          ← Use Platform Credentials
        </Button>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMsg("Please enter both email and password.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid email or password.");
      }

      const authData = await res.json();
      setAuthSession(authData.access_token, {
        id: authData.user.id,
        email: authData.user.email,
      });

      router.push("/dashboard");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to sign in. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (fillEmail: string, fillPass: string) => {
    setEmail(fillEmail);
    setPassword(fillPass);
    setErrorMsg(null);
  };

  return (
    <Card className="w-full max-w-md border-neutral-200/80 bg-white/95 shadow-2xl backdrop-blur-xl">
      <CardHeader className="text-center space-y-2 pb-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-[#FA651E] text-white shadow-md mb-2">
          <Radio className="h-6 w-6 animate-pulse" />
        </div>
        <CardTitle className="text-xl font-bold tracking-tight text-neutral-900">
          Sign In to Provenance
        </CardTitle>
        <CardDescription className="text-xs text-neutral-500">
          Multi-Tier Supply Chain Risk &amp; Procurement Platform
        </CardDescription>

        {/* Quick Demo Credentials */}
        <div className="pt-2 flex flex-col gap-1.5 bg-neutral-50 p-2.5 rounded-lg border border-neutral-200/60 text-left">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-neutral-700">
            <ShieldCheck className="h-3.5 w-3.5 text-[#FA651E]" />
            Pre-configured Ingested Accounts:
          </div>
          <div className="flex flex-wrap gap-1.5 mt-0.5">
            <button
              type="button"
              onClick={() => handleQuickFill("aravind@feuji.com", "Password123!")}
              className={`px-2 py-1 rounded text-[11px] font-medium border transition-colors ${
                email === "aravind@feuji.com"
                  ? "bg-[#FA651E]/10 border-[#FA651E] text-[#FA651E] font-semibold"
                  : "bg-white border-neutral-200 text-neutral-600 hover:border-neutral-300"
              }`}
            >
              aravind@feuji.com (Admin)
            </button>
            <button
              type="button"
              onClick={() => handleQuickFill("procurement@feuji.com", "Password123!")}
              className={`px-2 py-1 rounded text-[11px] font-medium border transition-colors ${
                email === "procurement@feuji.com"
                  ? "bg-[#FA651E]/10 border-[#FA651E] text-[#FA651E] font-semibold"
                  : "bg-white border-neutral-200 text-neutral-600 hover:border-neutral-300"
              }`}
            >
              procurement@feuji.com (Approver)
            </button>
          </div>
        </div>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4 pt-1">
          {errorMsg && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-neutral-700 flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-neutral-400" />
              Work Email
            </label>
            <Input
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-neutral-700 flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-neutral-400" />
              Password
            </label>
            <Input
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="h-9 text-xs"
              disabled={isLoading}
            />
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-3 pt-2">
          <Button
            type="submit"
            className="w-full text-xs bg-[#FA651E] hover:bg-[#E05310] text-white h-9 shadow-sm font-medium"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Authenticating...
              </>
            ) : (
              <>
                <span>Sign In to Feuji Inc.</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>

          <div className="flex items-center justify-between w-full pt-1 text-xs text-neutral-500">
            {hasClerk ? (
              <button
                type="button"
                onClick={() => setAuthMode("clerk")}
                className="text-neutral-500 hover:text-neutral-800 underline text-[11px]"
              >
                Use Clerk SSO
              </button>
            ) : <span />}

            <p className="text-right text-[11px] text-neutral-500">
              Don&apos;t have an account?{" "}
              <Link href="/sign-up" className="text-[#FA651E] hover:underline font-medium">
                Register
              </Link>
            </p>
          </div>
        </CardFooter>
      </form>
    </Card>
  );
}
