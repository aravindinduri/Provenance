/**
 * src/lib/store/ui-store.ts — UI state for navigation, persona selection, and theme.
 *
 * Manages:
 *   1. Active persona: "risk_manager" | "category_manager"
 *      - Risk Manager: Focuses on external geopolitical/regulatory signals and exposure paths.
 *      - Category Manager: Focuses on categories, supplier spend, and action plans.
 *   2. Sidebar collapsed state.
 *   3. Command palette open state.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Persona = "risk_manager" | "category_manager";

interface UIState {
  persona: Persona;
  isSidebarCollapsed: boolean;
  isCommandPaletteOpen: boolean;
  selectedCategory: string | null;

  // Actions
  setPersona: (persona: Persona) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setSelectedCategory: (category: string | null) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      persona: "risk_manager",
      isSidebarCollapsed: false,
      isCommandPaletteOpen: false,
      selectedCategory: null,

      setPersona: (persona: Persona) => set({ persona }),
      toggleSidebar: () =>
        set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
      setSidebarCollapsed: (collapsed: boolean) =>
        set({ isSidebarCollapsed: collapsed }),
      setCommandPaletteOpen: (open: boolean) =>
        set({ isCommandPaletteOpen: open }),
      setSelectedCategory: (category: string | null) =>
        set({ selectedCategory: category }),
    }),
    {
      name: "provenance-ui-storage",
      partialize: (state) => ({
        persona: state.persona,
        isSidebarCollapsed: state.isSidebarCollapsed,
      }),
    }
  )
);
