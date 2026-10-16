"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  InvoiceMatchView,
  InvoiceDetailItem,
} from "@/components/procurement/invoice-match-view";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function InvoiceDetailPage(): React.ReactElement {
  const params = useParams();
  const router = useRouter();
  const id = typeof params?.id === "string" ? params.id : "";
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [invoice, setInvoice] = useState<InvoiceDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadInvoice = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/invoices/${id}`, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch invoice (HTTP ${res.status})`);
      }

      const data = await res.json();
      setInvoice(data);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load invoice details");
    } finally {
      setIsLoading(false);
    }
  }, [id, orgId, getToken]);

  useEffect(() => {
    loadInvoice();
  }, [loadInvoice]);

  return (
    <div className="flex-1 space-y-6 p-6">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-32 text-neutral-500 font-mono">
          <Loader2 className="h-8 w-8 animate-spin text-[#FA651E] mb-3" />
          <p className="text-sm font-medium">Loading 3-way match &amp; invoice reconciliation details...</p>
        </div>
      ) : errorMsg || !invoice ? (
        <div className="flex flex-col items-center justify-center py-24 px-4 text-center font-mono">
          <div className="rounded-full bg-rose-50 p-3 mb-3 text-rose-500">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-sm font-semibold text-neutral-800">
            {errorMsg || "Invoice not found"}
          </h2>
          <p className="mt-1 text-xs text-neutral-500 max-w-sm">
            The requested invoice could not be retrieved from your organization's spend records.
          </p>
          <div className="mt-4 flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/invoices")}
              className="text-xs"
            >
              Back to Invoices
            </Button>
            <Button size="sm" onClick={loadInvoice} className="text-xs bg-neutral-900 text-white">
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <InvoiceMatchView invoice={invoice} onRefresh={loadInvoice} />
      )}
    </div>
  );
}
