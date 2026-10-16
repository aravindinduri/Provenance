"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Receipt, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  InvoiceList,
  InvoiceListItem,
  InvoiceStats,
} from "@/components/procurement/invoice-list";
import { InvoiceModal } from "@/components/procurement/invoice-modal";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function InvoicesPage(): React.ReactElement {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [stats, setStats] = useState<InvoiceStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const loadInvoices = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      let url = "/api/v1/invoices?limit=100";
      if (selectedStatus !== "all") {
        url += `&match_status=${selectedStatus}`;
      }

      // Fetch invoices & stats in parallel
      const [invoicesRes, statsRes] = await Promise.all([
        fetch(url, { headers }),
        fetch("/api/v1/invoices/stats", { headers }),
      ]);

      if (!invoicesRes.ok) {
        const err = await invoicesRes.json().catch(() => ({}));
        throw new Error(
          err.detail || `Failed to fetch invoices (HTTP ${invoicesRes.status})`
        );
      }

      const invoicesData = await invoicesRes.json();
      setItems(invoicesData.items || []);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (err: unknown) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to load invoices"
      );
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, selectedStatus, getToken]);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-neutral-100 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-orange-50 p-2.5 text-[#FA651E] shadow-sm">
              <Receipt className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-neutral-900 font-mono">
                Purchase Invoices &amp; 3-Way Matching
              </h1>
              <p className="text-xs text-neutral-500 font-mono">
                Automated 3-way matching engine across Purchase Orders, Goods Receipts (GRN), and Supplier Invoices
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadInvoices}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-900 border-neutral-200 font-mono"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-xs text-rose-800 font-mono">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadInvoices}
            className="text-xs text-rose-700 hover:bg-rose-100/50 font-mono"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Invoice List */}
      <InvoiceList
        items={items}
        stats={stats}
        isLoading={isLoading}
        selectedStatus={selectedStatus}
        onSelectStatus={setSelectedStatus}
        onCreateClick={() => setIsCreateModalOpen(true)}
        onRefresh={loadInvoices}
      />

      {/* Ingestion / Intake Modal */}
      <InvoiceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setIsCreateModalOpen(false);
          loadInvoices();
        }}
      />
    </div>
  );
}
