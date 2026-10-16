"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileQuestion,
  Calendar,
  Building2,
  Clock,
  BarChart3,
  Send,
  Plus,
  CheckCircle2,
  XCircle,
  FileText,
  Percent,
  Layers,
  Award,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DocumentStatusBadge,
  RFxTypeBadge,
} from "@/components/procurement/document-status-badge";
import { SupplierQuotationModal } from "@/components/procurement/supplier-quotation-modal";
import { cn } from "@/lib/utils";

interface RFxInvitationItem {
  id: string;
  supplier_id: string;
  status: string;
  invited_at: string;
  responded_at?: string | null;
  supplier_legal_name?: string | null;
  supplier_country?: string | null;
}

interface RFxResponseItem {
  id: string;
  supplier_id: string;
  response_number: string;
  total_amount: number;
  currency: string;
  line_items: any[];
  validity_date?: string | null;
  payment_terms?: string | null;
  delivery_terms?: string | null;
  submitted_at: string;
  is_best_offer: boolean;
  supplier_legal_name?: string | null;
  supplier_country?: string | null;
}

interface RFxDetailData {
  id: string;
  org_id: string;
  rfx_number: string;
  rfx_type: string;
  title: string;
  description?: string | null;
  status: string;
  material_request_id?: string | null;
  category?: string | null;
  evaluation_criteria: { criterion: string; weight: number; description?: string }[];
  published_at?: string | null;
  submission_deadline?: string | null;
  awarded_at?: string | null;
  awarded_supplier_id?: string | null;
  awarded_supplier_name?: string | null;
  created_by?: string | null;
  created_at: string;
  invitations: RFxInvitationItem[];
  responses: RFxResponseItem[];
}

interface RFxDetailProps {
  rfx: RFxDetailData;
  onRefresh: () => void;
  onPublish: () => void;
  onCloseEvent: () => void;
}

