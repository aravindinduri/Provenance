"use client";

import React, { useState } from "react";
import { Navbar } from "./Navbar";
import { HeroSection } from "./HeroSection";
import { TrustBar } from "./TrustBar";
import { ShowcaseSection } from "./ShowcaseSection";
import { SetupWalkthroughSection } from "./SetupWalkthroughSection";
import { OutreachBentoGrid } from "./OutreachBentoGrid";
import { VennSection } from "./VennSection";
import { MetricsAndTestimonials } from "./MetricsAndTestimonials";
import { IntegrationsSection } from "./IntegrationsSection";
import { FinalCTASection } from "./FinalCTASection";
import { Footer } from "./Footer";
import { AgentDemoModal } from "./AgentDemoModal";
import { ScrollAnimationProvider } from "./ScrollAnimationProvider";

// LandingPageClient - Agentic Procurement & Risk Analysis Platform
export function LandingPageClient(): React.ReactElement {
  const [demoDomain, setDemoDomain] = useState("yourcompany.com");
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);

  const handleLaunchDemo = (domain: string) => {
    setDemoDomain(domain || "yourcompany.com");
    setIsDemoModalOpen(true);
  };

  return (
    <ScrollAnimationProvider>
      <div className="min-h-screen bg-[#FAF9F6] text-[#0A0A0A] font-sans selection:bg-[#FA651E]/20 selection:text-[#FA651E] antialiased">
        {/* Navigation */}
        <Navbar />

        {/* Main Content Sections with GSAP ScrollTrigger Animations */}
        <main>
          {/* 1. Hero Section: Autonomous S2P Copilot + Deterministic Math */}
          <HeroSection onLaunchDemo={handleLaunchDemo} />

          {/* 2. Customer Trust Logo Bar */}
          <TrustBar />

          {/* 3. 4-Stage Product Showcase: Material Requisitions to Cited Approvals */}
          <ShowcaseSection onLaunchDemo={() => handleLaunchDemo("provenance.io")} />

          {/* 4. 3-Step Setup Walkthrough: Data Ingest to Active Defense */}
          <SetupWalkthroughSection />

          {/* 5. Capability Bento Grid: Agent Trace, Deterministic Math, Topology */}
          <OutreachBentoGrid />

          {/* 6. Unified Venn Diagram: S2P Core + Risk Integration */}
          <VennSection />

          {/* 7. Enterprise Metrics & Testimonials */}
          <MetricsAndTestimonials />

          {/* 8. Integrations Hub: ERPs, P2P, Legal Gazettes */}
          <IntegrationsSection />

          {/* 9. Final Call-To-Action Banner */}
          <FinalCTASection onLaunchDemo={handleLaunchDemo} />
        </main>

        {/* Footer */}
        <Footer />

        {/* Interactive Domain / Supplier Entity Scanner Modal */}
        <AgentDemoModal
          isOpen={isDemoModalOpen}
          onClose={() => setIsDemoModalOpen(false)}
          domain={demoDomain}
        />
      </div>
    </ScrollAnimationProvider>
  );
}
