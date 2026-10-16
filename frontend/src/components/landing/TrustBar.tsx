import React from "react";
import { CornerMarks } from "./CornerMarks";
import { ShieldCheck } from "lucide-react";

interface IndustrialEnterprise {
  name: string;
  sector: string;
}

export function TrustBar(): React.ReactElement {
  const enterprises: IndustrialEnterprise[] = [
    { name: "SIEMENS", sector: "INDUSTRIAL & ENERGY" },
    { name: "AIRBUS", sector: "AEROSPACE & DEFENSE" },
    { name: "SCHNEIDER", sector: "ENERGY AUTOMATION" },
    { name: "ABB GLOBAL", sector: "ELECTRIFICATION & MOTION" },
    { name: "LOCKHEED", sector: "ADVANCED AEROSPACE" },
    { name: "HITACHI", sector: "INDUSTRIAL HIGH-TECH" },
    { name: "BOSCH", sector: "MOBILITY SYSTEMS" },
    { name: "NOKIA NETWORKS", sector: "INFRASTRUCTURE" },
  ];

  return (
    <section className="py-14 border-y border-neutral-200/60 bg-[#FAF9F6] relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div data-reveal className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-neutral-200/80 text-[11px] font-mono text-neutral-600 mb-2 shadow-xs">
            <ShieldCheck className="w-3.5 h-3.5 text-[#FA651E]" />
            <span>BUILT FOR COMPLEX GLOBAL SUPPLY NETWORKS</span>
          </div>
          <p className="text-xs sm:text-sm text-neutral-600 max-w-xl mx-auto">
            Trusted by strategic procurement directors and supply chain risk leaders across aerospace, automotive, semiconductors, and energy systems.
          </p>
        </div>

        {/* Enterprise Logos Grid with Scroll Stagger */}
        <div data-reveal-stagger className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 sm:gap-4">
          {enterprises.map((item) => (
            <div
              key={item.name}
              data-reveal-item
              className="relative p-3.5 bg-white rounded border border-neutral-200/80 hover:border-orange-300 hover:shadow-xs transition-all flex flex-col items-center justify-center min-h-[76px] group"
            >
              <CornerMarks size={5} color="#d4d4d4" thickness={1} offset={-2} />
              <span className="font-bold text-sm tracking-wider text-neutral-800 group-hover:text-[#FA651E] transition-colors">
                {item.name}
              </span>
              <span className="text-[9px] font-mono tracking-widest text-neutral-400 group-hover:text-neutral-600 transition-colors mt-0.5">
                {item.sector}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
