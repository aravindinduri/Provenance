"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Receipt,
  Search,
  Plus,
  Loader2,
  Calendar,
  Building2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShoppingCart,
  ChevronRight,
  PackageCheck,
  CreditCard,
  DollarSign,
  Filter,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { cn } from "@/lib/utils";

export interface InvoiceListItem {
  id: string;
  org_id: string;
  invoice_number: string;
  company_id?: string | null;
  supplier_name?: string | null;
  po_id?: string | null;
  po_number?: string | null;
  goods_receipt_id?: string | null;
  grn_number?: string | null;
  invoice_date?: string | null;
  due_date?: string | null;
  amount: number;
  currency: string;
  category?: string | null;
  payment_status: string;
  match_status: string;
  match_exceptions: any[];
  approved_by?: string | null;
  created_at: string;
}

export interface InvoiceStats {
  total_count: number;
  total_amount: number;
  matched_3way_count: number;
  matched_2way_count: number;
  exception_count: number;
  unmatched_count: number;
  paid_count: number;
  unpaid_count: number;
  paid_amount: number;
}

interface InvoiceListProps {
  items: InvoiceListItem[];
  stats: InvoiceStats | null;
  isLoading: boolean;
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  onCreateClick: () => void;
  onRefresh: () => void;
}

export function InvoiceList({
  items,
  stats,
  isLoading,
  selectedStatus,
  onSelectStatus,
  onCreateClick,
  onRefresh,
}: InvoiceListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const statusTabs = [
    { label: "All Invoices", value: "all" },
    { label: "Matched 3-Way", value: "matched_3way" },
    { label: "Matched 2-Way", value: "matched_2way" },
    { label: "Exceptions", value: "exception" },
    { label: "Unmatched", value: "unmatched" },
  ];

  // Client-side search filtering
  const filteredItems = items.filter((item) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return (
      item.invoice_number.toLowerCase().includes(q) ||
      (item.supplier_name && item.supplier_name.toLowerCase().includes(q)) ||
      (item.po_number && item.po_number.toLowerCase().includes(q)) ||
      (item.grn_number && item.grn_number.toLowerCase().includes(q)) ||
      (item.category && item.category.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* ── KPI Summary Cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Invoiced */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-neutral-500 mb-2">
            <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
              Total Invoiced
            </span>
            <div className="w-7 h-7 rounded-lg bg-orange-50 text-[#FA651E] flex items-center justify-center">
              <Receipt className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl font-bold font-mono text-neutral-900">
            ${stats ? stats.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
          </div>
          <p className="text-[11px] text-neutral-400 font-mono mt-1">
            {stats ? stats.total_count : 0} total invoices recorded
          </p>
        </div>

        {/* 3-Way Matched */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-neutral-500 mb-2">
            <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
              Matched 3-Way
            </span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl font-bold font-mono text-emerald-700">
            {stats ? stats.matched_3way_count : 0}
          </div>
          <p className="text-[11px] text-neutral-400 font-mono mt-1">
            Verified PO + GRN + Invoice
          </p>
        </div>

        {/* Match Exceptions */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-neutral-500 mb-2">
            <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
              Match Exceptions
            </span>
            <div className="w-7 h-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl font-bold font-mono text-rose-700">
            {stats ? stats.exception_count : 0}
          </div>
          <p className="text-[11px] text-neutral-400 font-mono mt-1">
            Price or quantity variance flagged
          </p>
        </div>

        {/* Paid Volume */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs">
          <div className="flex items-center justify-between text-neutral-500 mb-2">
            <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
              Paid Settlements
            </span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <CreditCard className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl font-bold font-mono text-neutral-900">
            ${stats ? stats.paid_amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
          </div>
          <p className="text-[11px] text-neutral-400 font-mono mt-1">
            {stats ? stats.paid_count : 0} fully paid invoices
          </p>
        </div>
      </div>

      {/* ── Filter Controls & Actions ──────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Status Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {statusTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => onSelectStatus(tab.value)}
              className={cn(
                "px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition-colors whitespace-nowrap",
                selectedStatus === tab.value
                  ? "bg-neutral-900 text-white shadow-2xs font-semibold"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200/70 hover:text-neutral-900"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Intake Button */}
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-neutral-400" />
            <Input
              type="text"
              placeholder="Search invoices, PO, vendor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 text-xs h-9 font-mono"
            />
          </div>

          <Button
            onClick={onCreateClick}
            size="sm"
            className="text-xs font-mono h-9 gap-1.5 bg-[#FA651E] hover:bg-[#E05310] text-white shrink-0 shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5" />
            Log Invoice
          </Button>
        </div>
      </div>

      {/* ── Invoices Data Table ────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-neutral-200/80 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-neutral-50/70 border-b border-neutral-200/80 font-mono text-[11px] text-neutral-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Invoice #</th>
                <th className="py-3 px-4">Supplier</th>
                <th className="py-3 px-3">PO Reference</th>
                <th className="py-3 px-3">GRN Reference</th>
                <th className="py-3 px-3 text-right">Amount</th>
                <th className="py-3 px-3 text-center">Match Status</th>
                <th className="py-3 px-3 text-center">Payment</th>
                <th className="py-3 px-4">Invoice Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-neutral-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto text-[#FA651E] mb-2" />
                    <span>Loading purchase invoices...</span>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-neutral-400">
                    <Receipt className="w-8 h-8 text-neutral-300 mx-auto mb-2" />
                    <p className="text-xs font-semibold text-neutral-700">No Invoices Found</p>
                    <p className="text-[11px] text-neutral-400 mt-1 max-w-sm mx-auto">
                      Log a vendor invoice against an approved purchase order to trigger automated 3-way matching.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={onCreateClick}
                      className="mt-3 text-xs font-mono h-8 border-neutral-300"
                    >
                      Log First Invoice
                    </Button>
                  </td>
                </tr>
              ) : (
                filteredItems.map((inv) => (
                  <tr key={inv.id} className="hover:bg-neutral-50/60 transition-colors">
                    <td className="py-3 px-4 font-bold text-neutral-900">
                      <Link
                        href={`/invoices/${inv.id}`}
                        className="hover:text-[#FA651E] transition-colors flex items-center gap-1.5"
                      >
                        <Receipt className="w-3.5 h-3.5 text-[#FA651E]" />
                        <span>{inv.invoice_number}</span>
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-neutral-800">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
                        <span className="truncate max-w-[150px]">
                          {inv.supplier_name || "Direct Supplier"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      {inv.po_number ? (
                        <Link
                          href={`/purchase-orders/${inv.po_id}`}
                          className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                        >
                          <ShoppingCart className="w-3 h-3 text-blue-500" />
                          <span>{inv.po_number}</span>
                        </Link>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {inv.grn_number ? (
                        <Link
                          href="/receipts"
                          className="text-amber-600 hover:text-amber-800 hover:underline flex items-center gap-1"
                        >
                          <PackageCheck className="w-3 h-3 text-amber-500" />
                          <span>{inv.grn_number}</span>
                        </Link>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-neutral-950">
                      {inv.currency} {Number(inv.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <DocumentStatusBadge status={inv.match_status} size="sm" />
                    </td>
                    <td className="py-3 px-3 text-center">
                      <DocumentStatusBadge status={inv.payment_status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-neutral-500 text-[11px]">
                      {inv.invoice_date || inv.created_at.slice(0, 10)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/invoices/${inv.id}`}
                        className="inline-flex items-center gap-1 text-[11px] text-[#FA651E] hover:text-[#E05310] font-semibold"
                      >
                        <span>Inspect Match</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
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
