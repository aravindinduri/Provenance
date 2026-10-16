"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ShoppingCart,
  Search,
  Plus,
  ChevronRight,
  Loader2,
  Calendar,
  Building2,
  DollarSign,
  PackageCheck,
  Send,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { cn } from "@/lib/utils";

export interface PurchaseOrderListItem {
  id: string;
  org_id: string;
  po_number: string;
  company_id?: string | null;
  company_name?: string | null;
  contract_id?: string | null;
  material_request_id?: string | null;
  rfx_event_id?: string | null;
  rfx_response_id?: string | null;
  order_date?: string | null;
  expected_delivery_date?: string | null;
  total_amount: number;
  currency: string;
  line_items: any[];
  status: string;
  approved_by?: string | null;
  approved_at?: string | null;
  sent_at?: string | null;
  acknowledged_at?: string | null;
  payment_terms?: string | null;
  delivery_terms?: string | null;
  notes?: string | null;
  created_at: string;
  receipt_count: number;
}

interface PurchaseOrderListProps {
  items: PurchaseOrderListItem[];
  isLoading: boolean;
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  onCreateClick: () => void;
  onRefresh: () => void;
}

export function PurchaseOrderList({
  items,
  isLoading,
  selectedStatus,
  onSelectStatus,
  onCreateClick,
  onRefresh,
}: PurchaseOrderListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const statusTabs = [
    { label: "All Orders", value: "all" },
    { label: "Draft", value: "draft" },
    { label: "Pending Approval", value: "pending_approval" },
    { label: "Approved", value: "approved" },
    { label: "Sent / Out", value: "sent" },
    { label: "Acknowledged", value: "acknowledged" },
    { label: "Received", value: "received" },
    { label: "Closed", value: "closed" },
  ];

  const filteredItems = items.filter((po) => {
    const matchesStatus =
      selectedStatus === "all" ||
      po.status.toLowerCase() === selectedStatus.toLowerCase();

    if (!matchesStatus) return false;

    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const matchesNumber = po.po_number.toLowerCase().includes(term);
    const matchesVendor = (po.company_name || "").toLowerCase().includes(term);
    const matchesNotes = (po.notes || "").toLowerCase().includes(term);

    return matchesNumber || matchesVendor || matchesNotes;
  });

  // Dynamically compute KPIs from live items
  const totalSpend = items.reduce((acc, po) => acc + (po.total_amount || 0), 0);
  const activeOrdersCount = items.filter(
    (po) => !["closed", "cancelled", "draft"].includes(po.status.toLowerCase())
  ).length;
  const pendingReceiptCount = items.filter((po) =>
    ["approved", "sent", "acknowledged", "partially_received"].includes(
      po.status.toLowerCase()
    )
  ).length;

  return (
    <div className="space-y-6">
      {/* Dynamic Metric Highlights */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md transition-all hover:border-neutral-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Total Purchase Orders
            </span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
              <ShoppingCart className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {items.length}
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Across active procurement operations
          </p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md transition-all hover:border-neutral-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Total Committed Spend
            </span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            ${totalSpend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Aggregated PO contract value
          </p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md transition-all hover:border-neutral-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Active Fulfillment
            </span>
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {activeOrdersCount}
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Orders in approval, transit or delivery
          </p>
        </div>

        <div className="rounded-xl border border-neutral-200/80 bg-white/70 p-4 shadow-sm backdrop-blur-md transition-all hover:border-neutral-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">
              Awaiting Receipts
            </span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
              <PackageCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-neutral-900">
            {pendingReceiptCount}
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Receivable against incoming dock GRNs
          </p>
        </div>
      </div>

      {/* Control Bar: Filter Tabs & Search & Create Action */}
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
              placeholder="Search by PO #, vendor, notes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 text-xs bg-white/80 border-neutral-200"
            />
          </div>

          <Button
            onClick={onCreateClick}
            className="flex items-center gap-1.5 bg-neutral-900 text-xs font-medium text-white hover:bg-neutral-800 shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            New Purchase Order
          </Button>
        </div>
      </div>

      {/* Orders Table Container */}
      <div className="rounded-xl border border-neutral-200/80 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-neutral-500">
            <Loader2 className="h-8 w-8 animate-spin text-neutral-400 mb-3" />
            <p className="text-sm font-medium">Loading purchase orders...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="rounded-full bg-neutral-100 p-3 mb-3 text-neutral-400">
              <ShoppingCart className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-neutral-800">No purchase orders found</h3>
            <p className="mt-1 text-xs text-neutral-500 max-w-sm">
              {searchTerm || selectedStatus !== "all"
                ? "No purchase orders match your filter criteria. Try clearing the search or status filter."
                : "No purchase orders have been created yet. Generate a purchase order via Agent Trace or click 'New Purchase Order'."}
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
                className="mt-4 text-xs bg-neutral-900 text-white hover:bg-neutral-800"
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Create Purchase Order
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50/70 font-semibold text-neutral-600">
                  <th className="py-3 px-4">PO Number</th>
                  <th className="py-3 px-4">Supplier</th>
                  <th className="py-3 px-4">Order Date</th>
                  <th className="py-3 px-4">Expected Delivery</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Receipts</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 font-normal">
                {filteredItems.map((po) => {
                  // Compute fulfillment stats
                  const lines = po.line_items || [];
                  const totalOrdered = lines.reduce(
                    (acc, l) => acc + (floatOrZero(l.quantity)),
                    0
                  );
                  const totalReceived = lines.reduce(
                    (acc, l) => acc + (floatOrZero(l.qty_received)),
                    0
                  );
                  const percentReceived =
                    totalOrdered > 0
                      ? Math.min(100, Math.round((totalReceived / totalOrdered) * 100))
                      : 0;

                  return (
                    <tr
                      key={po.id}
                      className="transition-colors hover:bg-neutral-50/70 group"
                    >
                      <td className="py-3.5 px-4 font-mono font-semibold text-neutral-900">
                        <Link
                          href={`/purchase-orders/${po.id}`}
                          className="hover:underline flex items-center gap-1.5 text-blue-600"
                        >
                          {po.po_number}
                        </Link>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5 font-medium text-neutral-800">
                          <Building2 className="h-3.5 w-3.5 text-neutral-400 shrink-0" />
                          <span className="truncate max-w-[180px]">
                            {po.company_name || "Unassigned Vendor"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600">
                        {po.order_date || po.created_at.slice(0, 10)}
                      </td>
                      <td className="py-3.5 px-4 text-neutral-600">
                        {po.expected_delivery_date ? (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-neutral-400" />
                            {po.expected_delivery_date}
                          </span>
                        ) : (
                          <span className="text-neutral-400 italic">Not set</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold text-neutral-900">
                        {po.currency} {po.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-4">
                        <DocumentStatusBadge status={po.status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col gap-1 w-28">
                          <div className="flex justify-between text-[10px] text-neutral-500 font-mono">
                            <span>{po.receipt_count} GRN(s)</span>
                            <span>{percentReceived}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-neutral-100 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                "h-full transition-all duration-300",
                                percentReceived >= 100
                                  ? "bg-emerald-500"
                                  : percentReceived > 0
                                  ? "bg-amber-500"
                                  : "bg-neutral-300"
                              )}
                              style={{ width: `${percentReceived}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/purchase-orders/${po.id}`}
                          className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100 transition-colors"
                        >
                          View
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
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

function floatOrZero(val: any): number {
  const n = parseFloat(val);
  return isNaN(n) ? 0 : n;
}
