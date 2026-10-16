"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  Award,
  CheckCircle2,
  AlertCircle,
  Clock,
  DollarSign,
  TrendingUp,
  Building2,
  Calendar,
  Check,
  Loader2,
  ArrowLeft,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

export interface BidComparisonItem {
  response_id: string;
  response_number: string;
  supplier_id: string;
  supplier_name: string;
  supplier_country?: string | null;
  total_amount: number;
  currency: string;
  average_lead_time_days?: number | null;
  line_items: { item: string; qty: number; unit_price: number; lead_time_days?: number }[];
  criteria_scores: Record<string, number>;
  normalized_price_score: number;
  composite_score: number;
  is_best_offer: boolean;
  price_rank: number;
  overall_rank: number;
  payment_terms?: string | null;
  delivery_terms?: string | null;
}

export interface BidComparisonData {
  rfx_id: string;
  rfx_number: string;
  rfx_type: string;
  title: string;
  status: string;
  criteria: { criterion: string; weight: number; description?: string }[];
  bids: BidComparisonItem[];
  recommended_response_id?: string | null;
  recommended_supplier_id?: string | null;
  recommended_supplier_name?: string | null;
  recommendation_summary?: string | null;
}

interface BidComparisonTableProps {
  data: BidComparisonData;
  onAwardSuccess: () => void;
}

