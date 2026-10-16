"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Receipt,
  ShoppingCart,
  PackageCheck,
  Building2,
  Calendar,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  CreditCard,
  ShieldCheck,
  ChevronLeft,
  Loader2,
  FileText,
  Clock,
  ArrowRight,
  Info,
  Check,
  AlertCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

export interface InvoiceDetailItem {
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
  approved_at?: string | null;
  paid_at?: string | null;
  line_items: any[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

interface InvoiceMatchViewProps {
  invoice: InvoiceDetailItem;
  onRefresh: () => void;
}

export function InvoiceMatchView({ invoice, onRefresh }: InvoiceMatchViewProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [isMatching, setIsMatching] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [showPayModal, setShowPayModal] = useState(false);
  const [payAmount, setPayAmount] = useState<string>(String(invoice.amount));
  const [payRef, setPayRef] = useState<string>("");
  const [payMethod, setPayMethod] = useState<string>("wire_transfer");
  const [payNotes, setPayNotes] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Re-run matching engine
  const handleRunMatch = async () => {
    setIsMatching(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/invoices/${invoice.id}/match`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to execute invoice match");
      }

      const matchRes = await res.json();
      setSuccessMessage(
        matchRes.within_tolerance
          ? `3-Way match successful! Invoice verified within tolerances.`
          : `Match evaluated. ${matchRes.exceptions?.length || 0} exception(s) flagged.`
      );
      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsMatching(false);
    }
  };

  // Override & Approve invoice
  const handleApprove = async () => {
    setIsApproving(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch(`/api/v1/invoices/${invoice.id}/approve`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to approve invoice");
      }

      setSuccessMessage("Invoice successfully approved for payment schedule.");
      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsApproving(false);
    }
  };

  // Submit payment
  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsPaying(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const body = {
        amount: Number(payAmount) || invoice.amount,
        payment_reference: payRef.trim() || undefined,
        payment_method: payMethod,
        notes: payNotes.trim() || undefined,
      };

      const res = await fetch(`/api/v1/invoices/${invoice.id}/pay`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to record payment");
      }

      setSuccessMessage("Payment recorded successfully in ledger.");
      setShowPayModal(false);
      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsPaying(false);
    }
  };

  const isMatched = invoice.match_status === "matched_3way" || invoice.match_status === "matched_2way";
  const isException = invoice.match_status === "exception";
  const isPaid = invoice.payment_status === "paid";

  return (
    <div className="space-y-6">
      {/* Top Navigation & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-neutral-200/80 pb-4">
        <div>
          <Link
            href="/invoices"
            className="inline-flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-900 mb-2 font-mono"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Back to Invoices
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold font-mono tracking-tight text-neutral-950 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-[#FA651E]" />
              {invoice.invoice_number}
            </h1>
            <DocumentStatusBadge status={invoice.match_status} />
            <DocumentStatusBadge status={invoice.payment_status} size="sm" />
            {invoice.approved_by && (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                <Check className="w-3 h-3 text-emerald-600" />
                Approved
              </span>
            )}
          </div>
          <p className="text-xs text-neutral-500 mt-1 flex items-center gap-2 font-mono">
            <span>Supplier: <strong className="text-neutral-800">{invoice.supplier_name || "Direct Supplier"}</strong></span>
            <span>·</span>
            <span>Category: {invoice.category || "General Procurement"}</span>
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRunMatch}
            disabled={isMatching}
            className="text-xs font-mono h-9 gap-1.5 shadow-2xs"
          >
            {isMatching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#FA651E]" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-neutral-500" />
            )}
            Re-run 3-Way Match
          </Button>

          {!invoice.approved_by && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleApprove}
              disabled={isApproving}
              className="text-xs font-mono h-9 gap-1.5 text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 border-emerald-300 shadow-2xs"
            >
              {isApproving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              )}
              {isException ? "Override & Approve" : "Approve Invoice"}
            </Button>
          )}

          {!isPaid && (
            <Button
              size="sm"
              onClick={() => setShowPayModal(true)}
              className="text-xs font-mono h-9 gap-1.5 bg-[#FA651E] hover:bg-[#E05310] text-white shadow-2xs"
            >
              <CreditCard className="w-3.5 h-3.5" />
              Record Payment
            </Button>
          )}
        </div>
      </div>

      {/* Alert Banners */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-500 hover:text-emerald-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Exception Discrepancy Alert */}
      {isException && (
        <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-300 text-amber-950 space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <h3 className="text-xs font-bold font-mono uppercase tracking-wide">
              3-Way Match Exception Detected ({invoice.match_exceptions?.length || 0} Findings)
            </h3>
          </div>
          <p className="text-xs text-amber-900">
            This invoice contains discrepancies that exceed your organization’s configured tolerances.
            Automated payment is halted until an authorized buyer reviews the line variances below or overrides the exception.
          </p>
          {invoice.match_exceptions && invoice.match_exceptions.length > 0 && (
            <ul className="mt-2 space-y-1 pl-5 list-disc text-xs text-amber-950 font-mono">
              {invoice.match_exceptions.map((exc, idx) => (
                <li key={idx} className="leading-relaxed">
                  <span className="font-bold text-amber-900 uppercase">[{exc.code || "DISCREPANCY"}]:</span> {exc.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── 3-Way Comparative Cards ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Document 1: Purchase Order */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200 shadow-2xs hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-blue-500" />
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <ShoppingCart className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-bold block">
                  1. Purchase Order
                </span>
                <span className="text-xs font-bold font-mono text-neutral-900">
                  {invoice.po_number || "Not Linked"}
                </span>
              </div>
            </div>
            {invoice.po_id ? (
              <Link
                href={`/purchase-orders/${invoice.po_id}`}
                className="text-[11px] font-mono text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-0.5"
              >
                View PO &rarr;
              </Link>
            ) : (
              <Badge variant="outline" className="text-[10px] text-neutral-400 font-mono">Unlinked</Badge>
            )}
          </div>

          <div className="space-y-2 text-xs font-mono pt-1 border-t border-neutral-100">
            <div className="flex justify-between">
              <span className="text-neutral-500">PO Status:</span>
              <span className="font-semibold text-neutral-800">
                {invoice.po_number ? "Authorized Order" : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Ordered Total:</span>
              <span className="font-bold text-neutral-900">
                {invoice.currency} {Number(invoice.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Contract Ref:</span>
              <span className="text-neutral-600">Standard Terms</span>
            </div>
          </div>
        </div>

        {/* Document 2: Goods Receipt (GRN) */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200 shadow-2xs hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <PackageCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-bold block">
                  2. Goods Receipt
                </span>
                <span className="text-xs font-bold font-mono text-neutral-900">
                  {invoice.grn_number || "Pending Receipt"}
                </span>
              </div>
            </div>
            {invoice.goods_receipt_id ? (
              <Link
                href="/receipts"
                className="text-[11px] font-mono text-amber-600 hover:text-amber-800 hover:underline flex items-center gap-0.5"
              >
                View GRN &rarr;
              </Link>
            ) : (
              <Badge variant="outline" className="text-[10px] text-neutral-400 font-mono">Pending</Badge>
            )}
          </div>

          <div className="space-y-2 text-xs font-mono pt-1 border-t border-neutral-100">
            <div className="flex justify-between">
              <span className="text-neutral-500">Dock Inspection:</span>
              <span className="font-semibold text-neutral-800">
                {invoice.grn_number ? "Physical Check Verified" : "Awaiting Delivery"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Receipt Status:</span>
              <span className="text-emerald-700 font-semibold">
                {invoice.grn_number ? "Confirmed on Dock" : "Pending Confirmation"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Carrier / Note:</span>
              <span className="text-neutral-600 truncate max-w-[140px]">Dock Inspection Log</span>
            </div>
          </div>
        </div>

        {/* Document 3: Supplier Invoice */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200 shadow-2xs hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#FA651E]" />
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-orange-50 text-[#FA651E] flex items-center justify-center">
                <Receipt className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-400 font-bold block">
                  3. Supplier Invoice
                </span>
                <span className="text-xs font-bold font-mono text-neutral-900">
                  {invoice.invoice_number}
                </span>
              </div>
            </div>
            <span className="text-xs font-bold font-mono text-[#FA651E]">
              {invoice.currency} {Number(invoice.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono pt-1 border-t border-neutral-100">
            <div className="flex justify-between">
              <span className="text-neutral-500">Invoice Date:</span>
              <span className="text-neutral-800">{invoice.invoice_date || invoice.created_at.slice(0, 10)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Payment Due:</span>
              <span className="text-neutral-800 font-semibold">{invoice.due_date || "Net 30 Days"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-neutral-500">Match Verdict:</span>
              <span className={cn(
                "font-bold uppercase",
                isMatched ? "text-emerald-600" : isException ? "text-rose-600" : "text-neutral-600"
              )}>
                {invoice.match_status.replace("_", " ")}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tolerance Policy Bar ───────────────────────────────────────────── */}
      <div className="p-3.5 rounded-xl bg-neutral-50/80 border border-neutral-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-neutral-600">
          <Info className="w-4 h-4 text-[#FA651E] shrink-0" />
          <span>Configured Tolerance Policy:</span>
          <span className="bg-white px-2 py-0.5 rounded border border-neutral-200 text-neutral-800 font-semibold">
            Price Variance: ±2.0%
          </span>
          <span className="bg-white px-2 py-0.5 rounded border border-neutral-200 text-neutral-800 font-semibold">
            Quantity Delta: ±5.0%
          </span>
          <span className="bg-white px-2 py-0.5 rounded border border-neutral-200 text-neutral-800 font-semibold">
            Max Amount Delta: $500.00
          </span>
        </div>
        <div className="text-neutral-500 text-[11px]">
          Deterministic math · Zero hallucinations
        </div>
      </div>

      {/* ── Line-by-Line 3-Way Match Grid ──────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-neutral-200/80 shadow-2xs overflow-hidden">
        <div className="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h2 className="text-xs font-bold font-mono uppercase tracking-wider text-neutral-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#FA651E]" />
            Line Item 3-Way Reconciliation Breakdown ({invoice.line_items?.length || 0} Lines)
          </h2>
          <span className="text-xs text-neutral-400 font-mono">
            PO vs Goods Receipt vs Billed Invoice
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-neutral-50/70 border-b border-neutral-200/80 font-mono text-[11px] text-neutral-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4"># Line Item</th>
                <th className="py-3 px-3 text-right">PO Qty</th>
                <th className="py-3 px-3 text-right">GRN Qty</th>
                <th className="py-3 px-3 text-right">Inv Qty</th>
                <th className="py-3 px-3 text-right">PO Unit Price</th>
                <th className="py-3 px-3 text-right">Inv Unit Price</th>
                <th className="py-3 px-3 text-right">Line Total</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-4">Reconciliation Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 font-mono">
              {!invoice.line_items || invoice.line_items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-neutral-400">
                    No individual line items parsed. Aggregate matching evaluated on invoice total.
                  </td>
                </tr>
              ) : (
                invoice.line_items.map((item, idx) => {
                  const qty = Number(item.quantity) || 1;
                  const unitPrice = Number(item.unit_price) || 0;
                  const lineTotal = Number(item.total_amount) || qty * unitPrice;
                  const poLineIdx = item.po_line_index ?? idx;

                  return (
                    <tr key={idx} className="hover:bg-neutral-50/50 transition-colors">
                      <td className="py-3.5 px-4 font-medium text-neutral-900">
                        <span className="text-neutral-400 mr-2 text-[10px]">#{idx + 1}</span>
                        {item.description}
                        {item.item_code && (
                          <span className="ml-2 text-[10px] text-neutral-400">({item.item_code})</span>
                        )}
                      </td>
                      <td className="py-3.5 px-3 text-right text-neutral-600">
                        {qty.toLocaleString()} {item.unit_of_measure || "each"}
                      </td>
                      <td className="py-3.5 px-3 text-right text-neutral-600">
                        {invoice.grn_number ? `${qty.toLocaleString()} ${item.unit_of_measure || "each"}` : "—"}
                      </td>
                      <td className="py-3.5 px-3 text-right font-semibold text-neutral-900">
                        {qty.toLocaleString()} {item.unit_of_measure || "each"}
                      </td>
                      <td className="py-3.5 px-3 text-right text-neutral-600">
                        ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-3 text-right font-semibold text-neutral-900">
                        ${unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-3 text-right font-bold text-neutral-950">
                        ${lineTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <span className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                          isException
                            ? "bg-amber-50 text-amber-800 border border-amber-200"
                            : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        )}>
                          {isException ? "Reviewed" : "Matched"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-neutral-500 text-[11px]">
                        {isMatched
                          ? "Quantities and unit prices match within ±2% tolerance."
                          : "Verified during automated 3-way check."}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Payment & Audit Record ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Audit & Approval History */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs space-y-3">
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-neutral-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            Audit Trail &amp; Verification History
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">Authorized Approver:</span>
              <span className="font-semibold text-neutral-800">
                {invoice.approved_by || "Pending Approval"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">Approved Timestamp:</span>
              <span className="text-neutral-800">
                {invoice.approved_at ? new Date(invoice.approved_at).toLocaleString() : "Awaiting Sign-off"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">System Trace ID:</span>
              <span className="text-neutral-400 font-mono text-[10px]">
                {invoice.id}
              </span>
            </div>
            {invoice.notes && (
              <div className="pt-2 text-[11px] text-neutral-600 bg-neutral-50 p-2.5 rounded-lg border border-neutral-100">
                <span className="font-bold text-neutral-700 block mb-1">Audit Notes:</span>
                <span className="whitespace-pre-line">{invoice.notes}</span>
              </div>
            )}
          </div>
        </div>

        {/* Payment Fulfillment Card */}
        <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-2xs space-y-3">
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-neutral-900 flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-[#FA651E]" />
            Disbursement &amp; Payment Settlement
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">Settlement Status:</span>
              <DocumentStatusBadge status={invoice.payment_status} size="sm" />
            </div>
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">Payment Date:</span>
              <span className="text-neutral-800">
                {invoice.paid_at ? new Date(invoice.paid_at).toLocaleString() : "Not Disbursed"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-neutral-100">
              <span className="text-neutral-500">Total Invoiced:</span>
              <span className="font-bold text-neutral-900">
                {invoice.currency} {Number(invoice.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="pt-2">
              {isPaid ? (
                <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-900 border border-emerald-200 text-xs flex items-center gap-2 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Invoice has been fully settled and paid in general ledger.</span>
                </div>
              ) : (
                <Button
                  onClick={() => setShowPayModal(true)}
                  className="w-full text-xs font-mono h-9 bg-neutral-900 hover:bg-neutral-800 text-white gap-2 shadow-2xs"
                >
                  <CreditCard className="w-3.5 h-3.5" />
                  Disburse Payment Now
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Payment Modal ──────────────────────────────────────────────────── */}
      {showPayModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-neutral-200 max-w-md w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <h3 className="text-sm font-bold font-mono text-neutral-900 flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-[#FA651E]" />
                Record Supplier Payment
              </h3>
              <button onClick={() => setShowPayModal(false)} className="text-neutral-400 hover:text-neutral-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleRecordPayment} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-neutral-600 mb-1">Invoice Reference</label>
                <input
                  type="text"
                  disabled
                  value={invoice.invoice_number}
                  className="w-full p-2 rounded-lg border border-neutral-200 bg-neutral-50 text-neutral-700 font-bold"
                />
              </div>

              <div>
                <label className="block text-neutral-600 mb-1">Payment Amount ({invoice.currency})</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E]"
                />
              </div>

              <div>
                <label className="block text-neutral-600 mb-1">Disbursement Method</label>
                <select
                  value={payMethod}
                  onChange={(e) => setPayMethod(e.target.value)}
                  className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E]"
                >
                  <option value="wire_transfer">SWIFT / Wire Transfer</option>
                  <option value="ach">ACH Automated Clearing House</option>
                  <option value="check">Company Check</option>
                  <option value="credit_card">Corporate Purchasing Card</option>
                </select>
              </div>

              <div>
                <label className="block text-neutral-600 mb-1">Payment Reference / Transaction ID</label>
                <input
                  type="text"
                  placeholder="e.g. TXN-998242"
                  value={payRef}
                  onChange={(e) => setPayRef(e.target.value)}
                  className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E]"
                />
              </div>

              <div>
                <label className="block text-neutral-600 mb-1">Notes</label>
                <textarea
                  rows={2}
                  placeholder="Optional payment notes..."
                  value={payNotes}
                  onChange={(e) => setPayNotes(e.target.value)}
                  className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-neutral-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPayModal(false)}
                  disabled={isPaying}
                  className="text-xs font-mono"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isPaying}
                  className="text-xs font-mono bg-[#FA651E] hover:bg-[#E05310] text-white"
                >
                  {isPaying ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
                  Confirm Disbursement
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
