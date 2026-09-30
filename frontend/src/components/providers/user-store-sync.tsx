"use client";

/**
 * src/components/providers/user-store-sync.tsx
 *
 * Runs useMe() once after sign-in and writes the result into the Zustand
 * user store, so all client components can read role/org data synchronously
 * without each calling useMe() individually.
 *
 * Also clears the store on sign-out.
 *
 * Renders nothing — purely a side-effect component.
 * Mount it inside the dashboard layout, inside QueryProvider.
 */

import { useEffect } from "react";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useMe } from "@/lib/hooks/use-me";
import { useUserStore } from "@/lib/store/user-store";

export function UserStoreSync() {
  const { isSignedIn } = useAppAuth();
  const { data: me } = useMe();
  const { setFromMe, clear } = useUserStore();

  useEffect(() => {
    if (me) {
      setFromMe(me);
    }
  }, [me, setFromMe]);

  useEffect(() => {
    if (!isSignedIn) {
      clear();
    }
  }, [isSignedIn, clear]);

  return null;
}
