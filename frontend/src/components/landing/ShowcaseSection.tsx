"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { CornerMarks } from "./CornerMarks";
import {
  PackageCheck,
  Sparkles,
  Network,
  ShieldCheck,
  ArrowRight,
  Database,
  ExternalLink,
  ClipboardList,
  CheckCircle2,
  FileText,
  UserCheck,
} from "lucide-react";

interface ShowcaseSectionProps {
  onLaunchDemo?: () => void;
}

export function ShowcaseSection({ onLaunchDemo }: ShowcaseSectionProps): React.ReactElement {
  const [activeStage, setActiveStage] = useState(0);

  const stages = [
    {
      step: "1/4",
      title: "Material Requests & Unified Item Catalog",
      tag: "P2P FOUNDATION",
      description:
        "Centralize parts, standard unit prices, and purchase requisitions. Provenance ingests your ERP item master, maps items to UNSPSC categories, and tracks preferred supplier lead times with zero manual taxonomy overhead.",
      icon: PackageCheck,
    },
    {
      step: "2/4",
      title: "Agent Trace: Autonomous Procurement Copilot",
      tag: "AGENTIC ORCHESTRATION",
      description:
        "Agent Trace acts as an autonomous co-pilot for buyers and category managers. Conversational natural language requests automatically generate validated material requisitions, compare supplier quotes, and identify cost variances.",
      icon: Sparkles,
    },
    {
      step: "3/4",
      title: "Deterministic Multi-Tier Risk Analysis",
      tag: "DETERMINISTIC TOPOLOGY",
      description:
        "Before purchase orders are awarded, Provenance recursively traverses sub-tier foundries and sub-contractors (Tier 1→3) against official registers (OFAC SDN, BIS Entity List, EU Sanctions). Zero hallucinated arithmetic.",
      icon: Network,
    },
    {
      step: "4/4",
      title: "Delegation of Authority & Cited Audit Trail",
      tag: "GOVERNANCE & APPROVALS",
      description:
        "Deterministic approval routing enforces enterprise spend thresholds and compliance rules. Every approval packet links directly to verified legal gazette notices, contract terms, and supplier scorecards.",
      icon: ShieldCheck,
      hasCta: true,
    },
  ];

  // Auto-advance stages every 8 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % stages.length);
    }, 8000);
    return () => clearInterval(timer);
  }, [stages.length]);

  return (
    <section id="procurement" className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header with Corner Marks */}
        <div data-reveal className="relative max-w-4xl mb-16 p-4 sm:p-6 bg-white/40 rounded-xl border border-neutral-200/60">
          <CornerMarks size={8} color="#c7c7c7" thickness={1} offset={-4} />

          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E] animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-500 font-semibold">
              End-to-End Platform Architecture
            </span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-[-0.035em] text-[#0A0A0A] leading-tight mb-4">
            From natural language requisition to <br className="hidden sm:inline" />
            <span className="text-[#FA651E]">verified disruption defense</span>.
          </h2>

          <p className="text-base sm:text-lg text-neutral-600 max-w-2xl font-normal">
            A cohesive 4-stage architecture uniting transactional procurement workflows with multi-tier geopolitical and regulatory risk scoring.
          </p>
        </div>

        {/* 4-Stage Showcase Container */}
        <div
          data-reveal
          className="relative bg-white rounded-2xl border border-neutral-200 shadow-[0_12px_40px_rgba(0,0,0,0.04)] overflow-hidden"
        >
          <CornerMarks size={12} color="#FA651E" thickness={1.5} offset={-6} />

          {/* Top Stage Tabs Navigation */}
          <div className="grid grid-cols-2 md:grid-cols-4 border-b border-neutral-200 bg-neutral-50/70">
            {stages.map((stg, idx) => {
              const Icon = stg.icon;
              return (
                <button
                  key={stg.step}
                  onClick={() => setActiveStage(idx)}
                  className={`p-4 text-left border-r last:border-r-0 border-neutral-200 transition-all flex flex-col justify-between ${
                    activeStage === idx
                      ? "bg-white text-neutral-900 border-b-2 border-b-[#FA651E]"
                      : "text-neutral-500 hover:bg-white/60 hover:text-neutral-800"
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                        activeStage === idx
                          ? "bg-[#FA651E]/15 text-[#FA651E]"
                          : "bg-neutral-200/70 text-neutral-600"
                      }`}
                    >
                      <Icon className="w-3 h-3" />
                      Stage {stg.step}
                    </span>
                    {activeStage === idx && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#FA651E]" />
                    )}
                  </div>
                  <span className="text-xs sm:text-sm font-semibold tracking-tight line-clamp-1">
                    {stg.title}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Main Stage Display (Left Copy + Right Visual) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[480px]">
            {/* Left Copy Panel */}
            <div className="lg:col-span-5 p-8 sm:p-12 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-neutral-200 bg-white">
              <div>
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FA651E]/10 text-[#FA651E] text-xs font-mono font-bold mb-6">
                  <span>⬡</span>
                  <span>{stages[activeStage].step}</span>
                  <span className="text-neutral-300">|</span>
                  <span>{stages[activeStage].tag}</span>
                </div>

                <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#0A0A0A] leading-tight mb-4">
                  {stages[activeStage].title}
                </h3>

                <p className="text-base text-neutral-600 leading-relaxed font-normal">
                  {stages[activeStage].description}
                </p>
              </div>

              {/* Stage Contextual Badges / CTA */}
              <div className="pt-8">
                {activeStage === 0 && (
                  <div className="flex flex-col gap-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-neutral-200 bg-neutral-50 text-xs font-mono text-neutral-700">
                      <Database className="w-3.5 h-3.5 text-[#FA651E]" />
                      <span>Item Master Catalog · UNSPSC Taxonomy</span>
                    </div>
                    <Link
                      href="/material-requests"
                      className="text-xs font-semibold text-[#FA651E] hover:underline flex items-center gap-1 mt-1"
                    >
                      Explore Material Requests →
                    </Link>
                  </div>
                )}

                {activeStage === 1 && (
                  <div className="flex flex-col gap-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-purple-200 bg-purple-50 text-xs font-mono text-purple-900">
                      <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                      <span>Agent Trace Autonomous Copilot</span>
                    </div>
                    <Link
                      href="/trace"
                      className="text-xs font-semibold text-[#FA651E] hover:underline flex items-center gap-1 mt-1"
                    >
                      Open Agent Trace Workspace →
                    </Link>
                  </div>
                )}

                {activeStage === 2 && (
                  <div className="flex flex-col gap-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-orange-200 bg-orange-50 text-xs font-mono text-orange-900">
                      <Network className="w-3.5 h-3.5 text-[#FA651E]" />
                      <span>GLEIF Level-2 Resolution · Recursive CTE Graph</span>
                    </div>
                    <Link
                      href="/graph"
                      className="text-xs font-semibold text-[#FA651E] hover:underline flex items-center gap-1 mt-1"
                    >
                      Inspect Multi-Tier Graph →
                    </Link>
                  </div>
                )}

                {activeStage === 3 && (
                  <div className="flex items-center gap-3">
                    <Link
                      href="/approvals"
                      className="inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-[#0A0A0A] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold transition-all shadow-md group"
                    >
                      <span>View Approval Queue</span>
                      <ArrowRight className="w-4 h-4 text-[#FD8A6B] group-hover:translate-x-1 transition-transform" />
                    </Link>
                    {onLaunchDemo && (
                      <button
                        onClick={onLaunchDemo}
                        className="px-4 py-3 rounded-lg border border-neutral-300 text-neutral-800 text-xs sm:text-sm font-medium hover:bg-neutral-50 transition-colors"
                      >
                        Try Live Demo
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Right Visual Stage Panel */}
            <div className="lg:col-span-7 p-6 sm:p-10 bg-[#FAF9F6] flex items-center justify-center relative overflow-hidden">
              {/* STAGE 1 VISUAL: Material Request & Item Catalog */}
              {activeStage === 0 && (
                <div className="w-full max-w-lg space-y-3 font-mono text-xs animate-in fade-in duration-300">
                  <div className="p-3.5 rounded-lg bg-white border border-neutral-200/90 shadow-sm flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <ClipboardList className="w-4 h-4 text-[#FA651E]" />
                      <span className="text-neutral-900 font-bold">MR-2024-089 (Apollo Q4 Run)</span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                      APPROVED DRAFT
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-white border border-neutral-200/80 shadow-sm space-y-2.5">
                    <div className="flex items-center justify-between text-[11px] pb-2 border-b border-neutral-100">
                      <span className="text-neutral-500">Catalog Item Code:</span>
                      <span className="text-neutral-900 font-bold">ITM-SIC-001 (Silicon Carbide)</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div>
                        <span className="text-neutral-400 block">Unit Cost:</span>
                        <span className="text-neutral-800 font-semibold">$9,700.00 / ea</span>
                      </div>
                      <div>
                        <span className="text-neutral-400 block">Quantity:</span>
                        <span className="text-neutral-800 font-semibold">500 units</span>
                      </div>
                      <div>
                        <span className="text-neutral-400 block">Preferred Supplier:</span>
                        <span className="text-neutral-800 font-semibold">Apex Avionics AG</span>
                      </div>
                      <div>
                        <span className="text-neutral-400 block">Lead Time:</span>
                        <span className="text-neutral-800 font-semibold">60 days</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-orange-50/60 border border-orange-200 text-[11px] flex items-center justify-between">
                    <span className="text-orange-900 font-medium">Requisition Total Estimate:</span>
                    <span className="font-bold text-orange-950 text-sm">$4,850,000.00</span>
                  </div>
                </div>
              )}

              {/* STAGE 2 VISUAL: Agent Trace Autonomous Sourcing Copilot */}
              {activeStage === 1 && (
                <div className="w-full max-w-lg space-y-3 font-mono text-xs animate-in fade-in duration-300">
                  <div className="p-3.5 rounded-lg bg-white border border-neutral-200/90 shadow-sm flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#FA651E]" />
                      <span className="text-neutral-900 font-bold">Agent Trace Autonomous Session</span>
                    </div>
                    <span className="text-[10px] text-purple-700 bg-purple-50 px-2 py-0.5 rounded font-semibold border border-purple-200">
                      COPILOT ACTIVE
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-neutral-50 border border-neutral-200 text-[11px] space-y-2">
                    <div className="text-neutral-500 text-[10px]">THINKING PROCESS &amp; TOOL CALLS:</div>
                    <div className="flex items-center gap-2 text-neutral-800">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>Parsed natural language specs into MR-2024-089</span>
                    </div>
                    <div className="flex items-center gap-2 text-neutral-800">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>Compared 3 supplier quotations (Apex vs. Siltronic vs. Sumco)</span>
                    </div>
                    <div className="flex items-center gap-2 text-rose-700 font-medium">
                      <span className="font-bold">⚠</span>
                      <span>Flagged Tier-2 dependency on BIS restricted entity</span>
                    </div>
                    <div className="flex items-center gap-2 text-neutral-800">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>Synthesized alternative sourcing packet with 12% cost variance</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-white border border-neutral-200 flex items-center justify-between text-[11px]">
                    <span className="text-neutral-600">Action: Generated Approval Packet</span>
                    <span className="text-emerald-700 font-bold">Ready for Delegation L3</span>
                  </div>
                </div>
              )}

              {/* STAGE 3 VISUAL: Deterministic Multi-Tier Risk Analysis */}
              {activeStage === 2 && (
                <div className="w-full max-w-lg space-y-3 font-mono text-xs animate-in fade-in duration-300">
                  <div className="p-3.5 rounded-lg bg-white border border-neutral-200/90 shadow-sm flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-2 h-2 rounded-full bg-[#FA651E]" />
                      <span className="text-neutral-900 font-bold">Enterprise Multi-Tier Tree</span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600 font-semibold">
                      DEPTH: 3 TIERS
                    </span>
                  </div>

                  <div className="pl-6 border-l-2 border-dashed border-orange-300 space-y-2.5">
                    <div className="p-2.5 rounded-lg bg-white border border-neutral-200/80 shadow-xs flex items-center justify-between">
                      <div>
                        <div className="text-neutral-900 font-semibold">Tier-1: Apex Avionics AG</div>
                        <div className="text-[10px] text-neutral-500">LEI: 529900T8BM49AURSDO55 · $14.2M Annual Spend</div>
                      </div>
                      <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-semibold border border-emerald-200">
                        DIRECT VENDOR
                      </span>
                    </div>

                    <div className="pl-6 border-l-2 border-dashed border-rose-300 space-y-2">
                      <div className="p-2.5 rounded-lg bg-rose-50/70 border border-rose-200 shadow-xs flex items-center justify-between">
                        <div>
                          <div className="text-rose-900 font-semibold">Tier-2: Shenzhen Micro Ingot</div>
                          <div className="text-[10px] text-rose-700">Sub-Tier Foundry · Silicon Carbide Substrates</div>
                        </div>
                        <span className="text-[10px] text-rose-700 bg-rose-100 px-2 py-0.5 rounded font-bold border border-rose-200">
                          BIS RESTRICTED
                        </span>
                      </div>

                      <div className="pl-6 border-l-2 border-dashed border-neutral-300">
                        <div className="p-2 rounded bg-white border border-neutral-200 text-[10px] text-neutral-600 flex items-center justify-between">
                          <span>Tier-3: Baotou Rare Earth Mining Corp</span>
                          <span className="text-neutral-500">Raw Mineral Ingot</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-white border border-neutral-200/90 shadow-sm flex items-center justify-between">
                    <div>
                      <div className="text-xs text-neutral-800 font-bold uppercase">Computed Composite Risk</div>
                      <div className="text-[10px] text-neutral-500">Deterministic SQL CTE calculation</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-black text-rose-600">92 / 100</div>
                      <span className="text-[9px] text-rose-700 uppercase font-bold tracking-wider">
                        CRITICAL SEVERITY
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* STAGE 4 VISUAL: Delegation of Authority & Cited Audit Trail */}
              {activeStage === 3 && (
                <div className="w-full max-w-lg space-y-3 font-mono text-xs animate-in fade-in duration-300">
                  <div className="p-3.5 rounded-lg bg-white border border-neutral-200/90 shadow-sm">
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-neutral-100">
                      <span className="text-neutral-900 font-bold flex items-center gap-2">
                        <UserCheck className="w-3.5 h-3.5 text-[#FA651E]" />
                        Approval Queue &amp; Delegation Engine
                      </span>
                      <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-semibold border border-emerald-200">
                        GOVERNANCE ENFORCED
                      </span>
                    </div>
                    <div className="space-y-1.5 text-[11px]">
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-500">Routing Rule:</span>
                        <span className="text-neutral-900 font-semibold">Tier L3 (&gt; $1.0M Spend)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-500">Designated Approver:</span>
                        <span className="text-neutral-900 font-semibold">Sarah Jenkins (VP Procurement)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-neutral-500">Compliance Check:</span>
                        <span className="text-emerald-700 font-bold">Alternate Vendor Quote Attached</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="p-2.5 rounded bg-white border border-neutral-200/80 shadow-xs flex items-center justify-between text-[11px]">
                      <span className="text-neutral-600 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-neutral-400" />
                        Citation: Federal Register Vol. 89 § 744
                      </span>
                      <span className="text-[#FA651E] font-semibold flex items-center gap-1">
                        Official Gazette <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-white border border-neutral-200/80 shadow-xs flex items-center justify-between text-[11px]">
                      <span className="text-neutral-600 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Contract Exhibit C (Price Escalator Clause)
                      </span>
                      <span className="text-[#FA651E] font-semibold flex items-center gap-1">
                        SAP PO #49219 <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>
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
