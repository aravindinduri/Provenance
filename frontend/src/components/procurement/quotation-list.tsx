"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  Building2,
  Calendar,
  Loader2,
  DollarSign,
  ChevronRight,
  Award,
  Layers,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface QuotationItem {
  id: string;
  rfx_event_id: string;
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

interface QuotationListProps {
  items: QuotationItem[];
  isLoading: boolean;
  onRefresh: () => void;
}

export function QuotationList({ items, isLoading, onRefresh }: QuotationListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = items.filter((q) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const matchNum = q.response_number.toLowerCase().includes(term);
    const matchSup = (q.supplier_legal_name || "").toLowerCase().includes(term);
    const matchTerms = (q.payment_terms || "").toLowerCase().includes(term);
    return matchNum || matchSup || matchTerms;
  });

  return (
    <div className="space-y-4">
      {/* Search Header */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
          <Input
            type="text"
            placeholder="Search quotation #, supplier, terms..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 pl-8 text-xs bg-white/90 border-neutral-200/80 rounded-lg placeholder:text-neutral-400"
          />
        </div>
      </div>

      {/* Main Table Card */}
      <div className="rounded-xl border border-neutral-200/80 bg-white shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-neutral-50/75 border-b border-neutral-200 text-neutral-600 font-semibold tracking-wider uppercase text-[10px]">
              <tr>
                <th className="py-3 px-4">Quote Ref</th>
                <th className="py-3 px-4">Supplier</th>
                <th className="py-3 px-4">Total Amount</th>
                <th className="py-3 px-4">Line Items</th>
                <th className="py-3 px-4">Payment & Delivery</th>
                <th className="py-3 px-4">Validity</th>
                <th className="py-3 px-4">Submitted</th>
                <th className="py-3 px-4 text-right">Offer Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-neutral-400">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400 mb-2" />
                    <span>Loading supplier quotations...</span>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-14 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <div className="h-10 w-10 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400">
                        <FileText className="h-5 w-5" />
                      </div>
                      <span className="text-sm font-medium text-neutral-900">
                        {searchTerm ? "No quotations matching search" : "No quotations recorded yet"}
                      </span>
                      <p className="text-xs text-neutral-500 max-w-sm">
                        {searchTerm
                          ? "Try a different search query."
                          : "Quotations submitted by vendors or entered by procurement buyers against sourcing events will appear here."}
                      </p>
                      {!searchTerm && (
                        <Link href="/rfx" className="pt-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 text-xs font-medium"
                          >
                            View Active Sourcing Events
                          </Button>
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr key={item.id} className="hover:bg-neutral-50/60 transition-colors">
                    {/* Quote Ref */}
                    <td className="py-3.5 px-4 font-mono font-bold text-neutral-900 whitespace-nowrap">
                      <Link
                        href={`/rfx/${item.rfx_event_id}`}
                        className="hover:text-[#FA651E] transition-colors"
                      >
                        {item.response_number}
                      </Link>
                    </td>

                    {/* Supplier */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-neutral-900">
                        {item.supplier_legal_name || "Supplier"}
                      </div>
                      {item.supplier_country && (
                        <span className="text-[10px] text-neutral-400">
                          {item.supplier_country}
                        </span>
                      )}
                    </td>

                    {/* Total Amount */}
                    <td className="py-3.5 px-4 font-mono font-bold text-neutral-900 whitespace-nowrap">
                      {item.currency} {item.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* Line Items Count */}
                    <td className="py-3.5 px-4 text-neutral-600 whitespace-nowrap">
                      {item.line_items?.length || 0} items
                    </td>

                    {/* Payment & Delivery */}
                    <td className="py-3.5 px-4 text-neutral-600 text-[11px]">
                      <div>{item.payment_terms || "Standard terms"}</div>
                      <div className="text-neutral-400 text-[10px]">{item.delivery_terms || "—"}</div>
                    </td>

                    {/* Validity */}
                    <td className="py-3.5 px-4 text-neutral-500 text-[11px] whitespace-nowrap">
                      {item.validity_date ? (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-neutral-400" />
                          <span>{item.validity_date}</span>
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>

                    {/* Submitted At */}
                    <td className="py-3.5 px-4 text-neutral-500 text-[11px] whitespace-nowrap">
                      {new Date(item.submitted_at).toLocaleDateString()}
                    </td>

                    {/* Best Offer Status */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {item.is_best_offer ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <Award className="h-3 w-3" /> Best Offer
                          </span>
                        ) : (
                          <span className="text-neutral-400 text-[11px]">Standard Bid</span>
                        )}
                        <Link href={`/rfx/${item.rfx_event_id}/compare`}>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0 text-neutral-400 hover:text-neutral-700"
                            title="Compare in Matrix"
                          >
                            <ChevronRight className="h-3.5 w-3.5" />
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
