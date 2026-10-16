"use client";

import React, { useState } from "react";
import { CornerMarks } from "./CornerMarks";
import {
  Shield,
  ArrowRight,
  Search,
  AlertTriangle,
  Network,
  CheckCircle2,
  Lock,
  Sparkles,
  ClipboardList,
  PackageCheck,
  FileText,
  UserCheck,
} from "lucide-react";

interface HeroSectionProps {
  onLaunchDemo: (domain: string) => void;
}

export function HeroSection({ onLaunchDemo }: HeroSectionProps): React.ReactElement {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) {
      setError("Please enter a supplier, item code, or domain (e.g. tsmc.com, ITM-SIC-01, basf.com)");
      return;
    }
    setError("");
    onLaunchDemo(url.trim());
  };

  return (
    <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden bg-[#FAF9F6]">
      {/* Background Ambience: Signature Warm Peach / Coral Radial Mesh with Parallax Float */}
      <div
        data-parallax-float
        data-parallax-speed="0.15"
        className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[640px] opacity-75"
        style={{
          background:
            "radial-gradient(ellipse at 50% 15%, rgba(253, 138, 107, 0.3) 0%, rgba(250, 101, 30, 0.12) 40%, transparent 72%)",
        }}
        aria-hidden="true"
      />

      {/* Decorative Subtle Flowing Vectors */}
      <svg
        data-parallax-float
        data-parallax-speed="0.25"
        className="pointer-events-none absolute top-12 left-0 w-full h-[650px] opacity-40 -z-10"
        viewBox="0 0 1440 650"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M-50,80 C200,80 320,320 360,520"
          stroke="#FA651E"
          strokeWidth="1.2"
          strokeDasharray="4 4"
          opacity="0.35"
        />
        <path
          d="M-20,120 C180,140 280,360 360,520"
          stroke="#FD8A6B"
          strokeWidth="1.5"
          opacity="0.5"
        />
        <path
          d="M1490,80 C1240,80 1120,320 1080,520"
          stroke="#FA651E"
          strokeWidth="1.2"
          strokeDasharray="4 4"
          opacity="0.35"
        />
        <path
          d="M1460,120 C1260,140 1160,360 1080,520"
          stroke="#FD8A6B"
          strokeWidth="1.5"
          opacity="0.5"
        />
      </svg>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        {/* Status Badge with Corner Ticks */}
        <div data-reveal className="inline-flex items-center justify-center mb-7">
          <div className="relative px-3.5 py-1.5 bg-white/80 backdrop-blur-sm border border-neutral-200/80 rounded text-xs font-mono tracking-tight text-neutral-800 shadow-[0_2px_8px_rgba(0,0,0,0.03)] flex items-center gap-2">
            <CornerMarks size={6} color="#d4d4d4" thickness={1} offset={-3} />
            <Sparkles className="w-3.5 h-3.5 text-[#FA651E] animate-pulse" />
            <span className="text-neutral-500">AGENTIC PROCUREMENT &amp; RISK ANALYSIS</span>
            <span className="text-neutral-300">|</span>
            <span className="text-[#FA651E] font-semibold">AUTONOMOUS S2P COPILOT</span>
          </div>
        </div>

        {/* Hero Headline */}
        <h1
          data-reveal
          className="text-4xl sm:text-6xl lg:text-[66px] font-extrabold tracking-[-0.04em] text-[#0A0A0A] leading-[1.08] sm:leading-[1.06] mb-6"
        >
          Autonomous agentic procurement meets <br className="hidden sm:inline" />
          <span className="text-[#FA651E]">deterministic risk intelligence</span>.
        </h1>

        {/* Hero Subheadline */}
        <p
          data-reveal
          className="max-w-3xl mx-auto text-base sm:text-lg text-neutral-600 leading-relaxed font-normal mb-9"
        >
          Orchestrate source-to-pay workflows while preempting multi-tier supply disruptions. Provenance
          automates material requests, quotes comparison, and approval guardrails — continuously resolving
          supplier relationships against global trade sanctions with cited legal evidence.
        </p>

        {/* Interactive Domain / Supplier Entity Scanner */}
        <div data-reveal className="max-w-xl mx-auto mb-8 relative">
          <form
            onSubmit={handleSubmit}
            className="relative p-1.5 bg-white rounded-xl border border-neutral-200/90 shadow-[0_8px_30px_rgb(0,0,0,0.06)] flex flex-col sm:flex-row items-center gap-2"
          >
            <CornerMarks size={8} color="#a3a3a3" thickness={1.2} offset={-4} />

            <div className="flex-1 flex items-center w-full px-3.5 py-2">
              <Search className="w-4 h-4 text-neutral-400 mr-2.5 shrink-0" />
              <input
                type="text"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (error) setError("");
                }}
                placeholder="Enter supplier, part specification, or domain (e.g. tsmc.com, ITM-SIC-01)"
                className="w-full bg-transparent text-sm sm:text-base text-neutral-900 placeholder-neutral-400 focus:outline-none"
                aria-label="Enter supplier name or item code"
              />
            </div>

            <button
              type="submit"
              className="w-full sm:w-auto px-6 py-3 bg-[#0A0A0A] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold tracking-tight rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shrink-0 group shadow-md"
            >
              <Sparkles className="w-4 h-4 text-[#FD8A6B]" />
              <span>Simulate Agent Trace</span>
              <ArrowRight className="w-4 h-4 text-[#FD8A6B] group-hover:translate-x-0.5 transition-transform" />
            </button>
          </form>

          {error && (
            <p className="text-xs text-rose-600 mt-2 font-medium text-left px-2">
              {error}
            </p>
          )}

        </div>

        {/* Social Proof Row */}
        <div
          data-reveal
          className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-10 text-xs sm:text-[13px] text-neutral-600 mb-14"
        >
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-full bg-[#FA651E]/10 text-[#FA651E] flex items-center justify-center font-bold text-[11px] border border-[#FA651E]/20">
              ✓
            </div>
            <span className="text-neutral-700 font-medium">
              &ldquo;Cut requisition-to-award cycle time by 85% while flagging Tier-2 export curbs automatically.&rdquo;
            </span>
          </div>

          <div className="hidden sm:block w-px h-4 bg-neutral-300" />

          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#FA651E]" />
            <span className="font-semibold text-neutral-900">Deterministic Math Guardrail</span>
            <span className="text-neutral-500 font-mono">0% Calculation Hallucination</span>
          </div>
        </div>

        {/* Browser Chrome Preview (app.provenance.ai/trace) */}
        <div
          data-reveal
          className="relative max-w-5xl mx-auto rounded-xl border border-neutral-200 bg-white shadow-[0_24px_60px_rgba(0,0,0,0.08)] overflow-hidden text-left"
        >
          <CornerMarks size={10} color="#a3a3a3" thickness={1.2} offset={-5} />

          {/* Browser Top Chrome */}
          <div className="h-11 bg-neutral-100/80 border-b border-neutral-200 px-4 flex items-center justify-between">
            {/* Window Dots */}
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
              <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
              <div className="w-3 h-3 rounded-full bg-[#10B981]" />
            </div>

            {/* URL Bar */}
            <div className="max-w-md w-full bg-white border border-neutral-200/90 rounded-md py-1 px-3 flex items-center justify-center gap-2 text-xs font-mono text-neutral-600 shadow-inner">
              <Lock className="w-3 h-3 text-[#10B981]" />
              <span>https://app.provenance.ai/trace</span>
              <span className="text-[10px] text-neutral-400">· workspace: aerospace_procurement</span>
            </div>

            {/* Platform Tag */}
            <div className="text-[11px] font-mono text-[#FA651E] font-semibold flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              <span className="hidden sm:inline">Trace Copilot v2.0</span>
            </div>
          </div>

          {/* Unified Agentic Procurement & Risk App Preview */}
          <div className="p-4 sm:p-6 bg-[#FAF9F6] grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Left Column: Autonomous Agent Trace Session */}
            <div className="lg:col-span-7 bg-white p-4 sm:p-5 rounded-lg border border-neutral-200/80 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-4 border-b border-neutral-100">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E] animate-pulse" />
                    <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-neutral-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-[#FA651E]" />
                      Autonomous Copilot Trace
                    </h4>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-50 text-[#FA651E] border border-orange-200 font-semibold">
                    EXECUTION ACTIVE
                  </span>
                </div>

                {/* Trace Event 1: Natural Language Requisition Parse */}
                <div className="space-y-3 font-mono text-xs">
                  <div className="p-3 rounded-lg border border-neutral-200 bg-neutral-50/70">
                    <div className="flex items-center justify-between text-[11px] text-neutral-500 mb-1">
                      <span className="font-semibold text-neutral-800 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-neutral-600" />
                        Buyer Prompt &amp; Natural Language Sourcing
                      </span>
                      <span>14:02:18</span>
                    </div>
                    <p className="text-[11px] font-sans text-neutral-700">
                      &ldquo;Raise material request for 500 units of Silicon Carbide Substrates for Apollo Q4 production run. Verify supplier compliance and route approvals.&rdquo;
                    </p>
                  </div>

                  {/* Trace Step 2: Tool Execution & Item Catalog Lookup */}
                  <div className="p-3 rounded-lg border border-neutral-200 bg-white">
                    <div className="flex items-center justify-between text-[11px] text-neutral-500 mb-1.5">
                      <span className="font-semibold text-neutral-800 flex items-center gap-1.5">
                        <PackageCheck className="w-3.5 h-3.5 text-blue-600" />
                        Tool: <code className="text-blue-700 font-mono">catalog.match_item</code>
                      </span>
                      <span className="text-emerald-600 font-semibold">✓ 2ms resolved</span>
                    </div>
                    <div className="text-[11px] text-neutral-600 flex items-center justify-between bg-neutral-50 p-2 rounded">
                      <span>Item: <strong className="text-neutral-900">ITM-SIC-001</strong> (Semi Grade SiC)</span>
                      <span>Std Price: <strong className="text-neutral-900">$9,700.00 / unit</strong></span>
                    </div>
                  </div>

                  {/* Trace Step 3: Risk Overlap & Chokepoint Detected */}
                  <div className="p-3 rounded-lg border border-rose-200 bg-rose-50/50">
                    <div className="flex items-center justify-between text-[11px] text-rose-800 mb-1.5">
                      <span className="font-bold flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                        Tool: <code className="text-rose-900 font-mono">risk.traverse_subtiers</code>
                      </span>
                      <span className="text-rose-700 font-bold px-1.5 py-0.2 rounded bg-rose-100 text-[10px]">
                        RESTRICTION DETECTED
                      </span>
                    </div>
                    <p className="text-[11px] text-neutral-700 font-sans leading-snug">
                      Preferred vendor <strong className="text-neutral-900">Apex Avionics AG</strong> sources silicon ingots from Tier-2 foundry <strong className="text-rose-900 font-bold">Shenzhen Micro Ingot</strong>, subject to newly enacted BIS Entity List export curbs.
                    </p>
                    <div className="text-[10px] text-neutral-500 mt-2 flex items-center justify-between border-t border-rose-200/60 pt-1.5">
                      <span>Citation: Federal Register Vol. 89 § 744</span>
                      <span className="text-rose-700 font-semibold">$4.85M Spend Exposed</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Trace Proposed Action */}
              <div className="mt-4 pt-3 border-t border-neutral-100 flex items-center justify-between text-xs">
                <span className="text-neutral-600 font-mono flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                  Auto-Routing: <strong className="text-neutral-900">VP &amp; CPO Approval</strong>
                </span>
                <span className="text-[11px] font-mono text-[#FA651E] font-bold">Alternate Sourced: Siltronic EU</span>
              </div>
            </div>

            {/* Right Column: Procurement Artifact & Risk Calculations */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              {/* Material Request Requisition Card */}
              <div className="bg-white p-4 rounded-lg border border-neutral-200/80 shadow-sm">
                <div className="flex items-center justify-between pb-2 mb-3 border-b border-neutral-100">
                  <span className="text-xs font-mono font-semibold text-neutral-700 uppercase flex items-center gap-1.5">
                    <ClipboardList className="w-3.5 h-3.5 text-[#FA651E]" />
                    Material Request MR-2024-089
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-bold">
                    PENDING APPROVAL
                  </span>
                </div>

                <div className="space-y-2 font-mono text-[11px]">
                  <div className="flex items-center justify-between p-2 rounded bg-neutral-50 border border-neutral-100">
                    <span className="text-neutral-500">Department</span>
                    <span className="text-neutral-900 font-medium">Advanced Propulsion</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-neutral-50 border border-neutral-100">
                    <span className="text-neutral-500">Requested Quantity</span>
                    <span className="text-neutral-900 font-medium">500 units @ $9,700</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-neutral-50 border border-neutral-100">
                    <span className="text-neutral-500">Estimated Total</span>
                    <span className="text-neutral-900 font-bold text-xs">$4,850,000.00</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between text-[11px]">
                  <span className="text-neutral-500">Approval Level:</span>
                  <span className="font-mono font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                    Delegation L3 ($1M+ Threshold)
                  </span>
                </div>
              </div>

              {/* Exposure & Multi-Tier Topology Card */}
              <div className="bg-white p-4 rounded-lg border border-neutral-200/80 shadow-sm">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-neutral-100">
                  <span className="text-xs font-mono font-semibold text-neutral-700 uppercase flex items-center gap-1.5">
                    <Network className="w-3.5 h-3.5 text-[#FA651E]" />
                    Deterministic Risk Score
                  </span>
                  <span className="text-xs font-mono font-bold text-rose-600">92 / 100 CRITICAL</span>
                </div>
                <div className="text-[11px] text-neutral-600 font-sans">
                  Deterministic Math: [Severity 0.95 × SpendTier 0.90 × SingleSource 1.0]. Sub-tier choke point flagged before physical order placement.
                </div>
                <div className="mt-3 pt-2 border-t border-neutral-100 flex items-center justify-between text-[10px] font-mono">
                  <span className="text-emerald-700 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    GLEIF Verified
                  </span>
                  <span className="text-neutral-400">Recursive CTE &lt; 85ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
