"use client";

import React, { useState } from "react";
import { CornerMarks } from "./CornerMarks";
import {
  UploadCloud,
  Sparkles,
  ShieldAlert,
  FileSpreadsheet,
  CheckCircle2,
  PackageCheck,
  UserCheck,
} from "lucide-react";

export function SetupWalkthroughSection(): React.ReactElement {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      tab: "1. Ingest & Standardize",
      num: "01",
      badge: "ZERO COLD-START",
      title: "Sync ERP item masters, purchase orders, and supplier catalogs",
      description:
        "Upload a simple CSV catalog, drop in purchase orders, or connect your ERP (SAP, Coupa, NetSuite). Provenance deduplicates vendors, resolves entities against global GLEIF LEI registries, and catalogs items into standard UNSPSC categories.",
      subtext: "No manual taxonomy building required.",
      icon: UploadCloud,
    },
    {
      tab: "2. Deploy Agent Trace",
      num: "02",
      badge: "AGENTIC COPILOT",
      title: "Empower procurement with autonomous sourcing and approval routing",
      description:
        "Activate Agent Trace to parse buyer purchase requisitions into formal material requests, evaluate supplier price variances, and enforce enterprise Delegation of Authority rules automatically.",
      subtext: "Reduces transactional requisition-to-PO cycle times by 85%.",
      icon: Sparkles,
    },
    {
      tab: "3. Continuous Risk Radar",
      num: "03",
      badge: "DETERMINISTIC DEFENSE",
      title: "First cited disruption alerts and exposure scores in under 5 minutes",
      description:
        "Our deterministic engine immediately executes a 30-day retroactive sweep over all official sanctions, export controls, and regulatory registers to deliver verifiable, cited findings across your supplier network.",
      subtext: "Guaranteed visibility into live external and sub-tier exposure.",
      icon: ShieldAlert,
    },
  ];

  return (
    <section id="how-it-works" className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div data-reveal className="relative max-w-4xl mb-16 p-4 sm:p-6 bg-white/40 rounded-xl border border-neutral-200/60">
          <CornerMarks size={8} color="#c7c7c7" thickness={1} offset={-4} />

          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E]" />
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-500 font-semibold">
              Rapid Time to Value
            </span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0A0A0A] leading-tight mb-4">
            <span className="text-[#FA651E]">15 minutes</span> from data ingest to active agentic procurement.
          </h2>

          <p className="text-base sm:text-lg text-neutral-600 font-normal">
            No 6-month consulting integration. Connect your catalog and let our deterministic pipeline resolve your multi-tier risk immediately.
          </p>
        </div>

        {/* 3-Step Interactive Container */}
        <div
          data-reveal
          className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center bg-white rounded-2xl border border-neutral-200 p-8 sm:p-12 shadow-sm relative"
        >
          <CornerMarks size={12} color="#FA651E" thickness={1.5} offset={-6} />

          {/* Left: Step Tab Selectors */}
          <div className="md:col-span-5 space-y-4">
            {steps.map((st, index) => {
              const Icon = st.icon;
              const isActive = activeStep === index;
              return (
                <button
                  key={st.tab}
                  onClick={() => setActiveStep(index)}
                  className={`w-full text-left p-4 sm:p-5 rounded-xl border transition-all flex items-center justify-between group ${
                    isActive
                      ? "bg-orange-50/60 border-[#FA651E] shadow-sm text-neutral-900"
                      : "bg-neutral-50/50 border-neutral-200/70 text-neutral-500 hover:bg-neutral-100/60 hover:text-neutral-900"
                  }`}
                >
                  <div className="flex items-center gap-3.5">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${
                        isActive
                          ? "bg-[#FA651E] text-white shadow-xs"
                          : "bg-neutral-200 text-neutral-600 group-hover:bg-neutral-300"
                      }`}
                    >
                      {st.num}
                    </div>
                    <div>
                      <span className="text-sm sm:text-base font-semibold tracking-tight block">
                        {st.tab}
                      </span>
                      <span className="text-[11px] font-mono text-neutral-400 group-hover:text-neutral-500">
                        {st.badge}
                      </span>
                    </div>
                  </div>
                  <Icon
                    className={`w-5 h-5 ${
                      isActive ? "text-[#FA651E]" : "text-neutral-400 group-hover:text-neutral-600"
                    }`}
                  />
                </button>
              );
            })}
          </div>

          {/* Right: Step Detail Visual Stage */}
          <div className="md:col-span-7 bg-[#FAF9F6] rounded-xl border border-neutral-200/80 p-6 sm:p-8 flex flex-col justify-between min-h-[400px]">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FA651E]/10 border border-[#FA651E]/20 text-[#FA651E] text-xs font-mono font-bold mb-4">
                <span>STEP {steps[activeStep].num}</span>
                <span className="text-neutral-300">|</span>
                <span>{steps[activeStep].badge}</span>
              </div>

              <h3 className="text-xl sm:text-2xl font-bold text-[#0A0A0A] mb-3">
                {steps[activeStep].title}
              </h3>

              <p className="text-sm sm:text-base text-neutral-600 leading-relaxed mb-6">
                {steps[activeStep].description}
              </p>
            </div>

            {/* Custom Interactive Mockup Visuals per Step */}
            <div className="pt-4 border-t border-neutral-200">
              {activeStep === 0 && (
                <div className="p-4 rounded-lg bg-white border border-neutral-200/80 shadow-xs font-mono text-xs space-y-2.5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between text-neutral-600 pb-2 border-b border-neutral-100">
                    <span className="flex items-center gap-1.5 text-neutral-900 font-semibold">
                      <FileSpreadsheet className="w-3.5 h-3.5 text-[#FA651E]" />
                      erp_items_and_vendors.csv (840 records)
                    </span>
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold">
                      100% INGESTED
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>GLEIF Entity Resolution</span>
                    <span className="text-emerald-700 font-bold">✓ 834 Matches (99.2%)</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>Item Catalog Normalized</span>
                    <span className="text-neutral-900 font-medium">UNSPSC v25 Taxonomy Applied</span>
                  </div>
                </div>
              )}

              {activeStep === 1 && (
                <div className="p-4 rounded-lg bg-white border border-neutral-200/80 shadow-xs font-mono text-xs space-y-2.5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between text-neutral-600 pb-2 border-b border-neutral-100">
                    <span className="flex items-center gap-1.5 text-neutral-900 font-semibold">
                      <Sparkles className="w-3.5 h-3.5 text-[#FA651E]" />
                      Agent Trace Sourcing Orchestrator
                    </span>
                    <span className="text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200 font-bold">
                      ACTIVE
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>Requisition MR-2024-089</span>
                    <span className="text-neutral-900 font-semibold">500 units @ $9,700</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>Delegation Rule</span>
                    <span className="text-purple-700 font-bold">Tier L3 Routed to VP Procurement</span>
                  </div>
                </div>
              )}

              {activeStep === 2 && (
                <div className="p-4 rounded-lg bg-white border border-neutral-200/80 shadow-xs font-mono text-xs space-y-2.5 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between text-neutral-600 pb-2 border-b border-neutral-100">
                    <span className="flex items-center gap-1.5 text-neutral-900 font-semibold">
                      <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
                      30-Day Historical Sweep Complete
                    </span>
                    <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 font-bold">
                      1 HIGH IMPACT INTERSECTION
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>OFAC SDN &amp; BIS Entity Sweep</span>
                    <span className="text-emerald-700 font-bold">✓ Sub-100ms Recursive CTE</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-neutral-600">
                    <span>Audit Trail Citation</span>
                    <span className="text-neutral-900 font-semibold">Federal Register Vol. 89 § 744</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
