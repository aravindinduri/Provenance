"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Loader2, AlertCircle, ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  PurchaseOrderDetail,
  PODetailItem,
} from "@/components/procurement/purchase-order-detail";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function PurchaseOrderDetailPage(): React.ReactElement {
  const params = useParams();
  const router = useRouter();
  const id = typeof params?.id === "string" ? params.id : "";
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [po, setPo] = useState<PODetailItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadPO = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/purchase-orders/${id}`, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch purchase order (HTTP ${res.status})`);
      }

      const data = await res.json();
      setPo(data);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load purchase order details");
    } finally {
      setIsLoading(false);
    }
  }, [id, orgId, getToken]);

  useEffect(() => {
    loadPO();
  }, [loadPO]);

  return (
    <div className="flex-1 space-y-6 p-6">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-32 text-neutral-500">
          <Loader2 className="h-8 w-8 animate-spin text-neutral-400 mb-3" />
          <p className="text-sm font-medium">Loading purchase order details...</p>
        </div>
      ) : errorMsg || !po ? (
        <div className="flex flex-col items-center justify-center py-24 px-4 text-center">
          <div className="rounded-full bg-rose-50 p-3 mb-3 text-rose-500">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-sm font-semibold text-neutral-800">
            {errorMsg || "Purchase order not found"}
          </h2>
          <p className="mt-1 text-xs text-neutral-500 max-w-sm">
            The requested purchase order could not be retrieved or has been removed.
          </p>
          <div className="mt-4 flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/purchase-orders")}
              className="text-xs"
            >
              Back to Purchase Orders
            </Button>
            <Button size="sm" onClick={loadPO} className="text-xs bg-neutral-900 text-white">
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <PurchaseOrderDetail po={po} onRefresh={loadPO} />
      )}
    </div>
  );
}
