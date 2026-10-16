"use client";

import React, { useState } from "react";
import { CornerMarks } from "./CornerMarks";
import { Search, ArrowRight, Sparkles } from "lucide-react";

interface FinalCTASectionProps {
  onLaunchDemo: (domain: string) => void;
}

export function FinalCTASection({ onLaunchDemo }: FinalCTASectionProps): React.ReactElement {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) {
      setError("Please enter a supplier name or domain (e.g. tsmc.com, basf.com)");
      return;
    }
    setError("");
    onLaunchDemo(url.trim());
  };

  return (
    <section id="demo" className="py-24 bg-[#FAF9F6] relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          data-reveal
          className="relative rounded-3xl bg-white border border-neutral-200/80 p-8 sm:p-16 lg:p-20 shadow-[0_16px_50px_rgba(250,101,30,0.06)] overflow-hidden text-center"
        >
          <CornerMarks size={12} color="#FA651E" thickness={1.5} offset={-6} />

          {/* Warm Ambient Radial Glow with Parallax Float */}
          <div
            data-parallax-float
            data-parallax-speed="0.2"
            className="pointer-events-none absolute inset-0 opacity-70"
            style={{
              background:
                "radial-gradient(ellipse at 50% 20%, rgba(253, 138, 107, 0.3) 0%, rgba(250, 101, 30, 0.08) 50%, transparent 80%)",
            }}
            aria-hidden="true"
          />

          {/* Decorative Corner Guides */}
          <svg
            className="pointer-events-none absolute inset-0 w-full h-full opacity-30"
            viewBox="0 0 1000 400"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path d="M-50,50 Q180,180 280,320" stroke="#FA651E" strokeWidth="1.5" />
            <path d="M1050,50 Q820,180 720,320" stroke="#FA651E" strokeWidth="1.5" />
          </svg>

          <div className="relative z-10 max-w-3xl mx-auto">
            {/* Status Chip */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-50 border border-orange-200 text-[#FA651E] text-xs font-mono font-semibold mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AGENTIC PROCUREMENT &amp; RISK COMMAND CENTER</span>
            </div>

            {/* Headline */}
            <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#0A0A0A] leading-tight mb-4">
              Unify your procurement workflow <br className="hidden sm:inline" />
              before the <span className="text-[#FA651E]">next global shock</span>.
            </h2>

            {/* Subhead */}
            <p className="text-base sm:text-lg text-neutral-600 mb-10 font-normal">
              Enter any supplier, part code, or domain to simulate multi-tier exposure, identify single-source choke points, and test Agent Trace autonomous orchestration.
            </p>

            {/* Interactive Domain Input */}
            <div className="max-w-xl mx-auto mb-6">
              <form
                onSubmit={handleSubmit}
                className="relative p-1.5 bg-white rounded-xl border border-neutral-300 shadow-md flex flex-col sm:flex-row items-center gap-2"
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
                    placeholder="Enter supplier domain or part name (e.g. tsmc.com, basf.com)"
                    className="w-full bg-transparent text-sm sm:text-base text-neutral-900 placeholder-neutral-400 focus:outline-none"
                    aria-label="Enter supplier name or domain"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full sm:w-auto px-6 py-3 bg-[#0A0A0A] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold tracking-tight rounded-lg transition-all flex items-center justify-center gap-2 shrink-0 group shadow-md"
                >
                  <Sparkles className="w-4 h-4 text-[#FD8A6B]" />
                  <span>Analyze Platform Risk</span>
                  <ArrowRight className="w-4 h-4 text-[#FD8A6B] group-hover:translate-x-0.5 transition-transform" />
                </button>
              </form>

              {error && (
                <p className="text-xs text-rose-600 mt-2 font-medium text-left px-2">
                  {error}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
