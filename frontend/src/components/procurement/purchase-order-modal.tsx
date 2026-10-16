"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Plus,
  Trash2,
  Loader2,
  Building2,
  Calendar,
  DollarSign,
  Package,
  MapPin,
  FileText,
  AlertCircle,
  CheckCircle2,
  ShoppingCart,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

interface PurchaseOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialSupplierId?: string | null;
  initialSupplierName?: string | null;
}

interface LineItemForm {
  item_id?: string | null;
  item_code?: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  unit_price: number;
}

export function PurchaseOrderModal({
  isOpen,
  onClose,
  onSuccess,
  initialSupplierId,
  initialSupplierName,
}: PurchaseOrderModalProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [suppliers, setSuppliers] = useState<{ id: string; name: string }[]>([]);
  const [catalogItems, setCatalogItems] = useState<{ id: string; name: string; item_code: string; unit_price: number }[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);

  // Form state
  const [selectedSupplierId, setSelectedSupplierId] = useState(initialSupplierId || "");
  const [expectedDate, setExpectedDate] = useState("");
  const [paymentTerms, setPaymentTerms] = useState("Net 30");
  const [deliveryTerms, setDeliveryTerms] = useState("FOB Destination");
  const [notes, setNotes] = useState("");
  const [autoSubmit, setAutoSubmit] = useState(true);

  // Delivery Address
  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [country, setCountry] = useState("USA");

  // Line items
  const [lineItems, setLineItems] = useState<LineItemForm[]>([
    {
      description: "",
      quantity: 1,
      unit_of_measure: "each",
      unit_price: 0,
    },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load suppliers and items from live API
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    async function loadData() {
      setIsLoadingMetadata(true);
      try {
        const token = await getToken();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        // Fetch suppliers
        const supRes = await fetch("/api/v1/suppliers?limit=100", { headers });
        if (supRes.ok && isMounted) {
          const data = await supRes.json();
          const list = (data.items || []).map((s: any) => ({
            id: s.id || s.company_id,
            name: s.legal_name || s.name || "Vendor",
          }));
          setSuppliers(list);
          if (!selectedSupplierId && list.length > 0) {
            setSelectedSupplierId(list[0].id);
          }
        }

        // Fetch items
        const itemRes = await fetch("/api/v1/items?limit=100", { headers });
        if (itemRes.ok && isMounted) {
          const itemData = await itemRes.json();
          const items = (itemData.items || []).map((i: any) => ({
            id: i.id,
            name: i.name,
            item_code: i.item_code,
            unit_price: parseFloat(i.default_unit_price || 0),
          }));
          setCatalogItems(items);
        }
      } catch (err) {
        console.error("Error loading suppliers/items:", err);
      } finally {
        if (isMounted) setIsLoadingMetadata(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [isOpen, orgId, getToken]);

  if (!isOpen) return null;

  const handleAddLine = () => {
    setLineItems([
      ...lineItems,
      {
        description: "",
        quantity: 1,
        unit_of_measure: "each",
        unit_price: 0,
      },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    if (lineItems.length === 1) return;
    setLineItems(lineItems.filter((_, i) => i !== idx));
  };

  const handleLineChange = (idx: number, field: keyof LineItemForm, val: any) => {
    const updated = [...lineItems];
    updated[idx] = { ...updated[idx], [field]: val };
    setLineItems(updated);
  };

  const handleSelectCatalogItem = (idx: number, itemId: string) => {
    const found = catalogItems.find((ci) => ci.id === itemId);
    if (!found) return;
    const updated = [...lineItems];
    updated[idx] = {
      ...updated[idx],
      item_id: found.id,
      item_code: found.item_code,
      description: found.name,
      unit_price: found.unit_price,
    };
    setLineItems(updated);
  };

  const calculateTotal = () => {
    return lineItems.reduce((acc, it) => acc + (it.quantity || 0) * (it.unit_price || 0), 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedSupplierId) {
      setErrorMessage("Please select a vendor/supplier for this purchase order.");
      return;
    }

    const invalidItem = lineItems.find((it) => !it.description.trim() || it.quantity <= 0);
    if (invalidItem) {
      setErrorMessage("All line items must contain a valid description and quantity > 0.");
      return;
    }

    setIsSubmitting(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        company_id: selectedSupplierId,
        order_date: new Date().toISOString().slice(0, 10),
        expected_delivery_date: expectedDate || null,
        currency: "USD",
        payment_terms: paymentTerms,
        delivery_terms: deliveryTerms,
        delivery_address: street || city ? { street, city, state, country } : null,
        notes: notes || null,
        line_items: lineItems.map((li) => ({
          item_id: li.item_id || null,
          item_code: li.item_code || null,
          description: li.description,
          quantity: Number(li.quantity),
          unit_of_measure: li.unit_of_measure || "each",
          unit_price: Number(li.unit_price),
        })),
      };

      const res = await fetch("/api/v1/purchase-orders", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create purchase order.");
      }

      const createdPO = await res.json();

      // If auto-submit requested, route through DoA approval
      if (autoSubmit && createdPO.id) {
        try {
          await fetch(`/api/v1/purchase-orders/${createdPO.id}/submit`, {
            method: "POST",
            headers,
          });
        } catch {
          // non-blocking
        }
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred while creating the purchase order.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-neutral-900">New Purchase Order</h2>
              <p className="text-xs text-neutral-500">
                Generate an official binding purchase order with line-item specifications
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-700 border border-rose-200">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* Top Parameters */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Vendor / Supplier <span className="text-rose-500">*</span>
              </label>
              {isLoadingMetadata ? (
                <div className="flex items-center gap-2 py-2 text-xs text-neutral-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading vendors...
                </div>
              ) : (
                <select
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                  className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-900 focus:border-neutral-900 focus:outline-none"
                  required
                >
                  <option value="" disabled>Select supplier</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Expected Delivery Date
              </label>
              <Input
                type="date"
                value={expectedDate}
                onChange={(e) => setExpectedDate(e.target.value)}
                className="text-xs border-neutral-200"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Payment Terms
              </label>
              <select
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-900 focus:border-neutral-900 focus:outline-none"
              >
                <option value="Net 15">Net 15</option>
                <option value="Net 30">Net 30</option>
                <option value="Net 60">Net 60</option>
                <option value="Net 90">Net 90</option>
                <option value="Due on Receipt">Due on Receipt</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Delivery Terms (Incoterms)
              </label>
              <select
                value={deliveryTerms}
                onChange={(e) => setDeliveryTerms(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-900 focus:border-neutral-900 focus:outline-none"
              >
                <option value="FOB Destination">FOB Destination</option>
                <option value="FOB Shipping Point">FOB Shipping Point</option>
                <option value="CIF">CIF (Cost, Insurance & Freight)</option>
                <option value="DDP">DDP (Delivered Duty Paid)</option>
                <option value="EXW">EXW (Ex Works)</option>
              </select>
            </div>
          </div>

          {/* Delivery Destination */}
          <div className="rounded-xl border border-neutral-200 bg-neutral-50/50 p-3.5 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-800">
              <MapPin className="h-3.5 w-3.5 text-neutral-500" />
              <span>Receiving Facility / Delivery Address</span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
              <Input
                placeholder="Street address"
                value={street}
                onChange={(e) => setStreet(e.target.value)}
                className="sm:col-span-2 text-xs bg-white border-neutral-200"
              />
              <Input
                placeholder="City"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="text-xs bg-white border-neutral-200"
              />
              <Input
                placeholder="State / Region"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="text-xs bg-white border-neutral-200"
              />
            </div>
          </div>

          {/* Line Items Editor */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-neutral-700">
                Order Line Items
              </label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddLine}
                className="h-7 text-xs border-neutral-200 text-neutral-700 hover:bg-neutral-100"
              >
                <Plus className="h-3 w-3 mr-1" /> Add Row
              </Button>
            </div>

            <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
              {lineItems.map((line, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-2 items-center rounded-lg border border-neutral-200 bg-white p-2.5 text-xs shadow-sm"
                >
                  {catalogItems.length > 0 && (
                    <div className="col-span-12 sm:col-span-3">
                      <select
                        onChange={(e) => handleSelectCatalogItem(idx, e.target.value)}
                        className="w-full rounded border border-neutral-200 bg-neutral-50/50 px-2 py-1.5 text-xs text-neutral-700 focus:outline-none"
                      >
                        <option value="">Catalog Item (optional)</option>
                        {catalogItems.map((ci) => (
                          <option key={ci.id} value={ci.id}>
                            {ci.item_code} — {ci.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className={catalogItems.length > 0 ? "col-span-12 sm:col-span-4" : "col-span-12 sm:col-span-6"}>
                    <Input
                      placeholder="Item description or specification *"
                      value={line.description}
                      onChange={(e) => handleLineChange(idx, "description", e.target.value)}
                      className="text-xs border-neutral-200"
                      required
                    />
                  </div>

                  <div className="col-span-4 sm:col-span-2">
                    <Input
                      type="number"
                      step="any"
                      min="0.01"
                      placeholder="Qty"
                      value={line.quantity}
                      onChange={(e) => handleLineChange(idx, "quantity", parseFloat(e.target.value) || 0)}
                      className="text-xs border-neutral-200 font-mono"
                      required
                    />
                  </div>

                  <div className="col-span-4 sm:col-span-2">
                    <Input
                      type="number"
                      step="any"
                      min="0"
                      placeholder="Price ($)"
                      value={line.unit_price}
                      onChange={(e) => handleLineChange(idx, "unit_price", parseFloat(e.target.value) || 0)}
                      className="text-xs border-neutral-200 font-mono"
                      required
                    />
                  </div>

                  <div className="col-span-4 sm:col-span-1 flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => handleRemoveLine(idx)}
                      disabled={lineItems.length === 1}
                      className={cn(
                        "rounded p-1 text-neutral-400 transition-colors",
                        lineItems.length === 1 ? "opacity-30 cursor-not-allowed" : "hover:text-rose-600 hover:bg-rose-50"
                      )}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Total calculation bar */}
            <div className="flex items-center justify-between rounded-xl bg-neutral-900 px-4 py-3 text-white">
              <span className="text-xs font-medium text-neutral-300">Total Purchase Order Value</span>
              <span className="text-base font-bold font-mono">
                ${calculateTotal().toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1">
              Order Notes & Instructions
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Packaging requirements, delivery dock hours, compliance standards..."
              className="w-full rounded-lg border border-neutral-200 p-2.5 text-xs text-neutral-900 focus:border-neutral-900 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="autoSubmit"
              checked={autoSubmit}
              onChange={(e) => setAutoSubmit(e.target.checked)}
              className="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 h-4 w-4"
            />
            <label htmlFor="autoSubmit" className="text-xs text-neutral-700 select-none">
              Automatically route for Delegation of Authority (DoA) approval upon creation
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 border-t border-neutral-100 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="text-xs bg-neutral-900 text-white hover:bg-neutral-800"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                  Creating Order...
                </>
              ) : (
                "Issue Purchase Order"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
