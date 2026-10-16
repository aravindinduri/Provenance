"use client";

import React from "react";
import { CornerMarks } from "./CornerMarks";
import { ProvenanceLogo } from "./ProvenanceLogo";

export function IntegrationsSection(): React.ReactElement {
  const tools = [
    {
      name: "SAP S/4HANA",
      tag: "ERP & ITEMS",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#0070F2]/10 text-[#0070F2] flex items-center justify-center font-bold text-xs">
          SAP
        </div>
      ),
    },
    {
      name: "Coupa",
      tag: "P2P SUITE",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center font-black text-xs">
          CP
        </div>
      ),
    },
    {
      name: "NetSuite",
      tag: "ERP & POs",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#0284C7]/10 text-[#0284C7] flex items-center justify-center font-bold text-xs">
          NS
        </div>
      ),
    },
    {
      name: "GLEIF LEI",
      tag: "ENTITY REGISTRY",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#059669]/10 text-[#059669] flex items-center justify-center font-bold text-xs">
          LEI
        </div>
      ),
    },
    {
      name: "OFAC & BIS",
      tag: "SANCTIONS REGISTERS",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#DC2626]/10 text-[#DC2626] flex items-center justify-center font-black text-xs">
          SDN
        </div>
      ),
    },
    {
      name: "Federal Register",
      tag: "LEGAL GAZETTES",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#D97706]/10 text-[#D97706] flex items-center justify-center font-black text-xs">
          FR
        </div>
      ),
    },
    {
      name: "Slack & Teams",
      tag: "APPROVAL ALERTS",
      icon: (
        <div className="w-8 h-8 rounded-md bg-[#4A154B]/10 text-[#4A154B] flex items-center justify-center font-bold text-xs">
          #
        </div>
      ),
    },
  ];

  return (
    <section id="integrations" className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Section Header */}
        <div data-reveal className="max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#0A0A0A] mb-4">
            Synchronizes with your enterprise <br className="hidden sm:inline" />
            <span className="text-[#FA651E]">ERP, P2P suites, and official registers</span>.
          </h2>
          <p className="text-base text-neutral-600">
            Bi-directional connectors for catalog sync, PO creation, approval dispatch, and multi-tier sanctions resolution.
          </p>
        </div>

        {/* Tree Connection Graph Visual */}
        <div data-reveal className="relative max-w-4xl mx-auto py-8">
          {/* Top Provenance Hub Node */}
          <div className="relative mx-auto w-28 h-28 rounded-2xl bg-white border border-neutral-200 shadow-md flex items-center justify-center mb-16 group hover:scale-105 transition-transform p-3">
            <CornerMarks size={8} color="#FA651E" thickness={1.2} offset={-4} />
            <ProvenanceLogo size="sm" inverted={false} />
          </div>

          {/* Radiating Curved SVG Connectors in signature orange */}
          <svg
            className="absolute top-24 left-0 w-full h-28 pointer-events-none -z-10 hidden sm:block"
            viewBox="0 0 800 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M400,0 C400,50 60,60 60,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.35" />
            <path d="M400,0 C400,50 170,60 170,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.4" />
            <path d="M400,0 C400,50 285,60 285,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.5" />
            <path d="M400,0 L400,110" stroke="#FA651E" strokeWidth="1.5" opacity="0.6" />
            <path d="M400,0 C400,50 515,60 515,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.5" />
            <path d="M400,0 C400,50 630,60 630,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.4" />
            <path d="M400,0 C400,50 740,60 740,110" stroke="#FA651E" strokeWidth="1.2" opacity="0.35" />
          </svg>

          {/* 7 Connected Tool Cards with Stagger */}
          <div data-reveal-stagger className="grid grid-cols-2 sm:grid-cols-7 gap-4">
            {tools.map((t) => (
              <div
                key={t.name}
                data-reveal-item
                className="relative bg-white rounded-xl border border-neutral-200 p-4 shadow-sm flex flex-col items-center justify-center text-center hover:border-orange-300 hover:shadow-md transition-all group"
              >
                <CornerMarks size={6} color="#d4d4d4" thickness={1} offset={-3} />
                <div className="mb-2.5">{t.icon}</div>
                <span className="text-xs font-bold text-neutral-900 tracking-tight group-hover:text-[#FA651E] transition-colors">
                  {t.name}
                </span>
                <span className="text-[9px] font-mono text-neutral-400 mt-0.5">
                  {t.tag}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
