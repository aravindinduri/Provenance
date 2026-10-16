"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BidComparisonTable, BidComparisonData } from "@/components/procurement/bid-comparison-table";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function BidComparisonPage(): React.ReactElement {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [comparisonData, setComparisonData] = useState<BidComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadComparison = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/rfx/${id}/compare`, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load bid comparison");
      }

      const data = await res.json();
      setComparisonData(data);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Error loading comparison data");
    } finally {
      setIsLoading(false);
    }
  }, [id, orgId, getToken]);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-neutral-400">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600 mb-3" />
        <p className="text-xs font-medium">Computing deterministic multi-criteria bid comparison...</p>
      </div>
    );
  }

  if (errorMsg || !comparisonData) {
    return (
      <div className="flex-1 p-8 max-w-4xl mx-auto space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
          <div className="space-y-1">
            <span className="font-semibold">Unable to evaluate bids</span>
            <div>{errorMsg || "Comparison data not available."}</div>
          </div>
        </div>
        <Link href={`/rfx/${id}`}>
          <Button variant="outline" size="sm" className="text-xs">
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            Back to Event
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href={`/rfx/${id}`}>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-neutral-500 hover:text-neutral-900">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-neutral-500">
                {comparisonData.rfx_number}
              </span>
              <span className="text-[10px] uppercase font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.2 rounded">
                Bid Evaluation Matrix
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-neutral-900 mt-1 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              Side-by-Side Quotation Comparison
            </h1>
            <p className="text-xs text-neutral-500 mt-0.5">
              Deterministic weighted evaluation comparing price competitiveness, fulfillment speed, and risk posture.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadComparison}
            disabled={isLoading}
            className="h-8 text-xs border-neutral-200"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Recalculate
          </Button>
        </div>
      </div>

      {/* Comparison Matrix Component */}
      <BidComparisonTable
        data={comparisonData}
        onAwardSuccess={loadComparison}
      />
    </div>
  );
}
