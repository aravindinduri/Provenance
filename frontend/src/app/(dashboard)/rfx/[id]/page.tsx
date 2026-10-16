"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RFxDetailView } from "@/components/procurement/rfx-detail";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export default function RFxDetailPage(): React.ReactElement {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [rfx, setRfx] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/rfx/${id}`, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load sourcing event");
      }

      const data = await res.json();
      setRfx(data);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Error loading event");
    } finally {
      setIsLoading(false);
    }
  }, [id, orgId, getToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePublish = async () => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/rfx/${id}/publish`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to publish event");
      }

      loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error publishing event");
    }
  };

  const handleCloseEvent = async () => {
    if (!confirm("Are you sure you want to close this event to any new quotations?")) return;
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/rfx/${id}/close`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to close event");
      }

      loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error closing event");
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-neutral-400">
        <Loader2 className="h-8 w-8 animate-spin text-[#FA651E] mb-3" />
        <p className="text-xs font-medium">Loading sourcing event details...</p>
      </div>
    );
  }

  if (errorMsg || !rfx) {
    return (
      <div className="flex-1 p-8 max-w-4xl mx-auto space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
          <div className="space-y-1">
            <span className="font-semibold">Unable to display event</span>
            <div>{errorMsg || "Sourcing event not found."}</div>
          </div>
        </div>
        <Link href="/rfx">
          <Button variant="outline" size="sm" className="text-xs">
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
            Back to RFx List
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Back button */}
      <div className="flex items-center gap-2">
        <Link href="/rfx">
          <Button variant="ghost" size="sm" className="h-8 text-xs text-neutral-500 hover:text-neutral-900">
            <ArrowLeft className="mr-1 h-3.5 w-3.5" />
            All Sourcing Events
          </Button>
        </Link>
      </div>

      <RFxDetailView
        rfx={rfx}
        onRefresh={loadData}
        onPublish={handlePublish}
        onCloseEvent={handleCloseEvent}
      />
    </div>
  );
}