export function BidComparisonTable({ data, onAwardSuccess }: BidComparisonTableProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [isAwarding, setIsAwarding] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAward = async (responseId: string, supplierName: string) => {
    if (
      !confirm(
        `Are you sure you want to award this contract to ${supplierName}? This will advance the sourcing event to Awarded.`
      )
    ) {
      return;
    }

    setIsAwarding(responseId);
    setErrorMessage(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/rfx/${data.rfx_id}/award`, {
        method: "POST",
        headers,
        body: JSON.stringify({ response_id: responseId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to award RFx event");
      }

      onAwardSuccess();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Error awarding contract");
    } finally {
      setIsAwarding(null);
    }
  };

  if (!data.bids || data.bids.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-200/80 bg-white p-12 text-center shadow-xs">
        <BarChart3 className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
        <h3 className="text-base font-bold text-neutral-900">No Quotations to Compare</h3>
        <p className="text-xs text-neutral-500 max-w-md mx-auto mt-1">
          No supplier quotes have been registered yet for {data.rfx_number}. Once vendors submit bids, the deterministic comparison matrix will automatically rank them.
        </p>
        <Link href={`/rfx/${data.rfx_id}`} className="inline-block mt-4">
          <Button size="sm" variant="outline" className="text-xs h-8">
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            Back to Event
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Recommendation Banner */}
      {data.recommendation_summary && (
        <div className="rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50/90 via-indigo-50/70 to-white p-4 shadow-xs">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-purple-100 text-purple-700 mt-0.5">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-700">
                  Algorithmic Best-Value Recommendation
                </span>
                <span className="px-2 py-0.2 rounded-full text-[10px] bg-purple-100 text-purple-800 font-semibold">
                  Deterministic Scoring
                </span>
              </div>
              <p className="text-xs text-neutral-800 mt-1 font-medium leading-relaxed">
                {data.recommendation_summary}
              </p>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-neutral-500">
                <span>Criteria Weights:</span>
                {data.criteria.map((c, i) => (
                  <span key={i} className="bg-white/80 px-1.5 py-0.5 rounded border border-neutral-200">
                    {c.criterion}: <strong>{c.weight}%</strong>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Side-by-Side Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.bids.map((bid) => {
          const isWinner = data.status === "awarded" && bid.is_best_offer;
          const isRecommended = bid.is_best_offer && data.status !== "awarded";

          return (
            <div
              key={bid.response_id}
              className={cn(
                "rounded-xl border transition-all p-5 shadow-xs flex flex-col justify-between relative",
                isWinner
                  ? "border-emerald-300 bg-gradient-to-b from-emerald-50/40 to-white ring-2 ring-emerald-400"
                  : isRecommended
                  ? "border-purple-300 bg-gradient-to-b from-purple-50/40 to-white ring-1 ring-purple-300"
                  : "border-neutral-200/80 bg-white hover:border-neutral-300"
              )}
            >
              {/* Badges / Header */}
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs text-neutral-500 font-bold">
                      #{bid.overall_rank}
                    </span>
                    <span className="font-mono text-xs text-neutral-700">
                      {bid.response_number}
                    </span>
                  </div>

                  {isWinner ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <Award className="h-3 w-3" /> Awarded
                    </span>
                  ) : isRecommended ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                      ★ Best Value
                    </span>
                  ) : null}
                </div>

                {/* Supplier Name */}
                <h3 className="text-base font-bold text-neutral-900 mt-2">
                  {bid.supplier_name}
                </h3>
                <p className="text-[11px] text-neutral-400">
                  {bid.supplier_country ? `Jurisdiction: ${bid.supplier_country}` : "Global Supplier"}
                </p>

                {/* Overall Score Dial */}
                <div className="mt-4 p-3 rounded-lg bg-neutral-50 border border-neutral-100 space-y-1.5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[11px] font-semibold text-neutral-600">Composite Score</span>
                    <span className="font-mono text-lg font-bold text-neutral-900">
                      {bid.composite_score}
                      <span className="text-xs text-neutral-400 font-normal">/100</span>
                    </span>
                  </div>
                  <div className="w-full bg-neutral-200 h-2 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full transition-all",
                        bid.composite_score >= 85
                          ? "bg-emerald-500"
                          : bid.composite_score >= 70
                          ? "bg-[#FA651E]"
                          : "bg-amber-500"
                      )}
                      style={{ width: `${Math.min(bid.composite_score, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Commercial Price & Lead Time */}
                <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                  <div className="p-2.5 rounded-lg border border-neutral-100 bg-white">
                    <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">
                      Quoted Total
                    </span>
                    <span className="font-mono font-bold text-neutral-900 text-sm mt-0.5 block">
                      {bid.currency} {bid.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    <span className="text-[10px] text-neutral-400">
                      Price rank: #{bid.price_rank}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg border border-neutral-100 bg-white">
                    <span className="text-[10px] text-neutral-400 uppercase font-bold tracking-wider block">
                      Lead Time
                    </span>
                    <span className="font-mono font-bold text-neutral-900 text-sm mt-0.5 block">
                      {bid.average_lead_time_days ? `${bid.average_lead_time_days} Days` : "Not specified"}
                    </span>
                    <span className="text-[10px] text-neutral-400">
                      {bid.payment_terms || "Standard terms"}
                    </span>
                  </div>
                </div>

                {/* Criteria Breakdown */}
                <div className="mt-4 space-y-1.5 border-t border-neutral-100 pt-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400 block mb-1">
                    Score Breakdown
                  </span>
                  {Object.entries(bid.criteria_scores).map(([crit, score]) => (
                    <div key={crit} className="flex items-center justify-between text-xs">
                      <span className="text-neutral-600">{crit}</span>
                      <span className="font-mono font-semibold text-neutral-900">{score}/100</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Award Action Button */}
              <div className="mt-6 pt-3 border-t border-neutral-100">
                {data.status === "awarded" ? (
                  isWinner ? (
                    <div className="text-center py-1.5 text-xs text-emerald-700 font-bold bg-emerald-50 rounded-lg">
                      Contract Awarded
                    </div>
                  ) : (
                    <div className="text-center py-1.5 text-xs text-neutral-400 font-medium">
                      Event Closed
                    </div>
                  )
                ) : (
                  <Button
                    size="sm"
                    disabled={isAwarding !== null}
                    onClick={() => handleAward(bid.response_id, bid.supplier_name)}
                    className={cn(
                      "w-full text-xs h-8 font-semibold shadow-xs",
                      isRecommended
                        ? "bg-purple-700 hover:bg-purple-800 text-white"
                        : "bg-neutral-900 hover:bg-neutral-800 text-white"
                    )}
                  >
                    {isAwarding === bid.response_id ? (
                      <>
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                        Awarding...
                      </>
                    ) : (
                      <>
                        <Award className="mr-1.5 h-3.5 w-3.5" />
                        Award to {bid.supplier_name.split(" ")[0]}
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Detailed Line Item Price Comparison Matrix */}
      <div className="rounded-xl border border-neutral-200/80 bg-white p-5 shadow-xs space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">
          Line-Item Commercial Breakdown
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-neutral-50 border-b border-neutral-200 text-neutral-500 uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-3">Item Description</th>
                {data.bids.map((b) => (
                  <th key={b.response_id} className="py-2.5 px-3 text-right">
                    {b.supplier_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 font-mono">
              {data.bids[0]?.line_items?.map((itemRef, idx) => (
                <tr key={idx} className="hover:bg-neutral-50/50">
                  <td className="py-2.5 px-3 font-sans font-medium text-neutral-800">
                    {itemRef.item}
                    <span className="text-neutral-400 font-normal font-mono text-[10px] ml-1.5">
                      (Qty: {itemRef.qty})
                    </span>
                  </td>
                  {data.bids.map((b) => {
                    const matchLine = b.line_items[idx] || b.line_items.find((li) => li.item === itemRef.item);
                    return (
                      <td key={b.response_id} className="py-2.5 px-3 text-right font-medium text-neutral-900">
                        {matchLine
                          ? `${b.currency} ${matchLine.unit_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}/u`
                          : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
