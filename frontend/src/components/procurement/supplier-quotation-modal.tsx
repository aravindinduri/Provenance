"use client";

import React, { useState } from "react";
import {
  X,
  FileText,
  Plus,
  Trash2,
  Calendar,
  DollarSign,
  Loader2,
  Building2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

interface SupplierOption {
  id: string;
  legal_name: string;
}

interface LineItemRow {
  item: string;
  qty: number;
  unit_price: number;
  lead_time_days: number;
}

interface SupplierQuotationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  rfxEventId: string;
  rfxNumber?: string;
  availableSuppliers: SupplierOption[];
  defaultCurrency?: string;
}

export function SupplierQuotationModal({
  isOpen,
  onClose,
  onSuccess,
  rfxEventId,
  rfxNumber,
  availableSuppliers,
  defaultCurrency = "USD",
}: SupplierQuotationModalProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [supplierId, setSupplierId] = useState(
    availableSuppliers[0]?.id || ""
  );
  const [currency, setCurrency] = useState(defaultCurrency);
  const [validityDate, setValidityDate] = useState("");
  const [paymentTerms, setPaymentTerms] = useState("Net 30");
  const [deliveryTerms, setDeliveryTerms] = useState("DAP - Delivered at Place");
  const [lineItems, setLineItems] = useState<LineItemRow[]>([
    { item: "Commercial Line Item 1", qty: 10, unit_price: 500, lead_time_days: 14 },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddLineItem = () => {
    setLineItems([
      ...lineItems,
      { item: `Commercial Line Item ${lineItems.length + 1}`, qty: 1, unit_price: 0, lead_time_days: 14 },
    ]);
  };

  const handleUpdateLineItem = (index: number, field: keyof LineItemRow, val: any) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: val };
    setLineItems(updated);
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const computedTotal = lineItems.reduce((acc, curr) => acc + (curr.qty * curr.unit_price || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierId) {
      setErrorMessage("Please select the submitting supplier.");
      return;
    }
    if (lineItems.length === 0) {
      setErrorMessage("Please include at least 1 quoted line item.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        rfx_event_id: rfxEventId,
        supplier_id: supplierId,
        total_amount: computedTotal,
        currency,
        line_items: lineItems.map((li) => ({
          item: li.item.trim(),
          qty: Number(li.qty),
          unit_price: Number(li.unit_price),
          lead_time_days: Number(li.lead_time_days) || 14,
        })),
        validity_date: validityDate || null,
        payment_terms: paymentTerms || null,
        delivery_terms: deliveryTerms || null,
      };

      const res = await fetch("/api/v1/supplier-quotations", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to record supplier quotation");
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Error saving quotation");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-neutral-200 bg-white shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-[#FFF2EB] text-[#FA651E]">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-neutral-900">Record Supplier Quotation</h2>
              <p className="text-xs text-neutral-500">
                Log commercial proposal for {rfxNumber || "sourcing event"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {errorMessage && (
            <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Supplier Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700">
                Submitting Supplier <span className="text-red-500">*</span>
              </label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="w-full h-9 rounded-lg border border-neutral-200 bg-white px-3 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400 font-medium"
                required
              >
                <option value="">Select Supplier...</option>
                {availableSuppliers.map((sup) => (
                  <option key={sup.id} value={sup.id}>
                    {sup.legal_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full h-9 rounded-lg border border-neutral-200 bg-white px-3 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400 font-mono"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="INR">INR (₹)</option>
              </select>
            </div>
          </div>

          {/* Line Items Specification */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-neutral-700">Quoted Line Items</label>
              <span className="text-xs text-neutral-500 font-mono font-medium">
                Total: <span className="font-bold text-neutral-900">{currency} {computedTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </span>
            </div>

            <div className="border border-neutral-200 rounded-xl overflow-hidden divide-y divide-neutral-100">
              <div className="bg-neutral-50/80 px-3 py-2 grid grid-cols-12 gap-2 text-[10px] font-semibold text-neutral-500 uppercase">
                <span className="col-span-5">Item / Spec</span>
                <span className="col-span-2 text-right">Qty</span>
                <span className="col-span-2 text-right">Unit Price</span>
                <span className="col-span-2 text-right">Lead (Days)</span>
                <span className="col-span-1"></span>
              </div>

              {lineItems.map((li, idx) => (
                <div key={idx} className="p-2.5 grid grid-cols-12 gap-2 items-center bg-white">
                  <div className="col-span-5">
                    <Input
                      value={li.item}
                      onChange={(e) => handleUpdateLineItem(idx, "item", e.target.value)}
                      placeholder="Line item description"
                      className="h-7 text-xs"
                      required
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      min={1}
                      value={li.qty}
                      onChange={(e) => handleUpdateLineItem(idx, "qty", Number(e.target.value))}
                      className="h-7 text-xs text-right font-mono"
                      required
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      value={li.unit_price}
                      onChange={(e) => handleUpdateLineItem(idx, "unit_price", Number(e.target.value))}
                      className="h-7 text-xs text-right font-mono"
                      required
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      min={1}
                      value={li.lead_time_days}
                      onChange={(e) => handleUpdateLineItem(idx, "lead_time_days", Number(e.target.value))}
                      className="h-7 text-xs text-right font-mono"
                    />
                  </div>
                  <div className="col-span-1 text-center">
                    {lineItems.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveLineItem(idx)}
                        className="text-neutral-400 hover:text-red-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddLineItem}
              className="text-[11px] h-7 border-dashed border-neutral-300 text-neutral-600"
            >
              <Plus className="mr-1 h-3 w-3" />
              Add Line Item
            </Button>
          </div>

          {/* Terms & Validity */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-neutral-600">Validity Date</label>
              <Input
                type="date"
                value={validityDate}
                onChange={(e) => setValidityDate(e.target.value)}
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-neutral-600">Payment Terms</label>
              <Input
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                placeholder="e.g. Net 30, Net 60"
                className="h-8 text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-neutral-600">Delivery Terms</label>
              <Input
                value={deliveryTerms}
                onChange={(e) => setDeliveryTerms(e.target.value)}
                placeholder="e.g. DAP, FOB, CIF"
                className="h-8 text-xs"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-neutral-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs h-8"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="bg-[#FA651E] hover:bg-[#E05310] text-white text-xs h-8 font-semibold shadow-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  Saving Quote...
                </>
              ) : (
                "Save Quotation"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
