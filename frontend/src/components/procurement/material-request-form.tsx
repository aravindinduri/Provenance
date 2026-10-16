"use client";

import React, { useState, useEffect } from "react";
import { Plus, Trash2, Loader2, AlertCircle, ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export interface LineItemFormValue {
  item_id?: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  estimated_unit_price: number;
  currency: string;
}

export interface CatalogItemOption {
  id: string;
  item_code: string;
  name: string;
  default_unit_price: number | null;
  unit_of_measure: string | null;
  currency: string | null;
}

interface MaterialRequestFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (mr: Record<string, unknown>) => void;
}

export function MaterialRequestFormModal({
  isOpen,
  onClose,
  onSuccess,
}: MaterialRequestFormModalProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "critical">("medium");
  const [requiredByDate, setRequiredByDate] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [justification, setJustification] = useState("");
  const [autoSubmit, setAutoSubmit] = useState(false);

  const [catalogItems, setCatalogItems] = useState<CatalogItemOption[]>([]);
  const [lineItems, setLineItems] = useState<LineItemFormValue[]>([
    {
      description: "",
      quantity: 10,
      unit_of_measure: "units",
      estimated_unit_price: 100,
      currency: "USD",
    },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch available items from live API
  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    async function loadCatalog() {
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;
        const res = await fetch("/api/v1/items?limit=100&is_active=true", { headers });
        if (res.ok && isMounted) {
          const data = await res.json();
          setCatalogItems(data.items || []);
        }
      } catch {
        // silent fallback: allow free-text line items
      }
    }
    loadCatalog();
    return () => {
      isMounted = false;
    };
  }, [isOpen, orgId, getToken]);

  const addLineItem = () => {
    setLineItems((prev) => [
      ...prev,
      {
        description: "",
        quantity: 1,
        unit_of_measure: "units",
        estimated_unit_price: 50,
        currency,
      },
    ]);
  };

  const removeLineItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const updateLineItem = (index: number, patch: Partial<LineItemFormValue>) => {
    setLineItems((prev) =>
      prev.map((item, i) => {
        if (i !== index) return item;
        const updated = { ...item, ...patch };
        // If an item was picked from catalog, auto-populate details
        if (patch.item_id && patch.item_id !== "") {
          const found = catalogItems.find((ci) => ci.id === patch.item_id);
          if (found) {
            updated.description = found.name;
            if (found.default_unit_price != null) {
              updated.estimated_unit_price = Number(found.default_unit_price);
            }
            if (found.unit_of_measure) {
              updated.unit_of_measure = found.unit_of_measure;
            }
            if (found.currency) {
              updated.currency = found.currency;
            }
          }
        }
        return updated;
      })
    );
  };

  const totalAmount = lineItems.reduce(
    (sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.estimated_unit_price) || 0),
    0
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setErrorMsg("Title is required");
      return;
    }
    if (lineItems.length === 0) {
      setErrorMsg("At least one line item is required");
      return;
    }
    for (const li of lineItems) {
      if (!li.description.trim()) {
        setErrorMsg("All line items must have a description or catalog item selected");
        return;
      }
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        title: title.trim(),
        department: department.trim() || undefined,
        priority,
        required_by_date: requiredByDate && requiredByDate.trim() ? requiredByDate.trim() : undefined,
        currency,
        justification: justification.trim() || undefined,
        line_items: lineItems.map((li) => ({
          description: li.description.trim(),
          quantity: Number(li.quantity),
          unit_of_measure: li.unit_of_measure.trim() || "units",
          estimated_unit_price: Number(li.estimated_unit_price),
          currency: li.currency || currency,
          item_id: li.item_id && li.item_id.trim() ? li.item_id.trim() : undefined,
        })),
      };

      const res = await fetch("/api/v1/material-requests", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (err.errors && Array.isArray(err.errors) && err.errors.length > 0) {
          const fieldMsgs = err.errors
            .map((e: { field?: string; message?: string }) =>
              e.field ? `${e.field}: ${e.message}` : e.message
            )
            .filter(Boolean)
            .join("; ");
          throw new Error(fieldMsgs || err.detail || `Validation error (HTTP ${res.status})`);
        }
        throw new Error(err.detail || `Failed to create request (HTTP ${res.status})`);
      }

      let createdMr = await res.json();

      // If user toggled autoSubmit, submit immediately
      if (autoSubmit && createdMr.id) {
        const subRes = await fetch(`/api/v1/material-requests/${createdMr.id}/submit`, {
          method: "POST",
          headers,
        });
        if (subRes.ok) {
          createdMr = await subRes.json();
        }
      }

      onSuccess(createdMr);
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create material request");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base font-semibold">
            <ShoppingCart className="h-5 w-5 text-[#FA651E]" />
            New Material Request (Requisition)
          </DialogTitle>
          <DialogDescription className="text-xs text-neutral-500">
            Create an internal requisition for items and materials. Evaluates delegation of authority rules upon submission.
          </DialogDescription>
        </DialogHeader>

        {errorMsg && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-neutral-700">Requisition Title *</label>
              <Input
                placeholder="e.g., Raw Steel & Aluminum Bar Replenishment"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Department</label>
              <Input
                placeholder="e.g., Operations / Plant 2"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as any)}
                className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Required By Date</label>
              <Input
                type="date"
                value={requiredByDate}
                onChange={(e) => setRequiredByDate(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-neutral-700">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400 font-mono"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="INR">INR (₹)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>

            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-neutral-700">Business Justification</label>
              <Textarea
                placeholder="e.g., Project requirement for ongoing manufacturing run. Low stock alert triggered."
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                className="min-h-16 text-xs"
              />
            </div>
          </div>

          {/* Line Items Section */}
          <div className="space-y-2 pt-2 border-t border-neutral-100">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-900 uppercase tracking-wider font-mono">
                Line Items ({lineItems.length})
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addLineItem}
                className="h-7 text-xs border-dashed"
              >
                <Plus className="mr-1 h-3 w-3" />
                Add Line Item
              </Button>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {lineItems.map((item, idx) => {
                const rowTotal = (Number(item.quantity) || 0) * (Number(item.estimated_unit_price) || 0);
                return (
                  <div
                    key={idx}
                    className="grid grid-cols-12 gap-2 items-center rounded-lg border border-neutral-200/80 bg-neutral-50/50 p-2 text-xs"
                  >
                    <div className="col-span-12 sm:col-span-4">
                      {catalogItems.length > 0 ? (
                        <select
                          value={item.item_id || ""}
                          onChange={(e) => updateLineItem(idx, { item_id: e.target.value })}
                          className="w-full h-7 rounded border border-neutral-300 bg-white px-2 text-xs text-neutral-800"
                        >
                          <option value="">-- Custom Description --</option>
                          {catalogItems.map((ci) => (
                            <option key={ci.id} value={ci.id}>
                              {ci.item_code} - {ci.name}
                            </option>
                          ))}
                        </select>
                      ) : null}
                      <Input
                        placeholder="Item description *"
                        value={item.description}
                        onChange={(e) => updateLineItem(idx, { description: e.target.value })}
                        className="h-7 text-xs mt-1"
                        required
                      />
                    </div>

                    <div className="col-span-4 sm:col-span-2">
                      <Input
                        type="number"
                        min="0.01"
                        step="any"
                        placeholder="Qty"
                        value={item.quantity}
                        onChange={(e) => updateLineItem(idx, { quantity: parseFloat(e.target.value) || 0 })}
                        className="h-7 text-xs font-mono"
                        required
                      />
                    </div>

                    <div className="col-span-4 sm:col-span-2">
                      <Input
                        placeholder="UoM (e.g. units)"
                        value={item.unit_of_measure}
                        onChange={(e) => updateLineItem(idx, { unit_of_measure: e.target.value })}
                        className="h-7 text-xs"
                      />
                    </div>

                    <div className="col-span-4 sm:col-span-2">
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        placeholder="Est. Unit Price"
                        value={item.estimated_unit_price}
                        onChange={(e) =>
                          updateLineItem(idx, { estimated_unit_price: parseFloat(e.target.value) || 0 })
                        }
                        className="h-7 text-xs font-mono"
                      />
                    </div>

                    <div className="col-span-10 sm:col-span-1 text-right font-mono font-medium text-neutral-800">
                      ${rowTotal.toFixed(2)}
                    </div>

                    <div className="col-span-2 sm:col-span-1 text-right">
                      {lineItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeLineItem(idx)}
                          className="text-neutral-400 hover:text-red-600 p-1 rounded"
                          title="Remove item"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between rounded-lg bg-neutral-100/80 px-3 py-2 text-xs font-medium text-neutral-800">
              <span>Total Estimated Amount</span>
              <span className="font-mono text-sm font-bold text-neutral-950">
                {currency} {totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="autoSubmitCheck"
              checked={autoSubmit}
              onChange={(e) => setAutoSubmit(e.target.checked)}
              className="h-4 w-4 rounded border-neutral-300 text-[#FA651E] focus:ring-[#FA651E]"
            />
            <label htmlFor="autoSubmitCheck" className="text-xs text-neutral-700 select-none">
              Submit for approval immediately after creating (transitions to <span className="font-semibold text-amber-700">pending_approval</span>)
            </label>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-neutral-100">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="bg-[#FA651E] hover:bg-[#E05310] text-white shadow-2xs"
            >
              {isSubmitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
              {autoSubmit ? "Create & Submit for Approval" : "Save as Draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
