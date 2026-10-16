"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ClipboardList,
  Search,
  Plus,
  Send,
  XCircle,
  ChevronRight,
  Loader2,
  Calendar,
  Building,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DocumentStatusBadge,
  PriorityBadge,
} from "@/components/procurement/document-status-badge";
import { cn } from "@/lib/utils";

export interface MaterialRequestListItem {
  id: string;
  org_id: string;
  mr_number: string;
  title: string;
  status: string;
  requested_by?: string | null;
  required_by_date?: string | null;
  priority?: string | null;
  department?: string | null;
  total_estimated_amount?: number | null;
  currency?: string | null;
  created_at: string;
  line_item_count?: number;
}

interface MaterialRequestListProps {
  items: MaterialRequestListItem[];
  isLoading: boolean;
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  onOpenCreateModal: () => void;
  onSubmitDraft?: (id: string) => void;
  onCancelMR?: (id: string) => void;
}

export function MaterialRequestList({
  items,
  isLoading,
  selectedStatus,
  onSelectStatus,
  onOpenCreateModal,
  onSubmitDraft,
  onCancelMR,
}: MaterialRequestListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const statusTabs = [
    { label: "All", value: "all" },
    { label: "Draft", value: "draft" },
    { label: "Pending Approval", value: "pending_approval" },
    { label: "Approved", value: "approved" },
    { label: "Ordered", value: "ordered" },
    { label: "Cancelled", value: "cancelled" },
  ];

  const filteredItems = items.filter((item) => {
    if (selectedStatus !== "all" && item.status !== selectedStatus) {
      return false;
    }
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchNum = item.mr_number.toLowerCase().includes(q);
      const matchTitle = item.title.toLowerCase().includes(q);
      const matchDept = (item.department || "").toLowerCase().includes(q);
      return matchNum || matchTitle || matchDept;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Top Filter and Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => onSelectStatus(tab.value)}
              className={cn(
                "rounded-lg px-2.5 py-1 text-xs font-medium transition-colors whitespace-nowrap",
                selectedStatus === tab.value
                  ? "bg-neutral-900 text-white font-semibold shadow-2xs"
                  : "bg-neutral-100/80 text-neutral-600 hover:bg-neutral-200/70 hover:text-neutral-900"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Create Button */}
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-neutral-400" />
            <Input
              type="text"
              placeholder="Search by MR# or title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 pl-8 text-xs bg-white"
            />
          </div>
          <Button
            size="sm"
            onClick={onOpenCreateModal}
            className="h-8 shrink-0 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs font-medium"
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            New Request
          </Button>
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-xl border border-neutral-200/80 bg-white overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-center text-neutral-400">
            <Loader2 className="h-6 w-6 animate-spin text-[#FA651E] mb-2" />
            <span className="text-xs">Loading material requests from registry...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-50 text-[#FA651E] mb-3">
              <ClipboardList className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-neutral-900">No Material Requests Found</h3>
            <p className="mt-1 max-w-sm text-xs text-neutral-500">
              {searchTerm || selectedStatus !== "all"
                ? "No material requests match the selected filters."
                : "No requisitions have been created yet. Create your first request or instruct the AI Copilot in Agent Trace."}
            </p>
            {!searchTerm && selectedStatus === "all" && (
              <Button
                size="sm"
                onClick={onOpenCreateModal}
                className="mt-4 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Create First Requisition
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-neutral-200/80 bg-neutral-50/80 text-neutral-500 font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 font-semibold">MR Number</th>
                  <th className="px-4 py-3 font-semibold">Title &amp; Department</th>
                  <th className="px-3 py-3 font-semibold">Status</th>
                  <th className="px-3 py-3 font-semibold">Priority</th>
                  <th className="px-3 py-3 font-semibold">Required Date</th>
                  <th className="px-4 py-3 font-semibold text-right">Est. Amount</th>
                  <th className="px-4 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {filteredItems.map((mr) => (
                  <tr
                    key={mr.id}
                    className="hover:bg-neutral-50/60 transition-colors group"
                  >
                    <td className="px-4 py-3 font-mono font-bold text-neutral-900">
                      <Link
                        href={`/material-requests/${mr.id}`}
                        className="text-[#FA651E] hover:underline"
                      >
                        {mr.mr_number}
                      </Link>
                    </td>

                    <td className="px-4 py-3">
                      <Link
                        href={`/material-requests/${mr.id}`}
                        className="font-medium text-neutral-900 hover:text-[#FA651E] transition-colors block line-clamp-1"
                      >
                        {mr.title}
                      </Link>
                      {mr.department && (
                        <span className="text-[11px] text-neutral-400 flex items-center gap-1 mt-0.5">
                          <Building className="h-3 w-3" />
                          {mr.department}
                        </span>
                      )}
                    </td>

                    <td className="px-3 py-3">
                      <DocumentStatusBadge status={mr.status} size="sm" />
                    </td>

                    <td className="px-3 py-3">
                      <PriorityBadge priority={mr.priority || "medium"} />
                    </td>

                    <td className="px-3 py-3 text-neutral-600 font-mono text-[11px]">
                      {mr.required_by_date ? (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-neutral-400" />
                          {mr.required_by_date}
                        </span>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>

                    <td className="px-4 py-3 text-right font-mono font-semibold text-neutral-900">
                      {mr.currency || "USD"}{" "}
                      {Number(mr.total_estimated_amount || 0).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>

                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {mr.status === "draft" && onSubmitDraft && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onSubmitDraft(mr.id)}
                            className="h-7 px-2 text-[11px] text-amber-700 border-amber-200 hover:bg-amber-50"
                            title="Submit for Approval"
                          >
                            <Send className="mr-1 h-3 w-3" />
                            Submit
                          </Button>
                        )}
                        {(mr.status === "draft" || mr.status === "pending_approval") && onCancelMR && (
                          <button
                            type="button"
                            onClick={() => onCancelMR(mr.id)}
                            className="text-neutral-400 hover:text-rose-600 p-1 rounded"
                            title="Cancel Requisition"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <Link
                          href={`/material-requests/${mr.id}`}
                          className="p-1 text-neutral-400 hover:text-neutral-900 rounded"
                          title="View Details"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
