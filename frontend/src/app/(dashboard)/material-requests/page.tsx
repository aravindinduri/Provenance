"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ClipboardList,
  AlertCircle,
  Plus,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  MaterialRequestList,
  MaterialRequestListItem,
} from "@/components/procurement/material-request-list";
import { MaterialRequestFormModal } from "@/components/procurement/material-request-form";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function MaterialRequestsPage(): React.ReactElement {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [items, setItems] = useState<MaterialRequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const loadRequests = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      let url = "/api/v1/material-requests?limit=100";
      if (selectedStatus !== "all") {
        url += `&status=${selectedStatus}`;
      }

      const res = await fetch(url, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch material requests (HTTP ${res.status})`);
      }

      const data = await res.json();
      setItems(data.items || []);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load requests");
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, selectedStatus, getToken]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const handleSubmitDraft = async (id: string) => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/material-requests/${id}/submit`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to submit request for approval");
      }

      loadRequests();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error submitting request");
    }
  };

  const handleCancelMR = async (id: string) => {
    if (!confirm("Are you sure you want to cancel this requisition?")) return;
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/material-requests/${id}/cancel`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to cancel request");
      }

      loadRequests();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error cancelling request");
    }
  };

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <ClipboardList className="h-6 w-6 text-[#FA651E]" />
            Material Requests
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Purchase requisitions, line item specifications, and approval tracking across departments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadRequests}
            disabled={isLoading}
            className="h-8 text-xs border-neutral-200"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs font-medium"
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Requisition
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <div className="space-y-1">
            <span className="font-semibold">Unable to load material requests</span>
            <div>{errorMsg}</div>
          </div>
        </div>
      )}

      {/* Main List */}
      <MaterialRequestList
        items={items}
        isLoading={isLoading}
        selectedStatus={selectedStatus}
        onSelectStatus={setSelectedStatus}
        onOpenCreateModal={() => setIsCreateModalOpen(true)}
        onSubmitDraft={handleSubmitDraft}
        onCancelMR={handleCancelMR}
      />

      {/* Modal */}
      <MaterialRequestFormModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => loadRequests()}
      />
    </div>
  );
}
