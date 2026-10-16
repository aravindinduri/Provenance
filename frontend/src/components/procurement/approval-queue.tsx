"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  Filter,
  Check,
  X,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { ApprovalActionBar } from "@/components/procurement/approval-action-bar";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export interface ApprovalStepItem {
  id: string;
  step_number: number;
  approver_id?: string | null;
  approver_role?: string | null;
  status: string;
  decision_at?: string | null;
  comments?: string | null;
}

export interface ApprovalWorkflowItem {
  id: string;
  org_id: string;
  document_type: string;
  document_id: string;
  current_step: number;
  status: string;
  initiated_by?: string | null;
  initiated_at: string;
  completed_at?: string | null;
  steps: ApprovalStepItem[];
}

export function ApprovalQueue() {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [selectedRole, setSelectedRole] = useState("all");
  const [workflows, setWorkflows] = useState<ApprovalWorkflowItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const roles = [
    { label: "All Roles", value: "all" },
    { label: "Category Manager", value: "category_manager" },
    { label: "Procurement Head", value: "procurement_head" },
    { label: "Manager", value: "manager" },
    { label: "Director", value: "director" },
    { label: "Finance", value: "finance" },
    { label: "Admin", value: "admin" },
  ];

  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/approvals/queue?role=${selectedRole}&limit=50`, {
        headers,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load approval queue (HTTP ${res.status})`);
      }

      const data = await res.json();
      setWorkflows(data.items || []);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load approval queue");
      setWorkflows([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, selectedRole, getToken]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  return (
    <div className="space-y-4">
      {/* Role Selector Header */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-neutral-500 flex items-center gap-1 mr-1">
            <Filter className="h-3 w-3" />
            Approver Role:
          </span>
          <div className="flex items-center gap-1">
            {roles.map((r) => (
              <button
                key={r.value}
                onClick={() => setSelectedRole(r.value)}
                className={`rounded-lg px-2.5 py-1 text-xs transition-colors ${
                  selectedRole === r.value
                    ? "bg-neutral-900 text-white font-semibold shadow-2xs"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200/80"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={loadQueue}
          disabled={isLoading}
          className="h-8 text-xs border-neutral-200"
        >
          {isLoading ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
          Refresh Queue
        </Button>
      </div>

      {errorMsg && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Queue Items */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-12 text-center text-neutral-400 rounded-xl border border-neutral-200 bg-white">
          <Loader2 className="h-6 w-6 animate-spin text-[#FA651E] mb-2" />
          <span className="text-xs">Fetching pending workflows for {selectedRole}...</span>
        </div>
      ) : workflows.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-14 text-center rounded-xl border border-neutral-200 bg-white">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 mb-3">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-neutral-900">All Clear!</h3>
          <p className="mt-1 max-w-sm text-xs text-neutral-500">
            No pending approval workflows assigned to the <span className="font-semibold text-neutral-800 font-mono">{selectedRole}</span> role at this time.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {workflows.map((wf) => {
            const currentStep = wf.steps.find((s) => s.step_number === wf.current_step);
            const docLink =
              wf.document_type === "material_request"
                ? `/material-requests/${wf.document_id}`
                : "#";

            return (
              <div
                key={wf.id}
                className="rounded-xl border border-neutral-200 bg-white p-4 shadow-2xs space-y-3 hover:border-neutral-300 transition-colors"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold uppercase tracking-wider text-neutral-500">
                        {wf.document_type.replace(/_/g, " ")}
                      </span>
                      <DocumentStatusBadge status={wf.status} size="sm" />
                    </div>
                    <Link
                      href={docLink}
                      className="text-sm font-semibold text-neutral-900 hover:text-[#FA651E] transition-colors font-mono"
                    >
                      Doc #{wf.document_id.slice(0, 8)}...
                    </Link>
                    <div className="text-[11px] text-neutral-400 flex items-center gap-2">
                      <span>Initiated by: {wf.initiated_by || "System"}</span>
                      <span>•</span>
                      <span>{new Date(wf.initiated_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  {/* Step progression pill */}
                  <div className="flex items-center gap-1.5 rounded-lg bg-neutral-50 px-2.5 py-1 text-xs border border-neutral-200 font-mono">
                    <Clock className="h-3 w-3 text-neutral-400" />
                    <span>
                      Step <span className="font-bold text-neutral-900">{wf.current_step}</span> of{" "}
                      {wf.steps.length || 1}
                    </span>
                  </div>
                </div>

                {/* Steps visual track */}
                <div className="flex items-center gap-2 pt-1 border-t border-neutral-100">
                  {wf.steps.map((st) => (
                    <div
                      key={st.id}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border ${
                        st.status === "approved"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                          : st.status === "rejected"
                          ? "bg-rose-50 text-rose-800 border-rose-200"
                          : st.step_number === wf.current_step
                          ? "bg-amber-50 text-amber-800 border-amber-300 font-semibold"
                          : "bg-neutral-50 text-neutral-400 border-neutral-200"
                      }`}
                    >
                      {st.status === "approved" ? (
                        <Check className="h-3 w-3 text-emerald-600" />
                      ) : st.status === "rejected" ? (
                        <X className="h-3 w-3 text-rose-600" />
                      ) : (
                        <span>#{st.step_number}</span>
                      )}
                      <span>{st.approver_role || "Approver"}</span>
                    </div>
                  ))}
                </div>

                {/* Inline Action Bar */}
                <ApprovalActionBar
                  workflowId={wf.id}
                  documentType={wf.document_type}
                  documentNumber={`Doc #${wf.document_id.slice(0, 8)}`}
                  currentStepNumber={wf.current_step}
                  requiredRole={currentStep?.approver_role || selectedRole}
                  isPending={wf.status === "pending"}
                  onDecisionSuccess={loadQueue}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
