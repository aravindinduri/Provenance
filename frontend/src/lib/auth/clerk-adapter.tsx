"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { ClerkProvider as BaseClerkProvider, useAuth as useClerkAuth, useClerk as useClerkClient } from "@clerk/nextjs";

import { isClerkConfigured } from "./clerk-config";
export { isClerkConfigured };

interface AuthContextType {
  isSignedIn: boolean;
  userId: string | null;
  userEmail: string | null;
  getToken: () => Promise<string | null>;
  setAuthSession: (token: string, user: { id: string; email: string }) => void;
  signOut: (options?: { redirectUrl?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  isSignedIn: false,
  userId: null,
  userEmail: null,
  getToken: async () => null,
  setAuthSession: () => {},
  signOut: async () => {},
});

const TOKEN_KEY = "provenance_token";
const USER_ID_KEY = "provenance_user_id";
const USER_EMAIL_KEY = "provenance_user_email";

function NativeAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize from localStorage on browser mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      const storedUserId = localStorage.getItem(USER_ID_KEY);
      const storedEmail = localStorage.getItem(USER_EMAIL_KEY);
      if (storedToken) {
        setToken(storedToken);
        setUserId(storedUserId);
        setUserEmail(storedEmail);
      }
      setIsInitialized(true);
    }
  }, []);

  const setAuthSession = useCallback((newToken: string, user: { id: string; email: string }) => {
    setToken(newToken);
    setUserId(user.id);
    setUserEmail(user.email);
    if (typeof window !== "undefined") {
      localStorage.setItem(TOKEN_KEY, newToken);
      localStorage.setItem(USER_ID_KEY, user.id);
      localStorage.setItem(USER_EMAIL_KEY, user.email);
      document.cookie = `${TOKEN_KEY}=${newToken}; path=/; max-age=86400; SameSite=Lax`;
    }
  }, []);

  const signOut = useCallback(async (opts?: { redirectUrl?: string }) => {
    setToken(null);
    setUserId(null);
    setUserEmail(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_ID_KEY);
      localStorage.removeItem(USER_EMAIL_KEY);
      document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
      window.location.href = opts?.redirectUrl || "/sign-in";
    }
  }, []);

  const getToken = useCallback(async () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(TOKEN_KEY) || token;
    }
    return token;
  }, [token]);

  const value = useMemo(
    () => ({
      isSignedIn: !!token,
      userId,
      userEmail,
      getToken,
      setAuthSession,
      signOut,
    }),
    [token, userId, userEmail, getToken, setAuthSession, signOut]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function ClerkProviderWrapper({ children }: { children: React.ReactNode }) {
  const hasClerk = isClerkConfigured();

  if (!hasClerk) {
    return <NativeAuthProvider>{children}</NativeAuthProvider>;
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
  userEmail: string | null;
  getToken: () => Promise<string | null>;
  setAuthSession: (token: string, user: { id: string; email: string }) => void;
  signOut: (options?: { redirectUrl?: string }) => Promise<void>;
} {
  const hasClerk = isClerkConfigured();
  const nativeAuth = useContext(AuthContext);

  if (!hasClerk) {
    return {
      isSignedIn: nativeAuth.isSignedIn,
      userId: nativeAuth.userId,
      userEmail: nativeAuth.userEmail,
      getToken: nativeAuth.getToken,
      setAuthSession: nativeAuth.setAuthSession,
      signOut: nativeAuth.signOut,
    };
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const clerkAuth = useClerkAuth();
  return {
    isSignedIn: !!clerkAuth.isSignedIn,
    userId: clerkAuth.userId ?? null,
    userEmail: null,
    getToken: clerkAuth.getToken,
    setAuthSession: () => {},
    signOut: async () => {},
  };
}

export function useAppClerk(): {
  signOut: (options?: { redirectUrl?: string }) => Promise<void> | void;
} {
  const hasClerk = isClerkConfigured();
  const nativeAuth = useContext(AuthContext);

  if (!hasClerk) {
    return {
      signOut: nativeAuth.signOut,
    };
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const clerk = useClerkClient();
  return {
    signOut: clerk.signOut,
  };
}
