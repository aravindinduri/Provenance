import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GraphPage from "@/app/(dashboard)/graph/page";
import { useUserStore } from "@/lib/store/user-store";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/graph",
}));

describe("Phase 7 — Supply Chain Graph Visualizer", () => {
  beforeEach(() => {
    useUserStore.getState().setFromMe({
      user_id: "test_user_risk_mgr",
      email: "risk@apex.com",
      org_id: "00000000-0000-0000-0000-000000000001",
      clerk_org_id: "clerk_org_1",
      role: "analyst",
      persona: "risk_manager",
      assigned_categories: ["Semiconductors", "Alloys"],
      organization: {
        id: "00000000-0000-0000-0000-000000000001",
        clerk_org_id: "clerk_org_1",
        name: "Apex Turbine Systems",
        slug: "apex-turbines",
        company_id: null,
        industry: "Aerospace",
        country: "US",
        subscription_tier: "enterprise",
        monthly_token_budget: 5000000,
        onboarding_completed_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });

    // Mock global fetch
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/v1/graph/paths")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            from_node: {
              id: "comp_tsmc",
              label: "Taiwan Semiconductor Mfg Co",
              type: "company",
              country: "TW",
            },
            to_node: {
              id: "org_current",
              label: "Apex Turbine Systems",
              type: "organization",
              country: "US",
            },
            paths: [
              {
                depth: 1,
                path_confidence: 1.0,
                explanation:
                  "Path from Taiwan Semiconductor Mfg Co reaches Apex Turbine Systems across 1 tier(s) with 100.0% cumulative confidence. Supply Chain Route: Taiwan Semiconductor Mfg Co -> Apex Turbine Systems. Exposure impacts Apex Turbine Systems with $8,500,000 direct annual spend (Criticality: 5/5) via supplies_to.",
                nodes: [
                  {
                    id: "comp_tsmc",
                    label: "Taiwan Semiconductor Mfg Co",
                    type: "company",
                    country: "TW",
                  },
                  {
                    id: "org_current",
                    label: "Apex Turbine Systems",
                    type: "organization",
                    country: "US",
                  },
                ],
                edges: [
                  {
                    id: "edge_1",
                    source: "comp_tsmc",
                    target: "org_current",
                    relationship_type: "supplies_to",
                    tier: 1,
                    criticality: 5,
                    annual_spend_usd: 8500000,
                    confidence: 1.0,
                  },
                ],
              },
            ],
            summary:
              "Discovered 1 verified supply chain path(s) connecting Taiwan Semiconductor Mfg Co to Apex Turbine Systems across up to 1 tiers. Highest path confidence: 100.0%.",
          }),
        });
      }

      if (url.includes("/api/v1/graph")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            nodes: [
              {
                id: "org_current",
                label: "Apex Turbine Systems",
                type: "organization",
                country: "US",
                risk_level: "LOW",
              },
              {
                id: "comp_tsmc",
                entity_id: "comp-001",
                label: "Taiwan Semiconductor Mfg Co",
                type: "company",
                country: "TW",
                risk_level: "HIGH",
                risk_score: 72.0,
                annual_spend_usd: 8500000,
                criticality: 5,
                tier: 1,
                category: "Semiconductors",
                single_source: true,
              },
              {
                id: "comp_henan",
                entity_id: "comp-006",
                label: "Henan Yixin Heavy Alloys",
                type: "company",
                country: "CN",
                risk_level: "CRITICAL",
                risk_score: 86.5,
                annual_spend_usd: 1900000,
                criticality: 5,
                tier: 2,
                category: "Raw Alloys",
                single_source: true,
              },
            ],
            edges: [
              {
                id: "edge_1",
                source: "comp_tsmc",
                target: "org_current",
                relationship_type: "supplies_to",
                tier: 1,
                criticality: 5,
                annual_spend_usd: 8500000,
                confidence: 1.0,
                single_source: true,
              },
              {
                id: "edge_2",
                source: "comp_henan",
                target: "comp_tsmc",
                relationship_type: "sub_supplies_to",
                tier: 2,
                criticality: 5,
                annual_spend_usd: 1900000,
                confidence: 0.9,
                single_source: true,
              },
            ],
            meta: {
              depth: 3,
              node_count: 3,
              edge_count: 2,
              truncated: false,
            },
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  it("renders the Supply Chain Graph Visualizer header and metrics", async () => {
    render(<GraphPage />);

    expect(screen.getByText("Supply Chain Graph Visualizer")).toBeInTheDocument();
    expect(screen.getByText("Phase 7 Topology Engine")).toBeInTheDocument();

    // Check metric cards
    expect(screen.getByText("Total Entities")).toBeInTheDocument();
    expect(screen.getByText("Direct Suppliers")).toBeInTheDocument();
    expect(screen.getByText("Sub-tier Network")).toBeInTheDocument();
    expect(screen.getByText("Single Points of Failure")).toBeInTheDocument();
    expect(screen.getByText("High / Critical Risk")).toBeInTheDocument();
  });

  it("renders filter toolbar with search, layout modes, and selectors", async () => {
    render(<GraphPage />);

    // Search input
    expect(
      screen.getByPlaceholderText(/Search companies by name or country/i)
    ).toBeInTheDocument();

    // Layout buttons
    expect(screen.getByText("Hierarchy (Dagre)")).toBeInTheDocument();
    expect(screen.getByText("Clusters (Cose)")).toBeInTheDocument();
    expect(screen.getByText("Radial")).toBeInTheDocument();

    // Refresh and manage buttons
    expect(screen.getByRole("button", { name: /Refresh Graph/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Manage Suppliers/i })).toBeInTheDocument();
  });

  it("renders Topology Navigator empty-state guide when no node is selected", async () => {
    render(<GraphPage />);

    expect(screen.getByText("Topology Navigator")).toBeInTheDocument();
    expect(screen.getByText(/Red nodes: Critical\/High external risk exposure/i)).toBeInTheDocument();
    expect(screen.getByText(/Purple hexagon: Your organization anchor/i)).toBeInTheDocument();
  });

  it("switches layout mode when clicking layout buttons", async () => {
    render(<GraphPage />);

    const coseBtn = screen.getByText("Clusters (Cose)");
    fireEvent.click(coseBtn);
    expect(coseBtn).toHaveClass("bg-purple-600");

    const radialBtn = screen.getByText("Radial");
    fireEvent.click(radialBtn);
    expect(radialBtn).toHaveClass("bg-purple-600");
  });

  it("allows typing in the search filter", async () => {
    render(<GraphPage />);

    const searchInput = screen.getByPlaceholderText(/Search companies by name or country/i);
    fireEvent.change(searchInput, { target: { value: "Taiwan" } });
    expect(searchInput).toHaveValue("Taiwan");
  });

  it("refreshes graph data when clicking refresh button", async () => {
    render(<GraphPage />);

    const refreshBtn = screen.getByRole("button", { name: /Refresh Graph/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/graph?depth=3")
      );
    });
  });
});

