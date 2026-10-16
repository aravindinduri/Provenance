"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ShoppingCart, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  PurchaseOrderList,
  PurchaseOrderListItem,
} from "@/components/procurement/purchase-order-list";
import { PurchaseOrderModal } from "@/components/procurement/purchase-order-modal";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function PurchaseOrdersPage(): React.ReactElement {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [items, setItems] = useState<PurchaseOrderListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const loadPurchaseOrders = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      let url = "/api/v1/purchase-orders?limit=100";
      if (selectedStatus !== "all") {
        url += `&status=${selectedStatus}`;
      }

      const res = await fetch(url, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          err.detail || `Failed to fetch purchase orders (HTTP ${res.status})`
        );
      }

      const data = await res.json();
      setItems(data.items || []);
    } catch (err: unknown) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to load purchase orders"
      );
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, selectedStatus, getToken]);

  useEffect(() => {
    loadPurchaseOrders();
  }, [loadPurchaseOrders]);

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-neutral-100 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600 shadow-sm">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-neutral-900">
                Purchase Orders
              </h1>
              <p className="text-xs text-neutral-500">
                Manage committed purchasing contracts, approval states, and intake fulfillment
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadPurchaseOrders}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-900 border-neutral-200"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadPurchaseOrders}
            className="text-xs text-rose-700 hover:bg-rose-100/50"
          >
            Retry
          </Button>
        </div>
      )}

      {/* List Component */}
      <PurchaseOrderList
        items={items}
        isLoading={isLoading}
        selectedStatus={selectedStatus}
        onSelectStatus={setSelectedStatus}
        onCreateClick={() => setIsCreateModalOpen(true)}
        onRefresh={loadPurchaseOrders}
      />

      {/* Modal */}
      <PurchaseOrderModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setIsCreateModalOpen(false);
          loadPurchaseOrders();
        }}
      />
    </div>
  );
}
