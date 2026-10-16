"use client";

import React, { useState } from "react";
import { CornerMarks } from "./CornerMarks";
import { ProvenanceLogo } from "./ProvenanceLogo";

export function VennSection(): React.ReactElement {
  const [activeCircle, setActiveCircle] = useState<string | null>(null);

  return (
    <section className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div data-reveal className="relative max-w-4xl mb-16 p-4 sm:p-6 bg-white/40 rounded-xl border border-neutral-200/60">
          <CornerMarks size={8} color="#c7c7c7" thickness={1} offset={-4} />

          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E]" />
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-500 font-semibold">
              Consolidated Architecture
            </span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0A0A0A] leading-tight mb-4">
            One platform. Replaces your <span className="text-[#FA651E]">fragmented procurement &amp; risk stack</span>.
          </h2>

          <p className="text-base sm:text-lg text-neutral-600 font-normal">
            Legacy ERPs are blind to external shocks, news monitors have no BOM or purchase order context, spreadsheets rot, and generic AI chatbots hallucinate numbers. Provenance unifies them into an agentic, deterministic command center.
          </p>
        </div>

        {/* 4-Circle Venn Diagram Container */}
        <div
          data-reveal
          className="relative max-w-4xl mx-auto bg-white rounded-2xl border border-neutral-200 p-8 sm:p-14 shadow-sm"
        >
          <CornerMarks size={12} color="#FA651E" thickness={1.5} offset={-6} />

          <div className="relative w-full aspect-square max-w-[580px] mx-auto flex items-center justify-center">
            {/* SVG Background Coordinate Grid */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none opacity-20"
              viewBox="0 0 500 500"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle cx="250" cy="250" r="240" stroke="#000" strokeWidth="0.5" strokeDasharray="2 4" />
              <line x1="250" y1="0" x2="250" y2="500" stroke="#000" strokeWidth="0.5" strokeDasharray="3 3" />
              <line x1="0" y1="250" x2="500" y2="250" stroke="#000" strokeWidth="0.5" strokeDasharray="3 3" />
            </svg>

            {/* Circle 1: Top-Left (Legacy ERP / S2P) */}
            <div
              onMouseEnter={() => setActiveCircle("erp")}
              onMouseLeave={() => setActiveCircle(null)}
              className={`absolute top-6 left-6 w-[270px] sm:w-[310px] h-[270px] sm:h-[310px] rounded-full border border-neutral-400/80 transition-all duration-300 flex flex-col items-center justify-center p-6 ${activeCircle === "erp" ? "bg-orange-500/10 border-[#FA651E] scale-102" : "bg-neutral-50/20"
                }`}
            >
              <div className="absolute top-10 left-8 text-left">
                <span className="text-sm sm:text-base font-bold text-[#FA651E] tracking-tight block">
                  Legacy ERP &amp; S2P
                </span>
                <span className="text-[10px] font-mono text-neutral-400">Internal transactional data only</span>
                <div className="mt-2 space-y-1.5 text-xs text-neutral-700 font-semibold">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-900" />
                    <span>SAP S/4HANA &amp; Ariba</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" />
                    <span>Coupa Procurement</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Circle 2: Top-Right (External News Feeds) */}
            <div
              onMouseEnter={() => setActiveCircle("news")}
              onMouseLeave={() => setActiveCircle(null)}
              className={`absolute top-6 right-6 w-[270px] sm:w-[310px] h-[270px] sm:h-[310px] rounded-full border border-neutral-400/80 transition-all duration-300 flex flex-col items-center justify-center p-6 ${activeCircle === "news" ? "bg-orange-500/10 border-[#FA651E] scale-102" : "bg-neutral-50/20"
                }`}
            >
              <div className="absolute top-10 right-8 text-right">
                <span className="text-sm sm:text-base font-bold text-neutral-900 tracking-tight block">
                  Isolated Threat Feeds
                </span>
                <span className="text-[10px] font-mono text-neutral-400">No BOM or purchase order context</span>
                <div className="mt-2 space-y-1.5 text-xs text-neutral-700 font-semibold flex flex-col items-end">
                  <div className="flex items-center gap-1.5">
                    <span>Google Alerts &amp; News</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span>World-Check Sanctions</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-800" />
                  </div>
                </div>
              </div>
            </div>

            {/* Circle 3: Bottom-Left (Manual Spreadsheets) */}
            <div
              onMouseEnter={() => setActiveCircle("sheets")}
              onMouseLeave={() => setActiveCircle(null)}
              className={`absolute bottom-6 left-6 w-[270px] sm:w-[310px] h-[270px] sm:h-[310px] rounded-full border border-neutral-400/80 transition-all duration-300 flex flex-col items-center justify-center p-6 ${activeCircle === "sheets" ? "bg-orange-500/10 border-[#FA651E] scale-102" : "bg-neutral-50/20"
                }`}
            >
              <div className="absolute bottom-10 left-8 text-left">
                <span className="text-sm sm:text-base font-bold text-neutral-900 tracking-tight block">
                  Manual Spreadsheets &amp; Email
                </span>
                <span className="text-[10px] font-mono text-neutral-400">Stale records, slow approvals</span>
                <div className="mt-2 space-y-1.5 text-xs text-neutral-700 font-semibold">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-700" />
                    <span>Excel Supplier Lists</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
                    <span>Ad-hoc Email Approvals</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Circle 4: Bottom-Right (Generic AI Chatbots) */}
            <div
              onMouseEnter={() => setActiveCircle("ai")}
              onMouseLeave={() => setActiveCircle(null)}
              className={`absolute bottom-6 right-6 w-[270px] sm:w-[310px] h-[270px] sm:h-[310px] rounded-full border border-neutral-400/80 transition-all duration-300 flex flex-col items-center justify-center p-6 ${activeCircle === "ai" ? "bg-orange-500/10 border-[#FA651E] scale-102" : "bg-neutral-50/20"
                }`}
            >
              <div className="absolute bottom-10 right-8 text-right">
                <span className="text-sm sm:text-base font-bold text-[#FA651E] tracking-tight block">
                  Generic AI Chatbots
                </span>
                <span className="text-[10px] font-mono text-neutral-400">Ungrounded, fabricated numbers</span>
                <div className="mt-2 space-y-1.5 text-xs text-neutral-700 font-semibold flex flex-col items-end">
                  <div className="flex items-center gap-1.5">
                    <span>Ungrounded LLM Wrappers</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span>No Workflow Integration</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" />
                  </div>
                </div>
              </div>
            </div>

            {/* Center: Provenance Unified Solution */}
            <div className="relative z-20 w-44 h-44 sm:w-48 sm:h-48 rounded-full bg-white border-2 border-[#FA651E] shadow-[0_10px_35px_rgba(250,101,30,0.15)] flex flex-col items-center justify-center p-4 text-center group hover:scale-105 transition-transform duration-300">
              <CornerMarks size={8} color="#FA651E" thickness={1.2} offset={-4} />

              <div className="mb-1.5 scale-90">
                <ProvenanceLogo size="sm" inverted={false} />
              </div>

              <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#FA651E]/10 text-[#FA651E] text-[10px] font-mono font-bold">
                <span>Unified S2P Core</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
