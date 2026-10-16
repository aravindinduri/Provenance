"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type ProcurementDocumentStatus =
  | "draft"
  | "pending_approval"
  | "pending"
  | "approved"
  | "published"
  | "q_and_a"
  | "evaluation"
  | "negotiation"
  | "awarded"
  | "closed"
  | "ordered"
  | "partially_ordered"
  | "cancelled"
  | "rejected"
  | "active"
  | "inactive"
  | "invited"
  | "viewed"
  | "responded"
  | "shortlisted"
  | "declined";

interface DocumentStatusBadgeProps {
  status: string;
  className?: string;
  size?: "sm" | "md";
}

export function DocumentStatusBadge({
  status,
  className,
  size = "md",
}: DocumentStatusBadgeProps) {
  const normalized = (status || "").toLowerCase().trim();

  let label = status.replace(/_/g, " ");
  label = label.replace(/\b\w/g, (c) => c.toUpperCase());

  let styleClasses = "bg-neutral-100 text-neutral-700 border-neutral-200";

  switch (normalized) {
    case "draft":
      styleClasses = "bg-neutral-100 text-neutral-700 border-neutral-300";
      break;
    case "pending_approval":
    case "pending":
      styleClasses = "bg-amber-50 text-amber-700 border-amber-200/80 font-medium";
      break;
    case "published":
      styleClasses = "bg-cyan-50 text-cyan-700 border-cyan-200/80 font-medium";
      break;
    case "q_and_a":
      styleClasses = "bg-sky-50 text-sky-700 border-sky-200/80 font-medium";
      break;
    case "evaluation":
      styleClasses = "bg-purple-50 text-purple-700 border-purple-200/80 font-medium";
      break;
    case "negotiation":
      styleClasses = "bg-blue-50 text-blue-700 border-blue-200/80 font-medium";
      break;
    case "approved":
    case "awarded":
      styleClasses = "bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold";
      break;
    case "ordered":
      styleClasses = "bg-blue-50 text-blue-700 border-blue-200/80 font-medium";
      break;
    case "partially_ordered":
      styleClasses = "bg-indigo-50 text-indigo-700 border-indigo-200/80 font-medium";
      break;
    case "responded":
      styleClasses = "bg-teal-50 text-teal-700 border-teal-200/80 font-medium";
      break;
    case "shortlisted":
      styleClasses = "bg-amber-50 text-amber-800 border-amber-300 font-medium";
      break;
    case "invited":
      styleClasses = "bg-neutral-50 text-neutral-600 border-neutral-200";
      break;
    case "viewed":
      styleClasses = "bg-blue-50 text-blue-600 border-blue-200";
      break;
    case "declined":
    case "rejected":
    case "cancelled":
      styleClasses = "bg-rose-50 text-rose-700 border-rose-200/80 font-medium";
      break;
    case "sent":
      styleClasses = "bg-sky-50 text-sky-700 border-sky-300 font-medium";
      break;
    case "acknowledged":
      styleClasses = "bg-indigo-50 text-indigo-700 border-indigo-300 font-medium";
      break;
    case "partially_received":
    case "partial":
      styleClasses = "bg-amber-50 text-amber-800 border-amber-300 font-medium";
      break;
    case "received":
    case "confirmed":
      styleClasses = "bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold";
      break;
    case "closed":
      styleClasses = "bg-neutral-100 text-neutral-600 border-neutral-200";
      break;
    case "active":
      styleClasses = "bg-emerald-50 text-emerald-700 border-emerald-200/80 font-medium";
      break;
    case "matched_3way":
      styleClasses = "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold";
      label = "Matched 3-Way";
      break;
    case "matched_2way":
      styleClasses = "bg-teal-50 text-teal-800 border-teal-300 font-medium";
      label = "Matched 2-Way";
      break;
    case "exception":
      styleClasses = "bg-rose-50 text-rose-800 border-rose-300 font-bold";
      label = "Match Exception";
      break;
    case "unmatched":
      styleClasses = "bg-neutral-100 text-neutral-700 border-neutral-300 font-medium";
      label = "Unmatched";
      break;
    case "paid":
      styleClasses = "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold";
      break;
    case "unpaid":
      styleClasses = "bg-neutral-100 text-neutral-600 border-neutral-200 font-medium";
      break;
    case "partially_paid":
      styleClasses = "bg-amber-50 text-amber-800 border-amber-300 font-medium";
      label = "Partially Paid";
      break;
    case "overdue":
      styleClasses = "bg-red-50 text-red-700 border-red-300 font-bold";
      break;
    case "disputed":
      styleClasses = "bg-purple-50 text-purple-700 border-purple-300 font-medium";
      break;
    default:
      styleClasses = "bg-neutral-100 text-neutral-700 border-neutral-200";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono uppercase tracking-wide",
        size === "sm" ? "text-[10px] leading-tight" : "text-xs font-semibold",
        styleClasses,
        className
      )}
    >
      {label}
    </span>
  );
}

interface PriorityBadgeProps {
  priority: string;
  className?: string;
}

export function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  const norm = (priority || "").toLowerCase();
  let styleClasses = "bg-neutral-100 text-neutral-700 border-neutral-200";

  switch (norm) {
    case "critical":
      styleClasses = "bg-red-50 text-red-700 border-red-200 font-bold";
      break;
    case "high":
      styleClasses = "bg-orange-50 text-orange-700 border-orange-200 font-semibold";
      break;
    case "medium":
      styleClasses = "bg-amber-50 text-amber-700 border-amber-200";
      break;
    case "low":
      styleClasses = "bg-neutral-100 text-neutral-600 border-neutral-200";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-mono capitalize",
        styleClasses,
        className
      )}
    >
      {priority}
    </span>
  );
}

interface RFxTypeBadgeProps {
  rfxType: string;
  className?: string;
}

export function RFxTypeBadge({ rfxType, className }: RFxTypeBadgeProps) {
  const norm = (rfxType || "rfq").toLowerCase();
  let styleClasses = "bg-neutral-100 text-neutral-800 border-neutral-300";

  switch (norm) {
    case "rfq":
      styleClasses = "bg-[#FFF2EB] text-[#FA651E] border-[#FA651E]/30 font-semibold";
      break;
    case "rfp":
      styleClasses = "bg-purple-50 text-purple-700 border-purple-200 font-semibold";
      break;
    case "rfi":
      styleClasses = "bg-blue-50 text-blue-700 border-blue-200 font-semibold";
      break;
    case "rft":
      styleClasses = "bg-amber-50 text-amber-800 border-amber-300 font-semibold";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider font-bold",
        styleClasses,
        className
      )}
    >
      {norm}
    </span>
  );
}
