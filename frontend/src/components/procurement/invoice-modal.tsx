"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Receipt,
  ShoppingCart,
  PackageCheck,
  Loader2,
  Calendar,
  AlertCircle,
  Plus,
  Trash2,
  Building2,
  DollarSign,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

interface InvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  preselectedPOId?: string;
}

interface InvoiceLineFormItem {
  po_line_index: number;
  item_id?: string | null;
  item_code?: string | null;
  description: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  unit_of_measure: string;
}

export function InvoiceModal({
  isOpen,
  onClose,
  onSuccess,
  preselectedPOId,
}: InvoiceModalProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [availablePOs, setAvailablePOs] = useState<any[]>([]);
  const [selectedPOId, setSelectedPOId] = useState<string>(preselectedPOId || "");
  const [isLoadingPOs, setIsLoadingPOs] = useState(false);

  // Form fields
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [currency, setCurrency] = useState("USD");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
  );
  const [notes, setNotes] = useState("");
  const [autoMatch, setAutoMatch] = useState(true);
  const [lineItems, setLineItems] = useState<InvoiceLineFormItem[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load available POs when modal opens
  useEffect(() => {
    if (!isOpen) return;

    async function fetchPOs() {
      setIsLoadingPOs(true);
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        const res = await fetch("/api/v1/purchase-orders?limit=50", { headers });
        if (res.ok) {
          const data = await res.json();
          const pos = data.items || [];
          setAvailablePOs(pos);

          // If preselected, apply it
          if (preselectedPOId) {
            const found = pos.find((p: any) => p.id === preselectedPOId);
            if (found) {
              applyPO(found);
            }
          }
        }
      } catch (err: any) {
        console.error("Failed to load POs:", err);
      } finally {
        setIsLoadingPOs(false);
      }
    }

    fetchPOs();
  }, [isOpen, orgId, preselectedPOId, getToken]);

  // When user selects a PO, auto-fill vendor and lines
  const applyPO = (po: any) => {
    setSelectedPOId(po.id);
    setSupplierName(po.company_name || "");
    setCompanyId(po.company_id || null);
    setCurrency(po.currency || "USD");

    const lines: InvoiceLineFormItem[] = [];
    if (Array.isArray(po.line_items) && po.line_items.length > 0) {
      po.line_items.forEach((item: any, idx: number) => {
        const qty = Number(item.quantity) || 1;
        const price = Number(item.unit_price) || 0;
        lines.push({
          po_line_index: idx,
          item_id: item.item_id || null,
          item_code: item.item_code || null,
          description: item.description || "PO Line Item",
          quantity: qty,
          unit_price: price,
          total_amount: Math.round(qty * price * 100) / 100,
          unit_of_measure: item.unit_of_measure || "each",
        });
      });
    } else {
      lines.push({
        po_line_index: 0,
        description: `Supplies per PO ${po.po_number}`,
        quantity: 1,
        unit_price: Number(po.total_amount) || 1000,
        total_amount: Number(po.total_amount) || 1000,
        unit_of_measure: "lot",
      });
    }

    setLineItems(lines);
  };

  const handlePOChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const poId = e.target.value;
    if (!poId) {
      setSelectedPOId("");
      setLineItems([]);
      return;
    }
    const found = availablePOs.find((p) => p.id === poId);
    if (found) {
      applyPO(found);
    }
  };

  // Update line item
  const handleLineChange = (
    index: number,
    field: keyof InvoiceLineFormItem,
    val: any
  ) => {
    setLineItems((prev) => {
      const next = [...prev];
      const item = { ...next[index], [field]: val };
      if (field === "quantity" || field === "unit_price") {
        const q = Number(field === "quantity" ? val : item.quantity) || 0;
        const p = Number(field === "unit_price" ? val : item.unit_price) || 0;
        item.total_amount = Math.round(q * p * 100) / 100;
      }
      next[index] = item;
      return next;
    });
  };

  const addLine = () => {
    setLineItems((prev) => [
      ...prev,
      {
        po_line_index: prev.length,
        description: "Additional Line Item",
        quantity: 1,
        unit_price: 100,
        total_amount: 100,
        unit_of_measure: "each",
      },
    ]);
  };

  const removeLine = (idx: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const totalCalculated = lineItems.reduce((acc, curr) => acc + (curr.total_amount || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPOId && !supplierName.trim()) {
      setErrorMessage("Please select a Purchase Order or specify a supplier name.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        po_id: selectedPOId || undefined,
        company_id: companyId || undefined,
        supplier_name: supplierName.trim() || undefined,
        invoice_number: invoiceNumber.trim() || undefined,
        invoice_date: invoiceDate,
        due_date: dueDate,
        currency,
        amount: totalCalculated,
        line_items: lineItems.map((li) => ({
          po_line_index: li.po_line_index,
          item_id: li.item_id,
          item_code: li.item_code,
          description: li.description,
          quantity: li.quantity,
          unit_price: li.unit_price,
          total_amount: li.total_amount,
          unit_of_measure: li.unit_of_measure,
        })),
        notes: notes.trim() || undefined,
        auto_match: autoMatch,
      };

      const res = await fetch("/api/v1/invoices", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create invoice");
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl border border-neutral-200 max-w-2xl w-full p-6 space-y-5 shadow-2xl my-8">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-orange-50 text-[#FA651E] flex items-center justify-center">
              <Receipt className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold font-mono text-neutral-900">
                Log Supplier Invoice
              </h2>
              <p className="text-[11px] text-neutral-500 font-mono">
                Ingest vendor invoice and run deterministic 3-way matching
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-700">
            <X className="w-4 h-4" />
          </button>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 font-mono text-xs">
          {/* PO Selector */}
          <div>
            <label className="block text-neutral-600 mb-1 font-semibold">
              Select Purchase Order to Bill Against *
            </label>
            {isLoadingPOs ? (
              <div className="flex items-center gap-2 text-neutral-400 p-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Loading purchase orders...</span>
              </div>
            ) : (
              <select
                value={selectedPOId}
                onChange={handlePOChange}
                className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E] bg-white text-xs"
              >
                <option value="">-- Direct Invoice / Select Purchase Order --</option>
                {availablePOs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.po_number} · {p.company_name || "Supplier"} · {p.currency} {Number(p.total_amount).toLocaleString()} ({p.status})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-neutral-600 mb-1">
                Invoice Number (Leave blank to auto-generate)
              </label>
              <Input
                placeholder="e.g. INV-2026-0001"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="text-xs h-9 font-mono"
              />
            </div>

            <div>
              <label className="block text-neutral-600 mb-1">Supplier Legal Name</label>
              <Input
                placeholder="Vendor Name"
                value={supplierName}
                onChange={(e) => setSupplierName(e.target.value)}
                className="text-xs h-9 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-neutral-600 mb-1">Invoice Date</label>
              <Input
                type="date"
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                className="text-xs h-9 font-mono"
              />
            </div>

            <div>
              <label className="block text-neutral-600 mb-1">Payment Due Date</label>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="text-xs h-9 font-mono"
              />
            </div>

            <div>
              <label className="block text-neutral-600 mb-1">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full p-2 h-9 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E] bg-white text-xs"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="INR">INR (₹)</option>
              </select>
            </div>
          </div>

          {/* Line Items Editor */}
          <div className="border border-neutral-200 rounded-xl p-3 space-y-2 bg-neutral-50/60">
            <div className="flex items-center justify-between">
              <span className="font-bold text-neutral-700 uppercase tracking-wide text-[10px]">
                Billed Line Items ({lineItems.length})
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addLine}
                className="text-[10px] h-6 px-2 gap-1 text-[#FA651E] border-[#FA651E]/30"
              >
                <Plus className="w-2.5 h-2.5" /> Add Line
              </Button>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {lineItems.map((line, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 p-2 bg-white rounded-lg border border-neutral-200 text-xs"
                >
                  <input
                    type="text"
                    placeholder="Description"
                    value={line.description}
                    onChange={(e) => handleLineChange(idx, "description", e.target.value)}
                    className="flex-1 p-1 text-xs border border-neutral-200 rounded"
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Qty"
                    value={line.quantity}
                    onChange={(e) => handleLineChange(idx, "quantity", parseFloat(e.target.value) || 0)}
                    className="w-16 p-1 text-xs text-right border border-neutral-200 rounded"
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Price"
                    value={line.unit_price}
                    onChange={(e) => handleLineChange(idx, "unit_price", parseFloat(e.target.value) || 0)}
                    className="w-20 p-1 text-xs text-right border border-neutral-200 rounded"
                  />
                  <span className="w-20 text-right font-bold text-neutral-800">
                    ${(line.total_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeLine(idx)}
                    className="text-neutral-400 hover:text-rose-600 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-neutral-200/80 font-bold text-neutral-900">
              <span>Total Invoice Amount:</span>
              <span className="text-[#FA651E]">
                {currency} {totalCalculated.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-neutral-600 mb-1">Notes / Discrepancy Remarks</label>
            <textarea
              rows={2}
              placeholder="Internal accounting or remittance notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full p-2 rounded-lg border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-[#FA651E] text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoMatch"
              checked={autoMatch}
              onChange={(e) => setAutoMatch(e.target.checked)}
              className="rounded border-neutral-300 text-[#FA651E] focus:ring-[#FA651E]"
            />
            <label htmlFor="autoMatch" className="text-neutral-700 text-xs cursor-pointer">
              Automatically evaluate 3-Way Match against PO &amp; Goods Receipt Note
            </label>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-neutral-100">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs font-mono"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="text-xs font-mono bg-[#FA651E] hover:bg-[#E05310] text-white"
            >
              {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
              Log Invoice &amp; Run Match
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
