import { describe, it, expect, beforeEach, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "@/components/shell/sidebar";
import { useUIStore } from "@/lib/store/ui-store";
import { useUserStore } from "@/lib/store/user-store";

// Mock @clerk/nextjs
vi.mock("@clerk/nextjs", () => ({
  useClerk: () => ({
    signOut: vi.fn(),
  }),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

describe("App Shell & Navigation", () => {
  beforeEach(() => {
    useUIStore.setState({
      persona: "risk_manager",
      isSidebarCollapsed: false,
    });
    useUserStore.setState({
      userId: "usr_123",
      email: "risk.manager@provenance.internal",
      role: "org_admin",
      isPlatformAdmin: false,
      orgName: process.env.TEST_ORG_NAME || "Provenance Organization",
    });
  });

  describe("Sidebar", () => {
    it("renders core navigation items", () => {
      render(<Sidebar />);
      expect(screen.getByText("PROVENANCE")).toBeInTheDocument();
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Alerts")).toBeInTheDocument();
      expect(screen.getByText("Suppliers")).toBeInTheDocument();
      expect(screen.getByText("Graph")).toBeInTheDocument();
      expect(screen.getByText("Trace")).toBeInTheDocument();
      expect(screen.getByText("Purchase Order")).toBeInTheDocument();
      expect(screen.getByText("Purchase Receipt")).toBeInTheDocument();
    });

    it("hides platform admin link for regular org admins", () => {
      render(<Sidebar />);
      expect(screen.queryByText("Platform Admin")).not.toBeInTheDocument();
    });

    it("shows platform admin link when user isPlatformAdmin is true", () => {
      useUserStore.setState({ isPlatformAdmin: true, role: "platform_admin" });
      render(<Sidebar />);
      expect(screen.getByText("Platform Admin")).toBeInTheDocument();
    });

    it("toggles collapse state when collapse button is clicked", () => {
      render(<Sidebar />);
      const collapseBtn = screen.getByRole("button", { name: /collapse sidebar/i });
      fireEvent.click(collapseBtn);
      expect(useUIStore.getState().isSidebarCollapsed).toBe(true);
    });

    it("renders the user menu at the bottom of sidebar", () => {
      render(<Sidebar />);
      expect(screen.getByText("risk.manager")).toBeInTheDocument();
    });
  });
});
