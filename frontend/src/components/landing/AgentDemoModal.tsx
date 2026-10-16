"use client";

import React, { useState, useEffect } from "react";
import { CornerMarks } from "./CornerMarks";
import { CheckCircle2, X, ArrowRight, ShieldCheck, Network, Database, Scale } from "lucide-react";
import Link from "next/link";

interface AgentDemoModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain: string;
}

export function AgentDemoModal({ isOpen, onClose, domain }: AgentDemoModalProps): React.ReactElement | null {
  const [step, setStep] = useState(1);
  const [progress, setProgress] = useState(15);
  const cleanDomain = domain.replace(/^https?:\/\//, "").replace(/\/.*$/, "") || "supplier-entity.com";

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setProgress(15);
      return;
    }

    const t1 = setTimeout(() => {
      setStep(2);
      setProgress(45);
    }, 1100);

    const t2 = setTimeout(() => {
      setStep(3);
      setProgress(78);
    }, 2300);

    const t3 = setTimeout(() => {
      setStep(4);
      setProgress(100);
    }, 3600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-white border border-neutral-200 shadow-2xl rounded-xl p-6 sm:p-8 text-neutral-900">
        <CornerMarks size={12} color="#FA651E" thickness={1.5} offset={-6} />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[#FA651E]/10 flex items-center justify-center text-[#FA651E]">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold tracking-tight text-neutral-950">
              Multi-Tier Exposure Scan
            </h3>
            <p className="text-xs text-neutral-500 font-mono mt-0.5">
              Target Entity: <span className="text-[#FA651E] font-semibold">{cleanDomain}</span>
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs font-mono text-neutral-500 mb-2">
            <span>TRAVERSING MULTI-TIER GRAPH &amp; REGISTERS</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 w-full bg-neutral-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#FA651E] to-[#FD8A6B] transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Interactive Steps Feedback */}
        <div className="space-y-3.5 mb-8">
          <div
            className={`flex items-start gap-3 p-3 rounded-lg border text-sm transition-all ${
              step >= 1
                ? "bg-orange-50/50 border-[#FA651E]/20 text-neutral-900"
                : "bg-neutral-50 border-neutral-100 text-neutral-400"
            }`}
          >
            <Database
              className={`w-4 h-4 mt-0.5 shrink-0 ${
                step >= 1 ? "text-[#FA651E]" : "text-neutral-400"
              }`}
            />
            <div className="flex-1">
              <div className="font-semibold text-xs tracking-wider uppercase">
                1. GLEIF LEI Registry Resolution
              </div>
              <p className="text-xs text-neutral-600 mt-0.5">
                Matched canonical LEI: <span className="font-mono text-neutral-800">549300...</span> · Verified ultimate parent corporation.
              </p>
            </div>
            {step >= 1 && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          </div>

          <div
            className={`flex items-start gap-3 p-3 rounded-lg border text-sm transition-all ${
              step >= 2
                ? "bg-orange-50/50 border-[#FA651E]/20 text-neutral-900"
                : "bg-neutral-50 border-neutral-100 text-neutral-400"
            }`}
          >
            <Network
              className={`w-4 h-4 mt-0.5 shrink-0 ${
                step >= 2 ? "text-[#FA651E]" : "text-neutral-400"
              }`}
            />
            <div className="flex-1">
              <div className="font-semibold text-xs tracking-wider uppercase">
                2. Sub-Tier Dependency Mapping
              </div>
              <p className="text-xs text-neutral-600 mt-0.5">
                Traversed 14 sub-tier foundry nodes · Identified 1 single-source raw mineral choke point.
              </p>
            </div>
            {step >= 2 && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          </div>

          <div
            className={`flex items-start gap-3 p-3 rounded-lg border text-sm transition-all ${
              step >= 3
                ? "bg-orange-50/50 border-[#FA651E]/20 text-neutral-900"
                : "bg-neutral-50 border-neutral-100 text-neutral-400"
            }`}
          >
            <ShieldCheck
              className={`w-4 h-4 mt-0.5 shrink-0 ${
                step >= 3 ? "text-[#FA651E]" : "text-neutral-400"
              }`}
            />
            <div className="flex-1">
              <div className="font-semibold text-xs tracking-wider uppercase">
                3. Global Sanctions &amp; Trade Controls Check
              </div>
              <p className="text-xs text-neutral-600 mt-0.5">
                Cross-referenced OFAC SDN, BIS Entity List, EU Sanctions Map · 0 direct sanctions, 1 sub-tier trade curb.
              </p>
            </div>
            {step >= 3 && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          </div>

          <div
            className={`flex items-start gap-3 p-3 rounded-lg border text-sm transition-all ${
              step >= 4
                ? "bg-orange-50/50 border-[#FA651E]/20 text-neutral-900"
                : "bg-neutral-50 border-neutral-100 text-neutral-400"
            }`}
          >
            <Scale
              className={`w-4 h-4 mt-0.5 shrink-0 ${
                step >= 4 ? "text-[#FA651E]" : "text-neutral-400"
              }`}
            />
            <div className="flex-1">
              <div className="font-semibold text-xs tracking-wider uppercase">
                4. Deterministic Exposure Scoring
              </div>
              <p className="text-xs text-neutral-600 mt-0.5">
                Computed Risk Score: <span className="font-bold text-[#FA651E]">78/100 (HIGH EXPOSURE)</span> · Verifiable citations ready.
              </p>
            </div>
            {step >= 4 && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-neutral-100">
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-2 text-xs font-semibold text-neutral-600 hover:text-neutral-900 transition-colors"
          >
            Close Scan
          </button>

          <Link
            href="/dashboard"
            className="w-full sm:w-auto px-6 py-2.5 bg-[#0A0A0A] hover:bg-neutral-800 text-white rounded-lg text-xs font-semibold tracking-tight transition-all flex items-center justify-center gap-2 group shadow-sm"
          >
            <span>Open Provenance Terminal</span>
            <ArrowRight className="w-3.5 h-3.5 text-[#FD8A6B] group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  );
}
