"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileQuestion,
  Search,
  Plus,
  Send,
  ChevronRight,
  Loader2,
  Calendar,
  Building2,
  BarChart3,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DocumentStatusBadge,
  RFxTypeBadge,
} from "@/components/procurement/document-status-badge";
import { cn } from "@/lib/utils";

export interface RFxListItem {
  id: string;
  org_id: string;
  rfx_number: string;
  rfx_type: string;
  title: string;
  description?: string | null;
  status: string;
  material_request_id?: string | null;
  category?: string | null;
  submission_deadline?: string | null;
  published_at?: string | null;
  awarded_at?: string | null;
  awarded_supplier_id?: string | null;
  awarded_supplier_name?: string | null;
  created_at: string;
  total_invitations: number;
  total_responses: number;
}

interface RFxListProps {
  items: RFxListItem[];
  isLoading: boolean;
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  selectedType: string;
  onSelectType: (type: string) => void;
  onPublishDraft?: (id: string) => void;
}

export function RFxList({
  items,
  isLoading,
  selectedStatus,
  onSelectStatus,
  selectedType,
  onSelectType,
  onPublishDraft,
}: RFxListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const statusTabs = [
    { label: "All Events", value: "all" },
    { label: "Draft", value: "draft" },
    { label: "Published", value: "published" },
    { label: "Evaluation", value: "evaluation" },
    { label: "Awarded", value: "awarded" },
    { label: "Closed", value: "closed" },
  ];

  const typeOptions = [
    { label: "All Types", value: "all" },
    { label: "RFQ", value: "rfq" },
    { label: "RFP", value: "rfp" },
    { label: "RFI", value: "rfi" },
    { label: "RFT", value: "rft" },
  ];

  // Dynamically computed metrics from live API response
  const totalEvents = items.length;
  const inEvaluation = items.filter((i) => i.status === "evaluation").length;
  const awardedCount = items.filter((i) => i.status === "awarded").length;
  const totalBidsReceived = items.reduce((acc, curr) => acc + curr.total_responses, 0);

  const filteredItems = items.filter((item) => {
    if (selectedStatus !== "all" && item.status !== selectedStatus) {
      return false;
    }
    if (selectedType !== "all" && item.rfx_type.toLowerCase() !== selectedType.toLowerCase()) {
      return false;
    }
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchNum = item.rfx_number.toLowerCase().includes(q);
      const matchTitle = item.title.toLowerCase().includes(q);
      const matchCat = (item.category || "").toLowerCase().includes(q);
      const matchWinner = (item.awarded_supplier_name || "").toLowerCase().includes(q);
      return matchNum || matchTitle || matchCat || matchWinner;
    }
    return true;
  });

  return (
    <div className="space-y-5">
      {/* Dynamic Live KPI Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-neutral-200/80 bg-white/80 backdrop-blur-md p-3.5 shadow-xs">
          <div className="flex items-center justify-between text-neutral-500">
            <span className="text-[11px] font-medium tracking-wide">Sourcing Events</span>
            <Layers className="h-4 w-4 text-neutral-400" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-neutral-900 tracking-tight">
            {isLoading ? "—" : totalEvents}
          </div>
          <p className="text-[10px] text-neutral-400 mt-0.5">Total registered</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/80 backdrop-blur-md p-3.5 shadow-xs">
          <div className="flex items-center justify-between text-neutral-500">
            <span className="text-[11px] font-medium tracking-wide">In Evaluation</span>
            <Clock className="h-4 w-4 text-purple-500" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-neutral-900 tracking-tight">
            {isLoading ? "—" : inEvaluation}
          </div>
          <p className="text-[10px] text-purple-600 font-medium mt-0.5">Awaiting decision</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/80 backdrop-blur-md p-3.5 shadow-xs">
          <div className="flex items-center justify-between text-neutral-500">
            <span className="text-[11px] font-medium tracking-wide">Awarded</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-neutral-900 tracking-tight">
            {isLoading ? "—" : awardedCount}
          </div>
          <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Winner selected</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/80 backdrop-blur-md p-3.5 shadow-xs">
          <div className="flex items-center justify-between text-neutral-500">
            <span className="text-[11px] font-medium tracking-wide">Quotations Received</span>
            <BarChart3 className="h-4 w-4 text-[#FA651E]" />
          </div>
          <div className="mt-1.5 text-xl font-bold text-neutral-900 tracking-tight">
            {isLoading ? "—" : totalBidsReceived}
          </div>
          <p className="text-[10px] text-neutral-400 mt-0.5">Supplier bids</p>
        </div>
      </div>

      {/* Top Filter and Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
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

        {/* Type Filter & Search Bar */}
        <div className="flex items-center gap-2">
          <select
            value={selectedType}
            onChange={(e) => onSelectType(e.target.value)}
            className="h-8 rounded-lg border border-neutral-200 bg-white px-2.5 text-xs text-neutral-700 focus:outline-none focus:ring-1 focus:ring-neutral-400"
          >
            {typeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
            <Input
              type="text"
              placeholder="Search RFx #, title, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 pl-8 text-xs bg-white/90 border-neutral-200/80 rounded-lg placeholder:text-neutral-400"
            />
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="rounded-xl border border-neutral-200/80 bg-white shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-neutral-50/75 border-b border-neutral-200 text-neutral-600 font-semibold tracking-wider uppercase text-[10px]">
              <tr>
                <th className="py-3 px-4">Event Ref</th>
                <th className="py-3 px-4">Title & Scope</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Deadline</th>
                <th className="py-3 px-4">Vendors</th>
                <th className="py-3 px-4">Quotations</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-neutral-400">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400 mb-2" />
                    <span>Loading sourcing events...</span>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-14 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="h-10 w-10 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400">
                        <FileQuestion className="h-5 w-5" />
                      </div>
                      <span className="text-sm font-medium text-neutral-900">
                        {searchTerm ? "No sourcing events matching search" : "No sourcing events found"}
                      </span>
                      <p className="text-xs text-neutral-500 max-w-sm">
                        {searchTerm
                          ? "Try adjusting your search criteria or status filter."
                          : "Launch an RFQ or RFP to collect supplier bids, compare offers side-by-side, and award contracts."}
                      </p>
                      {!searchTerm && (
                        <Link href="/rfx/create" className="pt-2">
                          <Button
                            size="sm"
                            className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs font-medium"
                          >
                            <Plus className="mr-1.5 h-3.5 w-3.5" />
                            Create First RFx
                          </Button>
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-neutral-50/60 transition-colors group cursor-pointer"
                  >
                    {/* Event Ref */}
                    <td className="py-3.5 px-4 font-mono font-medium text-neutral-900 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <RFxTypeBadge rfxType={item.rfx_type} />
                        <Link
                          href={`/rfx/${item.id}`}
                          className="hover:text-[#FA651E] transition-colors font-semibold"
                        >
                          {item.rfx_number}
                        </Link>
                      </div>
                    </td>

                    {/* Title & Scope */}
                    <td className="py-3.5 px-4 max-w-xs sm:max-w-md">
                      <Link href={`/rfx/${item.id}`} className="block">
                        <div className="font-medium text-neutral-900 truncate hover:text-[#FA651E] transition-colors">
                          {item.title}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-neutral-500">
                          {item.category && (
                            <span className="bg-neutral-100 px-1.5 py-0.2 rounded text-[10px]">
                              {item.category}
                            </span>
                          )}
                          {item.awarded_supplier_name && (
                            <span className="text-emerald-700 font-medium">
                              Awarded: {item.awarded_supplier_name}
                            </span>
                          )}
                        </div>
                      </Link>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <DocumentStatusBadge status={item.status} size="sm" />
                    </td>

                    {/* Deadline */}
                    <td className="py-3.5 px-4 text-neutral-600 whitespace-nowrap">
                      {item.submission_deadline ? (
                        <div className="flex items-center gap-1 text-[11px]">
                          <Calendar className="h-3.5 w-3.5 text-neutral-400" />
                          <span>{item.submission_deadline.slice(0, 10)}</span>
                        </div>
                      ) : (
                        <span className="text-neutral-400 text-[11px]">—</span>
                      )}
                    </td>

                    {/* Vendors Invited */}
                    <td className="py-3.5 px-4 text-neutral-700 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Building2 className="h-3.5 w-3.5 text-neutral-400" />
                        <span className="font-medium">{item.total_invitations}</span>
                        <span className="text-neutral-400 text-[10px]">invited</span>
                      </div>
                    </td>

                    {/* Quotations Received */}
                    <td className="py-3.5 px-4 text-neutral-700 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={cn(
                            "inline-flex items-center justify-center px-1.5 py-0.5 rounded text-[11px] font-bold",
                            item.total_responses > 0
                              ? "bg-purple-50 text-purple-700 border border-purple-200"
                              : "bg-neutral-100 text-neutral-500"
                          )}
                        >
                          {item.total_responses}
                        </span>
                        <span className="text-neutral-400 text-[10px]">bids</span>
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        {item.total_responses > 0 && (
                          <Link href={`/rfx/${item.id}/compare`}>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-[11px] px-2 text-purple-700 border-purple-200 hover:bg-purple-50 font-medium"
                              title="Compare Bids Side-by-Side"
                            >
                              <BarChart3 className="mr-1 h-3 w-3" />
                              Compare Bids
                            </Button>
                          </Link>
                        )}

                        {item.status === "draft" && onPublishDraft && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPublishDraft(item.id);
                            }}
                            className="h-7 text-[11px] px-2 text-cyan-700 border-cyan-200 hover:bg-cyan-50 font-medium"
                            title="Publish RFx Event"
                          >
                            <Send className="mr-1 h-3 w-3" />
                            Publish
                          </Button>
                        )}

                        <Link href={`/rfx/${item.id}`}>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-neutral-400 hover:text-neutral-700"
                          >
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
