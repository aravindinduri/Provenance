import type { Metadata } from "next";
import { LandingPageClient } from "@/components/landing/LandingPageClient";

export const metadata: Metadata = {
  title: "Provenance — Agentic Procurement & Risk Analysis Platform",
  description:
    "Autonomous agentic procurement meets deterministic supply chain risk intelligence. Manage material requests, automate sourcing, route approvals, and continuously monitor multi-tier sanctions and trade disruption exposure.",
};

/**
 * Provenance Landing Page Root Route
 */
export default function RootPage(): React.ReactElement {
  return <LandingPageClient />;
}

