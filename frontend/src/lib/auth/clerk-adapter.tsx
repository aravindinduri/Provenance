"use client";

import React, { createContext, useContext, useMemo } from "react";
import { ClerkProvider as BaseClerkProvider, useAuth as useClerkAuth, useClerk as useClerkClient } from "@clerk/nextjs";

import { isClerkConfigured } from "./clerk-config";
export { isClerkConfigured };

interface DevAuthContextType {
  isSignedIn: boolean;
  userId: string | null;
  getToken: () => Promise<string | null>;
  signOut: (options?: { redirectUrl?: string }) => Promise<void>;
}

const DevAuthContext = createContext<DevAuthContextType>({
  isSignedIn: true,
  userId: "usr_dev_risk_lead",
  getToken: async () => "dev_test_token_provenance",
  signOut: async () => {},
});

function DevAuthProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(
    () => ({
      isSignedIn: true,
      userId: "usr_dev_risk_lead",
      getToken: async () => "dev_test_token_provenance",
      signOut: async (opts?: { redirectUrl?: string }) => {
        window.location.href = opts?.redirectUrl || "/sign-in";
      },
    }),
    []
  );

  return (
    <DevAuthContext.Provider value={value}>
      {children}
    </DevAuthContext.Provider>
  );
}

export function ClerkProviderWrapper({ children }: { children: React.ReactNode }) {
  const hasClerk = isClerkConfigured();

  if (!hasClerk) {
    return <DevAuthProvider>{children}</DevAuthProvider>;
  }

  return (
    <BaseClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
      signInUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL || "/sign-in"}
      signUpUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_UP_URL || "/sign-up"}
    >
      {children}
    </BaseClerkProvider>
  );
}

export function useAppAuth(): {
  isSignedIn: boolean;
  userId: string | null;
  getToken: () => Promise<string | null>;
} {
  const hasClerk = isClerkConfigured();
  const devAuth = useContext(DevAuthContext);

  if (!hasClerk) {
    return {
      isSignedIn: devAuth.isSignedIn,
      userId: devAuth.userId,
      getToken: devAuth.getToken,
    };
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const clerkAuth = useClerkAuth();
  return {
    isSignedIn: !!clerkAuth.isSignedIn,
    userId: clerkAuth.userId ?? null,
    getToken: clerkAuth.getToken,
  };
}

export function useAppClerk(): {
  signOut: (options?: { redirectUrl?: string }) => Promise<void> | void;
} {
  const hasClerk = isClerkConfigured();
  const devAuth = useContext(DevAuthContext);

  if (!hasClerk) {
    return {
      signOut: devAuth.signOut,
    };
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const clerk = useClerkClient();
  return {
    signOut: clerk.signOut,
  };
}
