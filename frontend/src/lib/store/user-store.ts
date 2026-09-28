/**
 * src/lib/store/user-store.ts — Zustand store for the resolved backend user.
 *
 * Clerk tells us who the user is at the identity level.
 * This store holds what the *backend* knows: their org UUID, role, persona,
 * and category assignments — things that drive permissions in the UI.
 *
 * Populated by <UserStoreSync /> once useMe() resolves.
 * Other components read from here instead of calling useMe() everywhere.
 *
 * Usage:
 *   const role = useUserStore(s => s.role);
 *   const hasPermission = useUserStore(s => s.hasPermission);
 *
 *   if (hasPermission("suppliers:write")) { ... }
 */

import { create } from "zustand";
import type { MeOut } from "@/lib/api/me";

// Permission map — mirrors backend app/auth/base.py PERMISSIONS dict.
// Keep in sync with the backend. A future codegen step can derive this.
const PERMISSIONS: Record<string, Set<string>> = {
  platform_admin: new Set([
    "platform:read", "platform:write",
    "org:read", "org:write",
    "members:read", "members:write",
    "suppliers:read", "suppliers:write",
    "alerts:read", "alerts:write",
    "documents:read", "documents:write",
    "graph:read", "graph:write",
    "ai:use", "admin:read", "admin:write",
  ]),
  org_admin: new Set([
    "org:read", "org:write",
    "members:read", "members:write",
    "suppliers:read", "suppliers:write",
    "alerts:read", "alerts:write",
    "documents:read", "documents:write",
    "graph:read", "graph:write",
    "ai:use",
  ]),
  analyst: new Set([
    "org:read", "members:read",
    "suppliers:read", "suppliers:write",
    "alerts:read", "alerts:write",
    "documents:read", "documents:write",
    "graph:read", "graph:write",
    "ai:use",
  ]),
  org_user: new Set([
    "org:read", "members:read",
    "suppliers:read",
    "alerts:read", "alerts:write",
    "documents:read",
    "graph:read",
  ]),
  read_only: new Set([
    "org:read", "members:read",
    "suppliers:read",
    "alerts:read",
    "documents:read",
    "graph:read",
  ]),
};

interface UserState {
  // Raw backend data
  userId: string | null;
  email: string | null;
  orgId: string | null;
  clerkOrgId: string | null;
  role: string | null;
  persona: string | null;
  assignedCategories: string[];
  orgName: string | null;
  orgSlug: string | null;
  subscriptionTier: string | null;

  // Derived helpers
  isLoaded: boolean;
  isPlatformAdmin: boolean;
  hasPermission: (permission: string) => boolean;

  // Actions
  setFromMe: (me: MeOut) => void;
  clear: () => void;
}

const _hasPermission = (role: string | null, permission: string): boolean => {
  if (!role) return false;
  return PERMISSIONS[role]?.has(permission) ?? false;
};

export const useUserStore = create<UserState>((set, get) => ({
  userId: null,
  email: null,
  orgId: null,
  clerkOrgId: null,
  role: null,
  persona: null,
  assignedCategories: [],
  orgName: null,
  orgSlug: null,
  subscriptionTier: null,

  isLoaded: false,
  isPlatformAdmin: false,

  hasPermission: (permission: string) => _hasPermission(get().role, permission),

  setFromMe: (me: MeOut) =>
    set({
      userId: me.user_id,
      email: me.email,
      orgId: me.org_id,
      clerkOrgId: me.clerk_org_id,
      role: me.role,
      persona: me.persona,
      assignedCategories: me.assigned_categories,
      orgName: me.organization?.name ?? null,
      orgSlug: me.organization?.slug ?? null,
      subscriptionTier: me.organization?.subscription_tier ?? null,
      isLoaded: true,
      isPlatformAdmin: me.role === "platform_admin",
    }),

  clear: () =>
    set({
      userId: null,
      email: null,
      orgId: null,
      clerkOrgId: null,
      role: null,
      persona: null,
      assignedCategories: [],
      orgName: null,
      orgSlug: null,
      subscriptionTier: null,
      isLoaded: false,
      isPlatformAdmin: false,
    }),
}));
