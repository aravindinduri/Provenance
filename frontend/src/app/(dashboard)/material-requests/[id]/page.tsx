"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ClipboardList,
  Calendar,
  Building,
  User,
  DollarSign,
  Send,
  XCircle,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Check,
  X,
  Clock,
  Package,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DocumentStatusBadge,
  PriorityBadge,
} from "@/components/procurement/document-status-badge";
import { ApprovalActionBar } from "@/components/procurement/approval-action-bar";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

interface MRLineItem {
  id: string;
  item_id?: string | null;
  description: string;
  quantity: number;
  unit_of_measure?: string | null;
  estimated_unit_price?: number | null;
  currency?: string | null;
  preferred_supplier_id?: string | null;
}

interface MRDetail {
  id: string;
  org_id: string;
  mr_number: string;
  title: string;
  status: string;
  requested_by?: string | null;
  required_by_date?: string | null;
  priority?: string | null;
  department?: string | null;
  justification?: string | null;
  total_estimated_amount?: number | null;
  currency?: string | null;
  created_at: string;
  line_items: MRLineItem[];
}

interface WorkflowStep {
  id: string;
  step_number: number;
  approver_id?: string | null;
  approver_role?: string | null;
  status: string;
  decision_at?: string | null;
  comments?: string | null;
}

interface WorkflowDetail {
  id: string;
  document_type: string;
  document_id: string;
  current_step: number;
  status: string;
  initiated_by?: string | null;
  steps: WorkflowStep[];
}

