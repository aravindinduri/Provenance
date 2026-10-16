"use client";

import React, { useState } from "react";
import { Check, X, Loader2, AlertCircle, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

interface ApprovalActionBarProps {
  workflowId: string;
  documentType: string;
  documentNumber?: string;
  currentStepNumber: number;
  requiredRole?: string;
  isPending: boolean;
  onDecisionSuccess?: () => void;
}

export function ApprovalActionBar({
  workflowId,
  documentType,
  documentNumber,
  currentStepNumber,
  requiredRole,
  isPending,
  onDecisionSuccess,
}: ApprovalActionBarProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState<"approve" | "reject">("approve");
  const [comments, setComments] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleOpenDialog = (action: "approve" | "reject") => {
    setSelectedAction(action);
    setComments("");
    setErrorMsg(null);
    setDialogOpen(true);
  };

  const handleConfirmDecision = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/approvals/workflows/${workflowId}/decide`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          action: selectedAction,
          comments: comments.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Decision failed (HTTP ${res.status})`);
      }

      setDialogOpen(false);
      onDecisionSuccess?.();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to record decision");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isPending) {
    return null;
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 shadow-2xs">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-neutral-900">
              Approval Step {currentStepNumber} Pending
            </div>
            <div className="text-[11px] text-neutral-500 font-mono">
              Required authority: <span className="font-semibold text-amber-900">{requiredRole || "Approver"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleOpenDialog("reject")}
            className="h-8 border-rose-200 bg-white text-xs font-medium text-rose-700 hover:bg-rose-50 hover:text-rose-800"
          >
            <X className="mr-1.5 h-3.5 w-3.5" />
            Reject
          </Button>
          <Button
            size="sm"
            onClick={() => handleOpenDialog("approve")}
            className="h-8 bg-emerald-600 text-xs font-medium text-white shadow-2xs hover:bg-emerald-700"
          >
            <Check className="mr-1.5 h-3.5 w-3.5" />
            Approve
          </Button>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-semibold">
              {selectedAction === "approve" ? (
                <>
                  <Check className="h-4 w-4 text-emerald-600" />
                  Approve {documentNumber || documentType.replace(/_/g, " ")}
                </>
              ) : (
                <>
                  <X className="h-4 w-4 text-rose-600" />
                  Reject {documentNumber || documentType.replace(/_/g, " ")}
                </>
              )}
            </DialogTitle>
            <DialogDescription className="text-xs text-neutral-500">
              {selectedAction === "approve"
                ? "This will approve the current step under your delegation of authority."
                : "This will reject the requisition and send it back to the requester."}
            </DialogDescription>
          </DialogHeader>

          {errorMsg && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-2 py-1">
            <label className="text-xs font-medium text-neutral-700">
              Decision Comments (optional)
            </label>
            <Textarea
              placeholder={
                selectedAction === "approve"
                  ? "e.g., Reviewed price against budget. Approved."
                  : "e.g., Exceeds department threshold. Please adjust quantity."
              }
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className="min-h-20 text-xs"
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              disabled={isSubmitting}
              onClick={() => setDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={isSubmitting}
              onClick={handleConfirmDecision}
              className={
                selectedAction === "approve"
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                  : "bg-rose-600 hover:bg-rose-700 text-white"
              }
            >
              {isSubmitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              Confirm {selectedAction === "approve" ? "Approval" : "Rejection"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
