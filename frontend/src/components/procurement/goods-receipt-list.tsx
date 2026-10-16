"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  PackageCheck,
  Search,
  Plus,
  Loader2,
  Calendar,
  Building2,
  Truck,
  CheckCircle2,
  Clock,
  ShoppingCart,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { cn } from "@/lib/utils";

export interface GoodsReceiptListItem {
  id: string;
  org_id: string;
  grn_number: string;
  purchase_order_id: string;
  po_number?: string | null;
  supplier_name?: string | null;
  received_date: string;
  received_by?: string | null;
  status: string;
  line_items: any[];
  delivery_note_ref?: string | null;
  carrier?: string | null;
  notes?: string | null;
  created_at: string;
}

interface GoodsReceiptListProps {
  items: GoodsReceiptListItem[];
  isLoading: boolean;
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  onCreateClick: () => void;
  onRefresh: () => void;
}

export function GoodsReceiptList({
  items,
  isLoading,
  selectedStatus,
  onSelectStatus,
  onCreateClick,
  onRefresh,
}: GoodsReceiptListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const statusTabs = [
    { label: "All Receipts", value: "all" },
    { label: "Confirmed", value: "confirmed" },
    { label: "Partial", value: "partial" },
    { label: "Draft", value: "draft" },
  ];

  const filteredItems = items.filter((grn) => {
    const matchesStatus =
      selectedStatus === "all" ||
      grn.status.toLowerCase() === selectedStatus.toLowerCase();

    if (!matchesStatus) return false;

    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const matchGRN = grn.grn_number.toLowerCase().includes(term);
    const matchPO = (grn.po_number || "").toLowerCase().includes(term);
    const matchSupplier = (grn.supplier_name || "").toLowerCase().includes(term);
    const matchRef = (grn.delivery_note_ref || "").toLowerCase().includes(term);
    const matchCarrier = (grn.carrier || "").toLowerCase().includes(term);

    return matchGRN || matchPO || matchSupplier || matchRef || matchCarrier;
  });

  const totalConfirmed = items.filter((g) => g.status === "confirmed").length;
  const totalPartial = items.filter((g) => g.status === "partial").length;
  const totalVerifiedPackages = items.reduce(
    (acc, g) =>
      acc +
      (g.line_items || []).reduce(
        (sum: number, l: any) => sum + (parseFloat(l.qty_received) || 0),
        0
      ),
    0
  );

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Total Goods Receipts
            </span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <PackageCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {items.length}
          </div>
          <p className="mt-1 text-xs text-neutral-500">All registered delivery receipts</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Confirmed Intake
            </span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {totalConfirmed}
          </div>
          <p className="mt-1 text-xs text-neutral-500">Passed dock inspection</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Partial Shipments
            </span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {totalPartial}
          </div>
          <p className="mt-1 text-xs text-neutral-500">Split or multi-drop deliveries</p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Verified Units
            </span>
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Truck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {totalVerifiedPackages.toLocaleString()}
          </div>
          <p className="mt-1 text-xs text-neutral-500">Physical units checked & signed</p>
        </div>
      </div>

      {/* Filter and Action bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => onSelectStatus(tab.value)}
              className={cn(
                "whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                selectedStatus === tab.value
                  ? "bg-neutral-900 text-white shadow-sm"
                  : "bg-white/80 text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 border border-neutral-200"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-400" />
            <Input
              type="text"
              placeholder="Search GRN, PO #, carrier..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 text-xs bg-white/80 border-neutral-200"
            />
          </div>

          <Button
            onClick={onCreateClick}
            className="flex items-center gap-1.5 bg-emerald-700 text-xs font-medium text-white hover:bg-emerald-800 shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            Record Goods Receipt
          </Button>
        </div>
      </div>

      {/* Table container */}
      <div className="rounded-xl border border-neutral-200/80 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-neutral-500">
            <Loader2 className="h-8 w-8 animate-spin text-neutral-400 mb-3" />
            <p className="text-sm font-medium">Loading goods receipts...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="rounded-full bg-neutral-100 p-3 mb-3 text-neutral-400">
              <PackageCheck className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-neutral-800">No goods receipts found</h3>
            <p className="mt-1 text-xs text-neutral-500 max-w-sm">
              {searchTerm || selectedStatus !== "all"
                ? "No receipts match your search filter criteria."
                : "No goods receipt notes have been registered yet. Record a delivery against an approved purchase order."}
            </p>
            {searchTerm || selectedStatus !== "all" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearchTerm("");
                  onSelectStatus("all");
                }}
                className="mt-4 text-xs"
              >
                Clear Filters
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={onCreateClick}
                className="mt-4 text-xs bg-emerald-700 text-white hover:bg-emerald-800"
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Record First Receipt
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50/70 font-semibold text-neutral-600">
                  <th className="py-3 px-4">GRN Number</th>
                  <th className="py-3 px-4">Linked Purchase Order</th>
                  <th className="py-3 px-4">Supplier</th>
                  <th className="py-3 px-4">Receipt Date</th>
                  <th className="py-3 px-4">Received By</th>
                  <th className="py-3 px-4">Delivery Ref / Carrier</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Verified Lines</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 font-normal">
                {filteredItems.map((grn) => {
                  const lineCount = (grn.line_items || []).length;
                  return (
                    <tr
                      key={grn.id}
                      className="transition-colors hover:bg-neutral-50/70 group"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-neutral-900">
                        {grn.grn_number}
                      </td>
                      <td className="py-3.5 px-4">
                        <Link
                          href={`/purchase-orders/${grn.purchase_order_id}`}
                          className="font-mono text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ShoppingCart className="h-3 w-3 text-blue-500" />
                          {grn.po_number || "View PO"}
                        </Link>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5 font-medium text-neutral-800">
                          <Building2 className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
                          <span className="truncate max-w-[180px]">
                            {grn.supplier_name || "Unassigned"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-neutral-400" />
                          {grn.received_date}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-neutral-800 font-medium">
                        {grn.received_by || "Receiving Dock"}
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600">
                        <div>
                          <span className="font-mono font-medium text-neutral-700">
                            {grn.delivery_note_ref || "Standard Intake"}
                          </span>
                          {grn.carrier && (
                            <span className="block text-[10px] text-neutral-400">
                              via {grn.carrier}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <DocumentStatusBadge status={grn.status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-medium text-neutral-900">
                        {lineCount} line(s)
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