export default function MaterialRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [mr, setMr] = useState<MRDetail | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      // 1. Fetch MR detail
      const res = await fetch(`/api/v1/material-requests/${id}`, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Material request not found (HTTP ${res.status})`);
      }
      const mrData: MRDetail = await res.json();
      setMr(mrData);

      // 2. Fetch associated approval workflow
      try {
        const wfRes = await fetch(`/api/v1/approvals/document/material_request/${id}`, { headers });
        if (wfRes.ok) {
          const wfData: WorkflowDetail = await wfRes.json();
          setWorkflow(wfData);
        } else {
          setWorkflow(null);
        }
      } catch {
        setWorkflow(null);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load material request");
    } finally {
      setIsLoading(false);
    }
  }, [id, orgId, getToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmitMR = async () => {
    setIsSubmitting(true);
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
        throw new Error(err.detail || "Submission failed");
      }

      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelMR = async () => {
    if (!confirm("Are you sure you want to cancel this requisition?")) return;
    setIsSubmitting(true);
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
        throw new Error(err.detail || "Cancellation failed");
      }

      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Cancellation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#FA651E]" />
      </div>
    );
  }

  if (errorMsg || !mr) {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-4">
        <Link
          href="/material-requests"
          className="inline-flex items-center text-xs text-neutral-500 hover:text-neutral-900"
        >
          <ArrowLeft className="mr-1 h-3.5 w-3.5" /> Back to Material Requests
        </Link>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-sm">Error Loading Requisition</div>
            <div className="mt-1">{errorMsg || "Material request not found."}</div>
          </div>
        </div>
      </div>
    );
  }

  const currentStep = workflow?.steps.find((s) => s.step_number === workflow.current_step);

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Back button */}
      <div>
        <Link
          href="/material-requests"
          className="inline-flex items-center text-xs text-neutral-500 hover:text-neutral-900 transition-colors"
        >
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Back to Material Requests
        </Link>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-2xs">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold font-mono tracking-tight text-neutral-900">
              {mr.mr_number}
            </h1>
            <DocumentStatusBadge status={mr.status} />
            <PriorityBadge priority={mr.priority || "medium"} />
          </div>
          <h2 className="text-sm font-semibold text-neutral-800">{mr.title}</h2>
          <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500 pt-0.5">
            {mr.department && (
              <span className="flex items-center gap-1 font-medium">
                <Building className="h-3.5 w-3.5 text-neutral-400" />
                {mr.department}
              </span>
            )}
            {mr.required_by_date && (
              <span className="flex items-center gap-1 font-mono">
                <Calendar className="h-3.5 w-3.5 text-neutral-400" />
                Required: {mr.required_by_date}
              </span>
            )}
            {mr.requested_by && (
              <span className="flex items-center gap-1">
                <User className="h-3.5 w-3.5 text-neutral-400" />
                Requester: {mr.requested_by}
              </span>
            )}
          </div>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex items-center gap-2">
          {mr.status === "draft" && (
            <Button
              size="sm"
              onClick={handleSubmitMR}
              disabled={isSubmitting}
              className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs"
            >
              <Send className="mr-1.5 h-3.5 w-3.5" />
              Submit for Approval
            </Button>
          )}

          {(mr.status === "draft" || mr.status === "pending_approval") && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelMR}
              disabled={isSubmitting}
              className="h-8 text-xs text-rose-700 border-rose-200 hover:bg-rose-50"
            >
              <XCircle className="mr-1.5 h-3.5 w-3.5" />
              Cancel Request
            </Button>
          )}
        </div>
      </div>

      {/* Approval Decision Bar (if pending) */}
      {workflow && workflow.status === "pending" && (
        <ApprovalActionBar
          workflowId={workflow.id}
          documentType={workflow.document_type}
          documentNumber={mr.mr_number}
          currentStepNumber={workflow.current_step}
          requiredRole={currentStep?.approver_role || "Approver"}
          isPending={workflow.status === "pending"}
          onDecisionSuccess={loadData}
        />
      )}

      {/* Approval Workflow Progress Card */}
      {workflow && (
        <Card className="p-4 space-y-3 border-neutral-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-neutral-900 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Approval Workflow Status
            </span>
            <DocumentStatusBadge status={workflow.status} size="sm" />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {workflow.steps.map((st) => (
              <div
                key={st.id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono border ${
                  st.status === "approved"
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : st.status === "rejected"
                    ? "bg-rose-50 text-rose-800 border-rose-200"
                    : st.step_number === workflow.current_step
                    ? "bg-amber-50 text-amber-800 border-amber-300 font-semibold"
                    : "bg-neutral-50 text-neutral-400 border-neutral-200"
                }`}
              >
                {st.status === "approved" ? (
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                ) : st.status === "rejected" ? (
                  <X className="h-3.5 w-3.5 text-rose-600" />
                ) : (
                  <Clock className="h-3.5 w-3.5 text-amber-500" />
                )}
                <span>
                  Step {st.step_number}: {st.approver_role || "Approver"}
                </span>
                {st.comments && (
                  <span className="text-[10px] text-neutral-500 italic">"{st.comments}"</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Line Items Table */}
      <Card className="overflow-hidden border-neutral-200 shadow-2xs">
        <div className="border-b border-neutral-100 bg-neutral-50/70 px-4 py-3 flex items-center justify-between">
          <span className="text-xs font-semibold text-neutral-900 uppercase tracking-wider font-mono flex items-center gap-1.5">
            <Package className="h-4 w-4 text-[#FA651E]" />
            Requisition Items ({mr.line_items.length})
          </span>
          <span className="text-xs font-mono font-bold text-neutral-900">
            Total: {mr.currency || "USD"}{" "}
            {Number(mr.total_estimated_amount || 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-neutral-200 bg-neutral-50/50 text-neutral-500 font-mono text-[11px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-2.5 font-semibold">#</th>
                <th className="px-4 py-2.5 font-semibold">Description</th>
                <th className="px-3 py-2.5 font-semibold text-right">Quantity</th>
                <th className="px-3 py-2.5 font-semibold">UoM</th>
                <th className="px-4 py-2.5 font-semibold text-right">Unit Price</th>
                <th className="px-4 py-2.5 font-semibold text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {mr.line_items.map((li, idx) => {
                const lineTotal = (Number(li.quantity) || 0) * (Number(li.estimated_unit_price) || 0);
                return (
                  <tr key={li.id || idx} className="hover:bg-neutral-50/50">
                    <td className="px-4 py-3 font-mono text-neutral-400 text-[11px]">{idx + 1}</td>
                    <td className="px-4 py-3 font-medium text-neutral-900">{li.description}</td>
                    <td className="px-3 py-3 text-right font-mono font-semibold text-neutral-800">
                      {Number(li.quantity).toLocaleString()}
                    </td>
                    <td className="px-3 py-3 font-mono text-neutral-500 text-[11px]">
                      {li.unit_of_measure || "units"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-neutral-700">
                      {li.currency || mr.currency || "USD"}{" "}
                      {Number(li.estimated_unit_price || 0).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-neutral-900">
                      {li.currency || mr.currency || "USD"}{" "}
                      {lineTotal.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Justification Box */}
      {mr.justification && (
        <Card className="p-4 space-y-1.5 border-neutral-200">
          <div className="text-xs font-semibold text-neutral-900 font-mono uppercase tracking-wider">
            Business Justification
          </div>
          <p className="text-xs text-neutral-600 leading-relaxed">{mr.justification}</p>
        </Card>
      )}
    </div>
  );
}
