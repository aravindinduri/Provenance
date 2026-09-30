import { describe, it, expect, beforeEach, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "@/components/shell/sidebar";
import { Header } from "@/components/shell/header";
import { PersonaSwitcher } from "@/components/shell/persona-switcher";
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
      orgName: "Acme Industrial Group",
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
      expect(screen.getByText("Investigate")).toBeInTheDocument();
      expect(screen.getByText("Data")).toBeInTheDocument();
      expect(screen.getByText("Settings")).toBeInTheDocument();
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
  });

  describe("PersonaSwitcher", () => {
    it("renders both personas and switches active persona", () => {
      render(<PersonaSwitcher />);
      const riskBtn = screen.getByRole("button", { name: /risk manager/i });
      const categoryBtn = screen.getByRole("button", { name: /category manager/i });

      expect(riskBtn).toBeInTheDocument();
      expect(categoryBtn).toBeInTheDocument();

      fireEvent.click(categoryBtn);
      expect(useUIStore.getState().persona).toBe("category_manager");

      fireEvent.click(riskBtn);
      expect(useUIStore.getState().persona).toBe("risk_manager");
    });
  });

  describe("Header", () => {
    it("renders the 9 Sources Active status pill and persona switcher", () => {
      render(<Header />);
      expect(screen.getByText("9 Sources Active")).toBeInTheDocument();
      expect(screen.getByText("SLO Freshness: <1h")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /risk manager/i })).toBeInTheDocument();
    });
  });
});
