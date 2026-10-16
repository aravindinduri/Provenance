"use client";

import React from "react";
import { CornerMarks } from "./CornerMarks";
import { ShieldCheck } from "lucide-react";

export function MetricsAndTestimonials(): React.ReactElement {
  const metrics = [
    {
      value: "100%",
      sub: "Deterministic & auditable risk calculations (0% math hallucinations)",
    },
    {
      value: "85% Faster",
      sub: "Requisition-to-approval cycle times with Agent Trace copilot",
    },
    {
      value: "$14.8M",
      sub: "Average disruption and maverick spend protected per 1,000 suppliers",
    },
  ];

  const testimonials = [
    {
      name: "Marcus Vance",
      role: "Global Head of Supply Chain Risk",
      company: "Aerospace Systems Corp",
      initials: "MV",
      badgeColor: "bg-blue-100 text-blue-800",
      quote:
        "Provenance detected graphite export curbs 11 days before our primary broker alerted us. Our team pre-qualified an alternate supplier in Europe through Agent Trace before spot prices surged 40%.",
    },
    {
      name: "Elena Rostova",
      role: "VP of Strategic Direct Procurement",
      company: "Global Automotive Electrics",
      initials: "ER",
      badgeColor: "bg-orange-100 text-[#9A3412]",
      quote:
        "The multi-tier graph revealed that 4 of our Tier-1 wiring harness vendors were relying on the same sanctioned copper smelter. We eliminated a catastrophic single-point-of-failure in one afternoon.",
    },
    {
      name: "David Chen",
      role: "Chief Compliance & Trade Officer",
      company: "Industrial Robotics Group",
      initials: "DC",
      badgeColor: "bg-emerald-100 text-emerald-800",
      quote:
        "Every approval packet comes with exact Federal Register legal citations and PO lines. Zero hallucinated AI summaries. Our general counsel accepts Provenance reports directly for export filings.",
    },
    {
      name: "Sarah Al-Mansoor",
      role: "Category Director, Critical Materials",
      company: "Renewable Energy Grid Solutions",
      initials: "SA",
      badgeColor: "bg-purple-100 text-purple-800",
      quote:
        "Agent Trace cut our requisition drafting and quote comparisons from days to minutes, while Delegation of Authority rules prevent maverick spending effortlessly. It is indispensable.",
    },
  ];

  return (
    <section id="case-studies" className="py-24 bg-[#FAF9F6] border-b border-neutral-200/60 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Headline with Registration Frame */}
        <div data-reveal className="relative max-w-4xl mb-16 p-6 sm:p-8 bg-white/40 rounded-xl border border-neutral-200/60">
          <CornerMarks size={8} color="#c7c7c7" thickness={1} offset={-4} />

          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FA651E]" />
            <span className="text-xs font-mono uppercase tracking-wider text-neutral-500 font-semibold">
              Enterprise Impact
            </span>
          </div>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#0A0A0A] leading-[1.12]">
            Procurement teams stop chasing late shipments.{" "}
            <span className="text-[#FA651E]">Provenance coordinates action first</span>.
          </h2>
        </div>

        {/* 3 Metric Stats with Scroll Stagger */}
        <div data-reveal-stagger className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20 text-center">
          {metrics.map((m) => (
            <div
              key={m.value}
              data-reveal-item
              className="relative p-8 bg-white rounded-xl border border-neutral-200 shadow-sm flex flex-col items-center justify-center hover:border-orange-200 transition-all"
            >
              <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />
              <div className="text-5xl sm:text-6xl font-extrabold tracking-tight text-[#0A0A0A] mb-3">
                {m.value}
              </div>
              <p className="text-sm sm:text-base text-neutral-600 font-medium max-w-xs">
                {m.sub}
              </p>
            </div>
          ))}
        </div>

        {/* Testimonials Grid with Scroll Stagger */}
        <div data-reveal-stagger className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {testimonials.map((t) => (
            <div
              key={t.name}
              data-reveal-item
              className="relative bg-white rounded-xl border border-neutral-200 p-6 shadow-sm flex flex-col justify-between hover:shadow-md hover:border-orange-200 transition-all group"
            >
              <CornerMarks size={8} color="#d4d4d4" thickness={1} offset={-4} />

              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={`w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm tracking-tight shrink-0 border border-neutral-200 ${t.badgeColor}`}
                  >
                    {t.initials}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-neutral-900 leading-tight">
                      {t.name}
                    </h4>
                    <p className="text-xs text-neutral-500 line-clamp-1">{t.role}</p>
                    <p className="text-[10px] font-mono text-[#FA651E]">{t.company}</p>
                  </div>
                </div>

                <p className="text-xs sm:text-sm text-neutral-600 leading-relaxed italic">
                  &ldquo;{t.quote}&rdquo;
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-neutral-100 flex items-center justify-between text-[11px] font-mono text-neutral-400">
                <span className="flex items-center gap-1 text-emerald-700">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Verified Enterprise User
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
