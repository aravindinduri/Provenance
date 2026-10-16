"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  Settings,
  Plus,
  Loader2,
  AlertCircle,
  Layers,
  Scale,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { ApprovalQueue } from "@/components/procurement/approval-queue";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export interface ApprovalRuleItem {
  id: string;
  document_type: string;
  min_amount?: number | null;
  max_amount?: number | null;
  currency?: string | null;
  required_role: string;
  auto_approve_below?: number | null;
  is_active: boolean;
  priority: number;
}

export default function ApprovalsPage() {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [activeTab, setActiveTab] = useState<"queue" | "rules">("queue");
  const [rules, setRules] = useState<ApprovalRuleItem[]>([]);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [rulesError, setRulesError] = useState<string | null>(null);

  // Add Rule Modal
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);
  const [docType, setDocType] = useState("material_request");
  const [requiredRole, setRequiredRole] = useState("manager");
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");
  const [autoBelow, setAutoBelow] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [isSubmittingRule, setIsSubmittingRule] = useState(false);
  const [ruleModalError, setRuleModalError] = useState<string | null>(null);

  const loadRules = useCallback(async () => {
    setIsLoadingRules(true);
    setRulesError(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch("/api/v1/approvals/rules", { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load DoA rules");
      }

      const data = await res.json();
      setRules(data || []);
    } catch (err: unknown) {
      setRulesError(err instanceof Error ? err.message : "Failed to load rules");
      setRules([]);
    } finally {
      setIsLoadingRules(false);
    }
  }, [orgId, getToken]);

  useEffect(() => {
    if (activeTab === "rules") {
      loadRules();
    }
  }, [activeTab, loadRules]);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingRule(true);
    setRuleModalError(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        document_type: docType,
        required_role: requiredRole,
        min_amount: minAmount ? parseFloat(minAmount) : undefined,
        max_amount: maxAmount ? parseFloat(maxAmount) : undefined,
        auto_approve_below: autoBelow ? parseFloat(autoBelow) : undefined,
        currency,
        priority: 10,
      };

      const res = await fetch("/api/v1/approvals/rules", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to create rule");
      }

      setIsRuleModalOpen(false);
      loadRules();
    } catch (err: unknown) {
      setRuleModalError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setIsSubmittingRule(false);
    }
  };

  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-[#FA651E]" />
            Approvals &amp; Governance
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Delegation of Authority (DoA) engine, pending decision queues, and audit trails.
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex items-center gap-1 rounded-xl bg-neutral-100 p-1 border border-neutral-200">
          <button
            onClick={() => setActiveTab("queue")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === "queue"
                ? "bg-white text-neutral-900 font-semibold shadow-2xs"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            Pending Queue
          </button>
          <button
            onClick={() => setActiveTab("rules")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === "rules"
                ? "bg-white text-neutral-900 font-semibold shadow-2xs"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            DoA Rules Matrix
          </button>
        </div>
      </div>

      {/* Active Tab Content */}
      {activeTab === "queue" ? (
        <ApprovalQueue />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-neutral-500 font-mono">
              Configured threshold rules for automatic routing and authorization
            </span>
            <Button
              size="sm"
              onClick={() => {
                setRuleModalError(null);
                setIsRuleModalOpen(true);
              }}
              className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs"
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add Authority Rule
            </Button>
          </div>

          {rulesError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{rulesError}</span>
            </div>
          )}

          <div className="rounded-xl border border-neutral-200/80 bg-white overflow-hidden shadow-2xs">
            {isLoadingRules ? (
              <div className="flex flex-col items-center justify-center p-12 text-center text-neutral-400">
                <Loader2 className="h-6 w-6 animate-spin text-[#FA651E] mb-2" />
                <span className="text-xs">Loading rules matrix...</span>
              </div>
            ) : rules.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-14 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-50 text-[#FA651E] mb-3">
                  <Scale className="h-6 w-6" />
                </div>
                <h3 className="text-sm font-semibold text-neutral-900">No Custom Rules Configured</h3>
                <p className="mt-1 max-w-sm text-xs text-neutral-500">
                  By default, material requests auto-approve if no explicit thresholds are defined. Create your first rule to require managerial or financial approval.
                </p>
                <Button
                  size="sm"
                  onClick={() => setIsRuleModalOpen(true)}
                  className="mt-4 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs"
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Define Threshold Rule
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-neutral-200 bg-neutral-50/80 text-neutral-500 font-mono text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Document Type</th>
                      <th className="px-4 py-3 font-semibold">Required Role</th>
                      <th className="px-4 py-3 font-semibold text-right">Min Amount</th>
                      <th className="px-4 py-3 font-semibold text-right">Max Amount</th>
                      <th className="px-4 py-3 font-semibold text-right">Auto-Approve Below</th>
                      <th className="px-3 py-3 font-semibold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {rules.map((rule) => (
                      <tr key={rule.id} className="hover:bg-neutral-50/60 transition-colors">
                        <td className="px-4 py-3 font-mono font-bold text-neutral-900 uppercase">
                          {rule.document_type.replace(/_/g, " ")}
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-semibold text-amber-900 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-mono text-[11px]">
                            {rule.required_role}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-neutral-700">
                          {rule.min_amount != null
                            ? `${rule.currency || "$"}${Number(rule.min_amount).toLocaleString()}`
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-neutral-700">
                          {rule.max_amount != null
                            ? `${rule.currency || "$"}${Number(rule.max_amount).toLocaleString()}`
                            : "No limit"}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-emerald-700">
                          {rule.auto_approve_below != null
                            ? `< ${rule.currency || "$"}${Number(rule.auto_approve_below).toLocaleString()}`
                            : "—"}
                        </td>
                        <td className="px-3 py-3 text-center">
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-mono text-emerald-700 border border-emerald-200">
                            Active
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Rule Dialog */}
      <Dialog open={isRuleModalOpen} onOpenChange={setIsRuleModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-semibold">
              <Scale className="h-4 w-4 text-[#FA651E]" />
              New Authority Rule
            </DialogTitle>
            <DialogDescription className="text-xs text-neutral-500">
              Configure spend thresholds and mandatory role-based approval steps.
            </DialogDescription>
          </DialogHeader>

          {ruleModalError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{ruleModalError}</span>
            </div>
          )}

          <form onSubmit={handleCreateRule} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Document Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none"
              >
                <option value="material_request">Material Request</option>
                <option value="purchase_order">Purchase Order</option>
                <option value="invoice">Invoice</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Required Role *</label>
              <select
                value={requiredRole}
                onChange={(e) => setRequiredRole(e.target.value)}
                className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none font-mono"
              >
                <option value="manager">manager</option>
                <option value="director">director</option>
                <option value="finance">finance</option>
                <option value="admin">admin</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Min Amount ($)</label>
                <Input
                  type="number"
                  placeholder="0"
                  value={minAmount}
                  onChange={(e) => setMinAmount(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Max Amount ($)</label>
                <Input
                  type="number"
                  placeholder="e.g. 50000"
                  value={maxAmount}
                  onChange={(e) => setMaxAmount(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Auto-Approve Below ($)</label>
              <Input
                type="number"
                placeholder="e.g. 1000 (auto-approve below this)"
                value={autoBelow}
                onChange={(e) => setAutoBelow(e.target.value)}
                className="h-8 text-xs font-mono"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-neutral-100">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsRuleModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingRule}
                className="bg-[#FA651E] hover:bg-[#E05310] text-white shadow-2xs"
              >
                {isSubmittingRule && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                Save Rule
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
