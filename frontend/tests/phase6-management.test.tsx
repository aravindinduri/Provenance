import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OnboardingPage from "@/app/(dashboard)/onboarding/page";
import SuppliersPage from "@/app/(dashboard)/suppliers/page";
import SettingsPage from "@/app/(dashboard)/settings/page";
import { useUserStore } from "@/lib/store/user-store";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/suppliers",
}));

describe("Phase 6 — Organization & Supplier Management", () => {
  beforeEach(() => {
    useUserStore.getState().setFromMe({
      user_id: "test_user_admin",
      email: "admin@test.com",
      org_id: "00000000-0000-0000-0000-000000000001",
      clerk_org_id: "clerk_org_1",
      role: "org_admin",
      persona: "risk_manager",
      assigned_categories: ["Semiconductors", "Direct Materials"],
      organization: {
        id: "00000000-0000-0000-0000-000000000001",
        clerk_org_id: "clerk_org_1",
        name: "Acme Industrial Corp",
        slug: "acme-industrial",
        company_id: null,
        industry: "Manufacturing",
        country: "US",
        subscription_tier: "enterprise",
        monthly_token_budget: 5000000,
        onboarding_completed_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });

    // Mock global fetch
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/v1/suppliers")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            data: [
              {
                id: "sup-1",
                org_id: "00000000-0000-0000-0000-000000000001",
                company_id: "comp-1",
                relationship_type: "supplies_to",
                tier: 1,
                criticality: 5,
                annual_spend_usd: 5000000,
                category: "Semiconductors",
                single_source: true,
                lead_time_days: 60,
                confidence: 1.0,
                source: "user_declared",
                company: {
                  id: "comp-1",
                  legal_name: "Apex Silicon Foundries",
                  name_norm: "apex silicon foundries",
                  country: "US",
                  primary_domain: "apexsilicon.com",
                  is_verified: true,
                },
              },
            ],
            pagination: { next_cursor: null, has_more: false },
          }),
        });
      }

      if (url.includes("/api/v1/organizations") && url.includes("/members")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            data: [
              {
                id: "mem-1",
                user_id: "test_user_admin",
                role: "org_admin",
                persona: "risk_manager",
                assigned_categories: ["Semiconductors"],
                joined_at: new Date().toISOString(),
                created_at: new Date().toISOString(),
              },
            ],
            total: 1,
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({ data: [] }),
      });
    });
  });

  describe("Onboarding Wizard (Journey J1)", () => {
    it("renders Step 1 for claiming canonical organization entity", () => {
      render(<OnboardingPage />);
      expect(screen.getByText("Supply Base Onboarding")).toBeInTheDocument();
      expect(screen.getByText("Claim Your Canonical Company")).toBeInTheDocument();
      expect(screen.getByText("1. Claim Entity")).toBeInTheDocument();
      expect(screen.getByText("2. Seed Suppliers")).toBeInTheDocument();
      expect(screen.getByText("3. Spend Matrix")).toBeInTheDocument();
      expect(screen.getByText("4. Backfill Scan")).toBeInTheDocument();
      expect(screen.getByText("Search Legal Entity Name or LEI Identifier")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/acme manufacturing/i)).toBeInTheDocument();
    });
  });

  describe("Supplier Directory (/suppliers)", () => {
    it("renders directory with KPI summary cards and action buttons", async () => {
      render(<SuppliersPage />);
      expect(screen.getByText("Supplier Directory & Registry")).toBeInTheDocument();
      expect(screen.getByText("Direct Suppliers")).toBeInTheDocument();
      expect(screen.getByText("High Risk Criticality")).toBeInTheDocument();
      expect(screen.getByText("Tracked Annual Spend")).toBeInTheDocument();
      expect(screen.getByText("Single Source Nodes")).toBeInTheDocument();

      // Action buttons
      expect(screen.getByRole("button", { name: /bulk csv import/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /add supplier/i })).toBeInTheDocument();

      // Verify loaded supplier row appears
      await waitFor(() => {
        expect(screen.getByText("Apex Silicon Foundries")).toBeInTheDocument();
      });
      expect(screen.getByText("$5,000,000")).toBeInTheDocument();
      expect(screen.getByText("Single Source")).toBeInTheDocument();
    });

    it("opens Add Supplier dialog when clicking button", () => {
      render(<SuppliersPage />);
      const addBtn = screen.getByRole("button", { name: /add supplier/i });
      fireEvent.click(addBtn);
      expect(screen.getByText("Add Supplier to Organization")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\. Nippon Electric Co/i)).toBeInTheDocument();
    });

    it("opens Bulk CSV Import dialog when clicking button", () => {
      render(<SuppliersPage />);
      const bulkBtn = screen.getByRole("button", { name: /bulk csv import/i });
      fireEvent.click(bulkBtn);
      expect(screen.getByText("Bulk Supplier CSV Upload")).toBeInTheDocument();
      expect(screen.getByText("Need standard CSV template?")).toBeInTheDocument();
    });
  });

  describe("Organization Settings (/settings)", () => {
    it("renders profile, members, and preferences tabs", async () => {
      render(<SettingsPage />);
      expect(screen.getByText("Organization Settings")).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /organization profile/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /team & members/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /risk preferences/i })).toBeInTheDocument();
      expect(screen.getByText("Tenant Identity")).toBeInTheDocument();
    });
  });
});
