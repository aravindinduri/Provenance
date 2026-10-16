"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  AlertCircle,
  RefreshCw,
  FileQuestion,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { QuotationList, QuotationItem } from "@/components/procurement/quotation-list";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function QuotationsPage(): React.ReactElement {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [items, setItems] = useState<QuotationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadQuotations = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch("/api/v1/supplier-quotations?limit=100", { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch quotations (HTTP ${res.status})`);
      }

      const data = await res.json();
      setItems(data.items || []);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load quotations");
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, getToken]);

  useEffect(() => {
    loadQuotations();
  }, [loadQuotations]);

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <FileText className="h-6 w-6 text-[#FA651E]" />
            Supplier Quotations
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Commercial proposals, pricing breakdowns, validity terms, and multi-vendor bids across sourcing events.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadQuotations}
            disabled={isLoading}
            className="h-8 text-xs border-neutral-200"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/rfx">
            <Button
              size="sm"
              className="h-8 bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-medium shadow-xs"
            >
              <FileQuestion className="mr-1.5 h-3.5 w-3.5" />
              View Sourcing Events
            </Button>
          </Link>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <div className="space-y-1">
            <span className="font-semibold">Unable to load quotations</span>
            <div>{errorMsg}</div>
          </div>
        </div>
      )}

      {/* Main List */}
      <QuotationList
        items={items}
        isLoading={isLoading}
        onRefresh={loadQuotations}
      />
    </div>
  );
}
