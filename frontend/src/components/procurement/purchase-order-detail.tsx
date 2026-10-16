"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ShoppingCart,
  Building2,
  Calendar,
  DollarSign,
  PackageCheck,
  Send,
  CheckCircle2,
  Clock,
  ChevronLeft,
  Loader2,
  FileText,
  MapPin,
  ShieldCheck,
  AlertCircle,
  Truck,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { GoodsReceiptModal } from "@/components/procurement/goods-receipt-modal";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

export interface PODetailItem {
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
  delivery_address?: any | null;
  payment_terms?: string | null;
  delivery_terms?: string | null;
  notes?: string | null;
  created_at: string;
  receipt_count: number;
  receipts: any[];
}

interface PurchaseOrderDetailProps {
  po: PODetailItem;
  onRefresh: () => void;
}

export function PurchaseOrderDetail({ po, onRefresh }: PurchaseOrderDetailProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [isActing, setIsActing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);

  // Lifecycle steps
  const steps = [
    { key: "draft", label: "Draft" },
    { key: "pending_approval", label: "Approval" },
    { key: "approved", label: "Approved" },
    { key: "sent", label: "Dispatched" },
    { key: "acknowledged", label: "Acknowledged" },
    { key: "receipts", label: "Goods Receipt" },
    { key: "closed", label: "Closed" },
  ];

  const getStepIndex = (status: string) => {
    switch (status.toLowerCase()) {
      case "draft":
        return 0;
      case "pending_approval":
        return 1;
      case "approved":
        return 2;
      case "sent":
        return 3;
      case "acknowledged":
        return 4;
      case "partially_received":
      case "received":
        return 5;
      case "closed":
        return 6;
      default:
        return 0;
    }
  };

  const currentStepIdx = getStepIndex(po.status);

  const executeAction = async (endpoint: string, payload: any = {}) => {
    setIsActing(true);
    setErrorMessage(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/purchase-orders/${po.id}/${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Failed to execute ${endpoint}.`);
      }

      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message || "Action failed.");
    } finally {
      setIsActing(false);
    }
  };

  // Compute fulfillment
  const lines = po.line_items || [];
  const totalOrdered = lines.reduce((acc, l) => acc + (parseFloat(l.quantity) || 0), 0);
  const totalReceived = lines.reduce((acc, l) => acc + (parseFloat(l.qty_received) || 0), 0);
  const totalRejected = lines.reduce((acc, l) => acc + (parseFloat(l.qty_rejected) || 0), 0);
  const percentFulfilled =
    totalOrdered > 0 ? Math.min(100, Math.round((totalReceived / totalOrdered) * 100)) : 0;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/purchase-orders"
            className="rounded-lg border border-neutral-200 bg-white p-2 text-neutral-600 hover:bg-neutral-50 transition-colors shadow-sm"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold font-mono text-neutral-900 tracking-tight">
                {po.po_number}
              </h1>
              <DocumentStatusBadge status={po.status} />
            </div>
            <p className="text-xs text-neutral-500 mt-0.5 flex items-center gap-2">
              <span>Vendor: <strong className="text-neutral-800">{po.company_name || "Unassigned"}</strong></span>
              <span>•</span>
              <span>Issued on {po.order_date || po.created_at.slice(0, 10)}</span>
            </p>
          </div>
        </div>

        {/* Dynamic Action Buttons based on status */}
        <div className="flex items-center gap-2 flex-wrap">
          {po.status === "draft" && (
            <Button
              onClick={() => executeAction("submit")}
              disabled={isActing}
              className="bg-neutral-900 text-white hover:bg-neutral-800 text-xs shadow-sm"
            >
              {isActing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />}
              Submit for Approval
            </Button>
          )}

          {po.status === "pending_approval" && (
            <Button
              onClick={() => executeAction("approve")}
              disabled={isActing}
              className="bg-emerald-600 text-white hover:bg-emerald-700 text-xs shadow-sm"
            >
              {isActing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
              Approve Order
            </Button>
          )}

          {po.status === "approved" && (
            <Button
              onClick={() => executeAction("send")}
              disabled={isActing}
              className="bg-blue-600 text-white hover:bg-blue-700 text-xs shadow-sm"
            >
              {isActing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Send className="h-3.5 w-3.5 mr-1.5" />}
              Mark Sent to Vendor
            </Button>
          )}

          {po.status === "sent" && (
            <Button
              onClick={() => executeAction("acknowledge")}
              disabled={isActing}
              className="bg-indigo-600 text-white hover:bg-indigo-700 text-xs shadow-sm"
            >
              {isActing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
              Mark Acknowledged
            </Button>
          )}

          {["approved", "sent", "acknowledged", "partially_received"].includes(po.status) && (
            <Button
              onClick={() => setIsReceiptModalOpen(true)}
              className="bg-emerald-700 text-white hover:bg-emerald-800 text-xs shadow-sm flex items-center gap-1.5"
            >
              <PackageCheck className="h-3.5 w-3.5" />
              Record Goods Receipt
            </Button>
          )}

          {["partially_received", "received"].includes(po.status) && (
            <Button
              variant="outline"
              onClick={() => executeAction("close")}
              disabled={isActing}
              className="text-xs border-neutral-300 text-neutral-700 hover:bg-neutral-100"
            >
              Close PO
            </Button>
          )}

          {!["closed", "cancelled"].includes(po.status) && (
            <Button
              variant="outline"
              onClick={() => executeAction("cancel", { reason: "Cancelled by buyer" })}
              disabled={isActing}
              className="text-xs border-rose-200 text-rose-600 hover:bg-rose-50"
            >
              Cancel Order
            </Button>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-700 border border-rose-200">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Lifecycle Stepper Track */}
      <div className="rounded-2xl border border-neutral-200/80 bg-white/70 p-5 shadow-sm backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">
            Procure-to-Receipt Lifecycle
          </span>
          <span className="text-xs font-mono font-semibold text-neutral-700">
            Fulfillment: {percentFulfilled}% Completed
          </span>
        </div>

        <div className="relative flex items-center justify-between">
          <div className="absolute top-1/2 left-0 w-full -translate-y-1/2 h-1 bg-neutral-100 -z-0" />
          <div
            className="absolute top-1/2 left-0 -translate-y-1/2 h-1 bg-neutral-900 transition-all duration-500 -z-0"
            style={{ width: `${(currentStepIdx / (steps.length - 1)) * 100}%` }}
          />

          {steps.map((st, i) => {
            const isDone = i < currentStepIdx;
            const isCurrent = i === currentStepIdx;
            return (
              <div key={st.key} className="relative z-10 flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-all shadow-sm",
                    isDone
                      ? "bg-neutral-900 text-white"
                      : isCurrent
                      ? "bg-blue-600 text-white ring-4 ring-blue-100"
                      : "bg-white border-2 border-neutral-200 text-neutral-400"
                  )}
                >
                  {isDone ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                </div>
                <span
                  className={cn(
                    "mt-2 text-[11px] font-medium whitespace-nowrap",
                    isCurrent ? "text-neutral-900 font-bold" : isDone ? "text-neutral-700" : "text-neutral-400"
                  )}
                >
                  {st.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Specification & Terms Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-medium text-neutral-500 mb-1">
            <DollarSign className="h-4 w-4 text-emerald-600" />
            <span>Total Value</span>
          </div>
          <div className="text-xl font-bold font-mono text-neutral-900">
            ${po.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {po.currency}
          </div>
          <p className="text-[11px] text-neutral-400 mt-1">Confirmed purchase commitment</p>
        </div>

        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-medium text-neutral-500 mb-1">
            <FileText className="h-4 w-4 text-blue-600" />
            <span>Commercial Terms</span>
          </div>
          <div className="text-sm font-semibold text-neutral-800">
            {po.payment_terms || "Net 30"}
          </div>
          <p className="text-[11px] text-neutral-400 mt-1">Incoterms: {po.delivery_terms || "FOB Destination"}</p>
        </div>

        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-medium text-neutral-500 mb-1">
            <Calendar className="h-4 w-4 text-indigo-600" />
            <span>Delivery Schedule</span>
          </div>
          <div className="text-sm font-semibold text-neutral-800">
            {po.expected_delivery_date || "Standard Schedule"}
          </div>
          <p className="text-[11px] text-neutral-400 mt-1">
            {po.sent_at ? `Dispatched ${po.sent_at.slice(0, 10)}` : "Pending supplier dispatch"}
          </p>
        </div>

        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-medium text-neutral-500 mb-1">
            <MapPin className="h-4 w-4 text-rose-600" />
            <span>Receiving Destination</span>
          </div>
          <div className="text-xs font-medium text-neutral-800 truncate">
            {po.delivery_address
              ? `${po.delivery_address.street || ""}, ${po.delivery_address.city || ""}`
              : "Main Operations Facility"}
          </div>
          <p className="text-[11px] text-neutral-400 mt-1">
            {po.delivery_address?.country || "Default Receiving Dock"}
          </p>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-neutral-200 bg-neutral-50/70 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-4 w-4 text-neutral-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-800">
              Purchased Line Items & Specifications
            </h2>
          </div>
          <span className="text-xs text-neutral-500 font-mono">
            {lines.length} Line(s)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50/40 font-semibold text-neutral-600">
                <th className="py-2.5 px-4 w-12">#</th>
                <th className="py-2.5 px-4">Item & Description</th>
                <th className="py-2.5 px-4">Unit Price</th>
                <th className="py-2.5 px-4">Ordered Qty</th>
                <th className="py-2.5 px-4">Received</th>
                <th className="py-2.5 px-4">Rejected</th>
                <th className="py-2.5 px-4">Total</th>
                <th className="py-2.5 px-4 text-right">Fulfillment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {lines.map((item: any, idx: number) => {
                const ordered = parseFloat(item.quantity) || 0;
                const received = parseFloat(item.qty_received) || 0;
                const rejected = parseFloat(item.qty_rejected) || 0;
                const unitPrice = parseFloat(item.unit_price) || 0;
                const lineTotal = parseFloat(item.total_price) || ordered * unitPrice;
                const itemPercent = ordered > 0 ? Math.min(100, Math.round((received / ordered) * 100)) : 0;

                return (
                  <tr key={idx} className="hover:bg-neutral-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono text-neutral-400">{idx + 1}</td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-neutral-900">{item.description}</div>
                      {item.item_code && (
                        <span className="text-[10px] font-mono text-neutral-400">
                          SKU: {item.item_code}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-neutral-700">
                      ${unitPrice.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-neutral-900">
                      {ordered.toLocaleString()} {item.unit_of_measure || "each"}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-emerald-700">
                      {received.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-rose-600">
                      {rejected > 0 ? rejected.toLocaleString() : "0"}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-neutral-900">
                      ${lineTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-semibold",
                          itemPercent >= 100
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : itemPercent > 0
                            ? "bg-amber-50 text-amber-800 border border-amber-200"
                            : "bg-neutral-100 text-neutral-600 border border-neutral-200"
                        )}
                      >
                        {itemPercent}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Goods Receipts (GRN) History Section */}
      <div className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-neutral-200 bg-neutral-50/70 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PackageCheck className="h-4 w-4 text-neutral-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-800">
              Goods Receipt Notes (GRN) History
            </h2>
          </div>
          {["approved", "sent", "acknowledged", "partially_received"].includes(po.status) && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsReceiptModalOpen(true)}
              className="h-7 text-xs border-neutral-300 text-neutral-700 hover:bg-neutral-100"
            >
              <Plus className="h-3 w-3 mr-1" />
              New Receipt Note
            </Button>
          )}
        </div>

        {po.receipts && po.receipts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50/40 font-semibold text-neutral-600">
                  <th className="py-2.5 px-4">GRN Number</th>
                  <th className="py-2.5 px-4">Receipt Date</th>
                  <th className="py-2.5 px-4">Received By</th>
                  <th className="py-2.5 px-4">Delivery Note Ref</th>
                  <th className="py-2.5 px-4">Carrier</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4 text-right">Items Verified</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {po.receipts.map((grn: any) => (
                  <tr key={grn.id} className="hover:bg-neutral-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-neutral-900">
                      {grn.grn_number}
                    </td>
                    <td className="py-3 px-4 text-neutral-600">{grn.received_date}</td>
                    <td className="py-3 px-4 text-neutral-800 font-medium">
                      {grn.received_by || "Receiving Clerk"}
                    </td>
                    <td className="py-3 px-4 font-mono text-neutral-700">
                      {grn.delivery_note_ref || "None"}
                    </td>
                    <td className="py-3 px-4 text-neutral-600">{grn.carrier || "Standard Freight"}</td>
                    <td className="py-3 px-4">
                      <DocumentStatusBadge status={grn.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-medium text-neutral-900">
                      {(grn.line_items || []).length} lines
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-10 text-center text-xs text-neutral-500">
            <p>No goods receipts recorded against this order yet.</p>
            {["approved", "sent", "acknowledged"].includes(po.status) && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsReceiptModalOpen(true)}
                className="mt-3 text-xs"
              >
                <PackageCheck className="h-3.5 w-3.5 mr-1" />
                Record First Receipt
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Modal for recording goods receipt */}
      <GoodsReceiptModal
        isOpen={isReceiptModalOpen}
        onClose={() => setIsReceiptModalOpen(false)}
        onSuccess={() => {
          setIsReceiptModalOpen(false);
          onRefresh();
        }}
        preselectedPOId={po.id}
        preselectedPONumber={po.po_number}
        preselectedLines={po.line_items}
      />
    </div>
  );
}
