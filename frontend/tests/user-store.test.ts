import { describe, it, expect, beforeEach } from "vitest";
import { useUserStore } from "@/lib/store/user-store";

describe("User Store & Permissions", () => {
  beforeEach(() => {
    useUserStore.getState().clear();
  });

  it("initializes with default empty state", () => {
    const state = useUserStore.getState();
    expect(state.userId).toBeNull();
    expect(state.isLoaded).toBe(false);
    expect(state.isPlatformAdmin).toBe(false);
  });

  it("populates state from MeOut payload", () => {
    useUserStore.getState().setFromMe({
      user_id: "usr_platform_admin",
      email: "admin@provenance.internal",
      org_id: "org_root_123",
      clerk_org_id: "org_clerk_456",
      role: "platform_admin",
      persona: "risk_manager",
      assigned_categories: ["electronics", "optics"],
      organization: {
        id: "org_root_123",
        clerk_org_id: "org_clerk_456",
        name: "Enterprise Core Tenant",
        slug: "enterprise-core",
        company_id: null,
        industry: "Advanced Manufacturing",
        country: "US",
        subscription_tier: "enterprise",
        monthly_token_budget: 1000000,
        onboarding_completed_at: "2026-09-01T00:00:00Z",
        created_at: "2026-09-01T00:00:00Z",
        updated_at: "2026-09-01T00:00:00Z",
      },
    });

    const state = useUserStore.getState();
    expect(state.userId).toBe("usr_platform_admin");
    expect(state.isPlatformAdmin).toBe(true);
    expect(state.orgName).toBe("Enterprise Core Tenant");
    expect(state.isLoaded).toBe(true);
  });

  it("evaluates role permissions correctly", () => {
    useUserStore.getState().setFromMe({
      user_id: "usr_analyst",
      email: "analyst@provenance.internal",
      org_id: "org_1",
      clerk_org_id: null,
      role: "analyst",
      persona: "category_manager",
      assigned_categories: [],
      organization: null,
    });

    const state = useUserStore.getState();
    expect(state.hasPermission("suppliers:read")).toBe(true);
    expect(state.hasPermission("suppliers:write")).toBe(true);
    expect(state.hasPermission("platform:write")).toBe(false); // analyst cannot mutate platform
  });

  it("clear resets store state", () => {
    useUserStore.getState().setFromMe({
      user_id: "usr_test",
      email: "test@test.com",
      org_id: "org_test",
      clerk_org_id: null,
      role: "org_user",
      persona: null,
      assigned_categories: [],
      organization: null,
    });
    expect(useUserStore.getState().userId).toBe("usr_test");

    useUserStore.getState().clear();
    expect(useUserStore.getState().userId).toBeNull();
    expect(useUserStore.getState().isLoaded).toBe(false);
  });
});
