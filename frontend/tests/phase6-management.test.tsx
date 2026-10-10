import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OnboardingPage from "@/app/(dashboard)/onboarding/page";
import SuppliersPage from "@/app/(dashboard)/suppliers/page";
import SettingsPage from "@/app/(dashboard)/settings/page";
import AlertsPage from "@/app/(dashboard)/alerts/page";
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

const TEST_ORG_ID = process.env.TEST_ORG_ID || "c3d0ecce-c25c-48f9-80e2-110ec2f10bd1";
const TEST_ORG_NAME = process.env.TEST_ORG_NAME || "Feuji Inc.";
const TEST_ORG_SLUG = process.env.TEST_ORG_SLUG || "feuji-inc";
const TEST_CLERK_ORG_ID = process.env.TEST_CLERK_ORG_ID || "org_dev_feuji_001";
const TEST_USER_ID = process.env.TEST_USER_ID || "0f803a08-3091-4e52-bda5-8a54bd57ea2e";
const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL || "aravind@feuji.com";

describe("Phase 6 — Organization & Supplier Management", () => {
  beforeEach(() => {
    useUserStore.getState().setFromMe({
      user_id: TEST_USER_ID,
      email: TEST_USER_EMAIL,
      org_id: TEST_ORG_ID,
      clerk_org_id: TEST_CLERK_ORG_ID,
      role: "org_admin",
      persona: "risk_manager",
      assigned_categories: ["Semiconductors", "Direct Materials"],
      organization: {
        id: TEST_ORG_ID,
        clerk_org_id: TEST_CLERK_ORG_ID,
        name: TEST_ORG_NAME,
        slug: TEST_ORG_SLUG,
        company_id: null,
        industry: "Technology Services",
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

      if (url.includes("/api/v1/alerts/counts")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total: 2,
            new: 1,
            acknowledged: 0,
            investigating: 1,
            escalated: 0,
            resolved: 0,
            dismissed: 0,
            critical: 1,
            high: 1,
            medium: 0,
            low: 0,
          }),
        });
      }

      if (url.includes("/api/v1/alerts")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            data: [
              {
                id: "alert-1",
                org_id: TEST_ORG_ID,
                risk_assessment_id: "ra-1",
                event_id: "ev-1",
                company_id: "comp-1",
                headline: "Export Control Notice: Apex Silicon Foundries",
                explanation: "BIS regulatory notice flagged potential cross-border component review.",
                why_it_matters: "Direct operational impact on primary fab supply.",
                recommendations: ["Audit safety stock buffers", "Verify secondary sourcing"],
                severity_band: "CRITICAL",
                impact_score: 88,
                confidence: 0.95,
                status: "new",
                company_name: "Apex Silicon Foundries",
                company_country: "US",
                category: "Semiconductors",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                evidence: [
                  {
                    id: "ev-rec-1",
                    evidence_type: "source_record",
                    source_name: "Federal Register Bulletin",
                    source_url: "https://www.federalregister.gov/bulletin-123",
                    excerpt: "Export licensing requirement for semiconductor foundries updated.",
                  },
                ],
                actions: [],
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
      expect(screen.getByPlaceholderText(/siemens/i)).toBeInTheDocument();
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

  describe("Alert Center (/alerts)", () => {
    it("renders Alert Center header, dynamic KPI metrics, and filter tabs", async () => {
      render(<AlertsPage />);
      expect(screen.getByText("Alerts & Signal Stream")).toBeInTheDocument();
      expect(screen.getByText("Total Signals")).toBeInTheDocument();
      expect(screen.getByText("Critical Exposures")).toBeInTheDocument();
      expect(screen.getByText("In Investigation")).toBeInTheDocument();
      expect(screen.getAllByText("Resolved")[0]).toBeInTheDocument();

      // Action buttons
      expect(screen.getByRole("button", { name: /run risk scan/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();

      // Filter tabs
      expect(screen.getByText("All Alerts")).toBeInTheDocument();
      expect(screen.getByText("New Signals")).toBeInTheDocument();

      // Verify loaded alert card
      await waitFor(() => {
        expect(
          screen.getByText("Export Control Notice: Apex Silicon Foundries")
        ).toBeInTheDocument();
      });
      expect(screen.getAllByText("CRITICAL").length).toBeGreaterThan(0);
      expect(screen.getByText("New Signal")).toBeInTheDocument();
    });

    it("opens Alert Dossier dialog when clicking View Dossier & Evidence", async () => {
      render(<AlertsPage />);
      await waitFor(() => {
        expect(
          screen.getByText("Export Control Notice: Apex Silicon Foundries")
        ).toBeInTheDocument();
      });

      const dossierBtn = screen.getByRole("button", { name: /view dossier & evidence/i });
      fireEvent.click(dossierBtn);

      await waitFor(() => {
        expect(screen.getByText(/Root Cause & Regulatory Exposure/i)).toBeInTheDocument();
        expect(screen.getByText(/Supporting Evidence Chain/i)).toBeInTheDocument();
        expect(screen.getByText(/Federal Register Bulletin/i)).toBeInTheDocument();
      });
    });
  });
});