export function RFxDetailView({
  rfx,
  onRefresh,
  onPublish,
  onCloseEvent,
}: RFxDetailProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "vendors" | "quotes">("overview");
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false);

  // Available suppliers for quoting (from invited suppliers)
  const availableSuppliers = rfx.invitations.map((inv) => ({
    id: inv.supplier_id,
    legal_name: inv.supplier_legal_name || "Supplier " + inv.supplier_id.slice(0, 8),
  }));

  return (
    <div className="space-y-6">
      {/* Top Banner if Awarded */}
      {rfx.status === "awarded" && (
        <div className="rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50/90 to-teal-50/90 p-4 shadow-xs flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
              <Award className="h-6 w-6" />
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-700 font-bold">
                Contract Awarded
              </span>
              <h3 className="text-sm font-bold text-neutral-900 mt-0.5">
                Winner: {rfx.awarded_supplier_name || "Selected Vendor"}
              </h3>
              <p className="text-xs text-neutral-600 mt-0.5">
                Awarded on {rfx.awarded_at ? new Date(rfx.awarded_at).toLocaleDateString() : "Record"}
              </p>
            </div>
          </div>
          <Link href={`/rfx/${rfx.id}/compare`}>
            <Button size="sm" variant="outline" className="h-8 text-xs border-emerald-300 text-emerald-800 bg-white">
              View Award Scorecard
            </Button>
          </Link>
        </div>
      )}

      {/* Main Header Card */}
      <div className="rounded-xl border border-neutral-200/80 bg-white/90 backdrop-blur-md p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <RFxTypeBadge rfxType={rfx.rfx_type} />
              <span className="font-mono text-sm font-bold text-neutral-900">{rfx.rfx_number}</span>
              <DocumentStatusBadge status={rfx.status} size="sm" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-neutral-900 mt-2">
              {rfx.title}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500 mt-2">
              {rfx.category && (
                <span className="flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5 text-neutral-400" />
                  Category: <strong className="text-neutral-700 font-medium">{rfx.category}</strong>
                </span>
              )}
              {rfx.submission_deadline && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-neutral-400" />
                  Deadline: <strong className="text-neutral-700 font-medium">{rfx.submission_deadline.slice(0, 10)}</strong>
                </span>
              )}
              <span className="flex items-center gap-1">
                <Building2 className="h-3.5 w-3.5 text-neutral-400" />
                Invited Vendors: <strong className="text-neutral-700 font-medium">{rfx.invitations.length}</strong>
              </span>
              <span className="flex items-center gap-1">
                <FileText className="h-3.5 w-3.5 text-neutral-400" />
                Quotations: <strong className="text-neutral-700 font-medium">{rfx.responses.length}</strong>
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {rfx.status === "draft" && (
              <Button
                size="sm"
                onClick={onPublish}
                className="h-8 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-medium shadow-xs"
              >
                <Send className="mr-1.5 h-3.5 w-3.5" />
                Publish Event
              </Button>
            )}

            {rfx.status !== "closed" && rfx.status !== "cancelled" && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsQuoteModalOpen(true)}
                className="h-8 text-xs border-neutral-200 text-neutral-800"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Enter Quotation
              </Button>
            )}

            {rfx.responses.length > 0 && (
              <Link href={`/rfx/${rfx.id}/compare`}>
                <Button
                  size="sm"
                  className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs font-semibold shadow-xs"
                >
                  <BarChart3 className="mr-1.5 h-3.5 w-3.5" />
                  Compare Bids ({rfx.responses.length})
                </Button>
              </Link>
            )}

            {rfx.status === "published" && (
              <Button
                size="sm"
                variant="outline"
                onClick={onCloseEvent}
                className="h-8 text-xs text-neutral-600 border-neutral-200"
              >
                Close Submissions
              </Button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-6 mt-6 border-t border-neutral-100 pt-4 text-xs font-medium">
          <button
            onClick={() => setActiveTab("overview")}
            className={cn(
              "pb-1 border-b-2 transition-colors",
              activeTab === "overview"
                ? "border-[#FA651E] text-[#FA651E] font-bold"
                : "border-transparent text-neutral-500 hover:text-neutral-900"
            )}
          >
            Overview & Requirements
          </button>
          <button
            onClick={() => setActiveTab("vendors")}
            className={cn(
              "pb-1 border-b-2 transition-colors flex items-center gap-1.5",
              activeTab === "vendors"
                ? "border-[#FA651E] text-[#FA651E] font-bold"
                : "border-transparent text-neutral-500 hover:text-neutral-900"
            )}
          >
            <span>Invited Vendors</span>
            <span className="bg-neutral-100 px-1.5 py-0.2 rounded-full text-[10px]">
              {rfx.invitations.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("quotes")}
            className={cn(
              "pb-1 border-b-2 transition-colors flex items-center gap-1.5",
              activeTab === "quotes"
                ? "border-[#FA651E] text-[#FA651E] font-bold"
                : "border-transparent text-neutral-500 hover:text-neutral-900"
            )}
          >
            <span>Supplier Quotations</span>
            <span
              className={cn(
                "px-1.5 py-0.2 rounded-full text-[10px]",
                rfx.responses.length > 0 ? "bg-purple-100 text-purple-700 font-bold" : "bg-neutral-100"
              )}
            >
              {rfx.responses.length}
            </span>
          </button>
        </div>
      </div>

      {/* Tab 1: Overview & Scope */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Description Card */}
            <div className="rounded-xl border border-neutral-200/80 bg-white p-5 shadow-xs space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                Scope of Work & Commercial Requirements
              </h3>
              <p className="text-xs text-neutral-700 leading-relaxed whitespace-pre-wrap">
                {rfx.description || "No additional scope notes entered for this event."}
              </p>
            </div>

            {/* Evaluation Criteria Weights */}
            <div className="rounded-xl border border-neutral-200/80 bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                  Evaluation Criteria Weights
                </h3>
                <span className="text-[11px] text-neutral-400 font-medium">Deterministic Scoring Engine</span>
              </div>

              <div className="border border-neutral-200 rounded-xl overflow-hidden divide-y divide-neutral-100">
                {rfx.evaluation_criteria.map((c, idx) => (
                  <div key={idx} className="p-3 flex items-center justify-between bg-white text-xs">
                    <div>
                      <span className="font-semibold text-neutral-900">{c.criterion}</span>
                      {c.description && (
                        <p className="text-[11px] text-neutral-500 mt-0.5">{c.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-neutral-100 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-[#FA651E] h-full"
                          style={{ width: `${Math.min(c.weight, 100)}%` }}
                        />
                      </div>
                      <span className="font-mono font-bold text-neutral-900 w-10 text-right">
                        {c.weight}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Metadata & Shortcuts */}
          <div className="space-y-4">
            <div className="rounded-xl border border-neutral-200/80 bg-white p-4 shadow-xs space-y-3 text-xs">
              <h3 className="font-bold text-neutral-900">Event Details</h3>
              <div className="space-y-2 text-neutral-600">
                <div className="flex justify-between py-1 border-b border-neutral-100">
                  <span className="text-neutral-500">Type</span>
                  <span className="font-mono font-semibold uppercase">{rfx.rfx_type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-neutral-100">
                  <span className="text-neutral-500">Status</span>
                  <span className="font-semibold capitalize">{rfx.status.replace("_", " ")}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-neutral-100">
                  <span className="text-neutral-500">Created At</span>
                  <span>{new Date(rfx.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-neutral-500">Submission Window</span>
                  <span className="font-semibold text-neutral-900">
                    {rfx.submission_deadline ? rfx.submission_deadline.slice(0, 10) : "Open"}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Bid Compare Banner */}
            <div className="rounded-xl border border-purple-200 bg-purple-50/60 p-4 space-y-2">
              <div className="flex items-center gap-2 text-purple-900 font-bold text-xs">
                <BarChart3 className="h-4 w-4 text-purple-600" />
                <span>Bid Comparison Matrix</span>
              </div>
              <p className="text-[11px] text-purple-700 leading-snug">
                Compare normalized prices, lead times, and weighted scorecards across all {rfx.responses.length} received quotes.
              </p>
              <Link href={`/rfx/${rfx.id}/compare`} className="block pt-1">
                <Button
                  size="sm"
                  className="w-full bg-purple-700 hover:bg-purple-800 text-white text-xs h-7 font-medium"
                >
                  Open Comparison Matrix
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Invited Vendors */}
      {activeTab === "vendors" && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-neutral-900">Invited Suppliers ({rfx.invitations.length})</h2>
              <p className="text-xs text-neutral-500">Status of sourcing event invitations sent to vendors.</p>
            </div>
          </div>

          <div className="border border-neutral-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-50 border-b border-neutral-200 text-neutral-500 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-4">Supplier</th>
                  <th className="py-2.5 px-4">Country</th>
                  <th className="py-2.5 px-4">Invitation Status</th>
                  <th className="py-2.5 px-4">Invited Date</th>
                  <th className="py-2.5 px-4">Responded Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rfx.invitations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-neutral-400">
                      No suppliers invited yet.
                    </td>
                  </tr>
                ) : (
                  rfx.invitations.map((inv) => (
                    <tr key={inv.id} className="hover:bg-neutral-50/50">
                      <td className="py-3 px-4 font-semibold text-neutral-900">
                        {inv.supplier_legal_name || inv.supplier_id}
                      </td>
                      <td className="py-3 px-4 text-neutral-600">
                        {inv.supplier_country || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <DocumentStatusBadge status={inv.status} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-neutral-500 text-[11px]">
                        {new Date(inv.invited_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-neutral-500 text-[11px]">
                        {inv.responded_at ? new Date(inv.responded_at).toLocaleDateString() : "Pending"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Supplier Quotations */}
      {activeTab === "quotes" && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-neutral-900">Received Quotations ({rfx.responses.length})</h2>
              <p className="text-xs text-neutral-500">Commercial proposals and line-item estimates from suppliers.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => setIsQuoteModalOpen(true)}
                className="h-8 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs font-medium"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Record Quotation
              </Button>
            </div>
          </div>

          <div className="border border-neutral-200 rounded-xl overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-50 border-b border-neutral-200 text-neutral-500 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-4">Quote Ref</th>
                  <th className="py-2.5 px-4">Supplier</th>
                  <th className="py-2.5 px-4">Total Amount</th>
                  <th className="py-2.5 px-4">Line Items</th>
                  <th className="py-2.5 px-4">Validity</th>
                  <th className="py-2.5 px-4">Payment Terms</th>
                  <th className="py-2.5 px-4 text-right">Best Offer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rfx.responses.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-neutral-400">
                      No quotations received yet. Click "Record Quotation" to enter a supplier proposal.
                    </td>
                  </tr>
                ) : (
                  rfx.responses.map((resp) => (
                    <tr key={resp.id} className="hover:bg-neutral-50/50">
                      <td className="py-3 px-4 font-mono font-bold text-neutral-900">
                        {resp.response_number}
                      </td>
                      <td className="py-3 px-4 font-medium text-neutral-900">
                        {resp.supplier_legal_name || "Supplier"}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-neutral-900">
                        {resp.currency} {resp.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-neutral-600">
                        {resp.line_items?.length || 0} items
                      </td>
                      <td className="py-3 px-4 text-neutral-500 text-[11px]">
                        {resp.validity_date || "—"}
                      </td>
                      <td className="py-3 px-4 text-neutral-600 text-[11px]">
                        {resp.payment_terms || "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {resp.is_best_offer ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            ★ Top Score
                          </span>
                        ) : (
                          <span className="text-neutral-400 text-[11px]">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quote Entry Modal */}
      <SupplierQuotationModal
        isOpen={isQuoteModalOpen}
        onClose={() => setIsQuoteModalOpen(false)}
        onSuccess={onRefresh}
        rfxEventId={rfx.id}
        rfxNumber={rfx.rfx_number}
        availableSuppliers={availableSuppliers}
      />
    </div>
  );
}
