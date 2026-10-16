"use client";

import React, { useState } from "react";
import { CornerMarks } from "./CornerMarks";
import {
  Network,
  Scale,
  Sparkles,
  ClipboardList,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  TrendingUp,
} from "lucide-react";

export function OutreachBentoGrid(): React.ReactElement {
  const [highAlertMode, setHighAlertMode] = useState(false);

  return (
    <section id="engine" className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div data-reveal className="relative max-w-4xl mb-16 p-4 sm:p-6 bg-white/40 rounded-xl border border-neutral-200/60">
          <CornerMarks size={8} color="#c7c7c7" thickness={1} offset={-4} />

          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E]" />
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-500 font-semibold">
              Mission-Critical Capabilities
            </span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0A0A0A] leading-tight mb-4">
            Agentic intelligence with <span className="text-[#FA651E]">zero math hallucinations</span>.
          </h2>

          <p className="text-base sm:text-lg text-neutral-600 font-normal">
            Where other AI platforms hallucinate prices and fabricate vendor relationships, Provenance separates deterministic computation from generative agentic orchestration.
          </p>
        </div>

        {/* Bento Grid with Scroll Stagger */}
        <div data-reveal-stagger className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: AGENT TRACE ORCHESTRATOR */}
          <div
            data-reveal-item
            className="relative bg-white rounded-xl border border-neutral-200 p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-orange-200 transition-all group"
          >
            <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />
            <div>
              <div className="inline-flex items-center gap-2 mb-4 text-xs font-mono font-bold tracking-wider text-neutral-400 uppercase">
                <Sparkles className="w-3.5 h-3.5 text-[#FA651E]" />
                <span>AGENTIC COPILOT</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                Agent Trace: Autonomous Sourcing &amp; Analysis
              </h3>
              <p className="text-sm text-neutral-600 leading-relaxed">
                Interact with your procurement data in plain language. Draft material requests, interrogate supplier risk postures, compare RFx quotes, and trigger multi-level approvals through conversational commands.
              </p>
            </div>

            <div className="mt-8 p-3 rounded-lg bg-neutral-50 border border-neutral-100 flex items-center justify-between text-xs font-mono text-neutral-600">
              <span className="text-neutral-500">&ldquo;Draft MR for SiC substrates&rdquo;</span>
              <span className="text-[#FA651E] font-bold">Auto-Routed</span>
            </div>
          </div>

          {/* Card 2: DETERMINISTIC VS AI (Large middle card) */}
          <div
            data-reveal-item
            className="relative bg-white rounded-xl border border-neutral-200 p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-orange-200 transition-all group md:col-span-2"
          >
            <CornerMarks size={8} color="#FA651E" thickness={1.2} offset={-4} />
            <div>
              <div className="inline-flex items-center gap-2 mb-4 text-xs font-mono font-bold tracking-wider text-neutral-400 uppercase">
                <Scale className="w-3.5 h-3.5 text-[#FA651E]" />
                <span>ARCHITECTURAL SEPARATION</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                Deterministic Math Engine vs. LLM Natural Language
              </h3>
              <p className="text-sm text-neutral-600 leading-relaxed max-w-xl">
                The default is deterministic. Large Language Models are strictly used for unstructured legal gazette extraction, document parsing, and natural language communication. All dollar exposure figures, price variances, and risk scores are computed by auditable Python formulas and PostgreSQL CTEs.
              </p>
            </div>

            {/* Architectural Badges in Reference Warm Palette */}
            <div className="mt-8 flex flex-wrap items-center gap-2.5">
              <span className="px-3 py-1.5 rounded-full bg-[#FEF08A] text-[#854D0E] text-xs font-semibold shadow-xs">
                Auditable SQL Scoring
              </span>
              <span className="px-3 py-1.5 rounded-full bg-[#FD8A6B]/25 text-[#9A3412] text-xs font-semibold shadow-xs">
                Zero Math Hallucination
              </span>
              <span className="px-3 py-1.5 rounded-full bg-[#A7F3D0] text-[#065F46] text-xs font-semibold shadow-xs">
                Grounded Legal Citations
              </span>
              <span className="px-3 py-1.5 rounded-full bg-[#FDE047]/60 text-[#713F12] text-xs font-semibold shadow-xs">
                Delegation Governance
              </span>
            </div>
          </div>

          {/* Card 3: MATERIAL MASTER & REQUISITION LIFECYCLE */}
          <div
            data-reveal-item
            className="relative bg-white rounded-xl border border-neutral-200 p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-orange-200 transition-all group"
          >
            <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />
            <div>
              <div className="inline-flex items-center gap-2 mb-4 text-xs font-mono font-bold tracking-wider text-neutral-400 uppercase">
                <ClipboardList className="w-3.5 h-3.5 text-[#FA651E]" />
                <span>TRANSACTIONAL P2P</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                Material Master &amp; Requisition Engine
              </h3>
              <p className="text-sm text-neutral-600 leading-relaxed">
                Standardize items with UNSPSC classification, default unit prices, preferred vendors, and lead-time tracking. Manage purchase requests through approval, ordering, and receipt.
              </p>
            </div>

            <div className="mt-8 p-3 rounded-lg bg-neutral-50 border border-neutral-100 flex items-center justify-between text-xs font-mono text-neutral-600">
              <span>Catalog Harmonization</span>
              <span className="text-emerald-700 font-bold">Standardized</span>
            </div>
          </div>

          {/* Card 4: MULTI-TIER GRAPH TOPOLOGY */}
          <div
            data-reveal-item
            className="relative bg-white rounded-xl border border-neutral-200 p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-orange-200 transition-all group"
          >
            <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />
            <div>
              <div className="inline-flex items-center gap-2 mb-4 text-xs font-mono font-bold tracking-wider text-neutral-400 uppercase">
                <Network className="w-3.5 h-3.5 text-[#FA651E]" />
                <span>TOPOLOGY</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                Recursive Multi-Tier Graph Traversal
              </h3>
              <p className="text-sm text-neutral-600 leading-relaxed">
                Traverse up to 5 tiers deep in sub-100ms via recursive SQL CTEs. Uncovers hidden single-source choke points where multiple Tier-1 vendors source from the same sanctioned smelter or sub-contractor.
              </p>
            </div>

            <div className="mt-8 p-3 rounded-lg bg-neutral-50 border border-neutral-100 flex items-center justify-between text-xs font-mono text-neutral-600">
              <span>Tier 1 → 5 Recursion</span>
              <span className="text-emerald-700 font-bold">&lt; 100ms</span>
            </div>
          </div>

          {/* Card 5: DELEGATION OF AUTHORITY & APPROVAL GUARDRAILS */}
          <div
            data-reveal-item
            className="relative bg-white rounded-xl border border-neutral-200 p-6 sm:p-8 shadow-sm flex flex-col justify-between hover:border-orange-200 transition-all group"
          >
            <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />
            <div>
              <div className="inline-flex items-center gap-2 mb-4 text-xs font-mono font-bold tracking-wider text-neutral-400 uppercase">
                <ShieldCheck className="w-3.5 h-3.5 text-[#FA651E]" />
                <span>GOVERNANCE</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0A0A0A] mb-3">
                Delegation of Authority &amp; Push Routing
              </h3>
              <p className="text-sm text-neutral-600 leading-relaxed">
                Enforces spending authority boundaries automatically. Multi-level sign-offs route to managers, category heads, or CPOs depending on total value, risk overlap, and budget variances.
              </p>
            </div>

            {/* Interactive Toggle */}
            <div className="mt-8 p-4 rounded-lg bg-neutral-50 border border-neutral-100 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono font-bold text-neutral-900 block">
                  {highAlertMode ? "STRICT GOVERNANCE (L3 ESCALATION)" : "DELEGATED THRESHOLDS (STANDARD)"}
                </span>
                <span className="text-[10px] text-neutral-500">
                  {highAlertMode ? "Mandatory CPO sign-off on any Tier-2 risk flag" : "Auto-route based on spend bands"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setHighAlertMode(!highAlertMode)}
                className="text-neutral-400 hover:text-neutral-900 focus:outline-none"
                aria-label="Toggle governance sensitivity"
              >
                {highAlertMode ? (
                  <ToggleRight className="w-8 h-8 text-[#FA651E]" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-neutral-400" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
