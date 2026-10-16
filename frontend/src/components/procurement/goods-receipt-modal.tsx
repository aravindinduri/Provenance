"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  PackageCheck,
  Loader2,
  Calendar,
  Truck,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

interface GoodsReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  preselectedPOId?: string;
  preselectedPONumber?: string;
  preselectedLines?: any[];
}

interface ReceiptLineInput {
  po_line_index: number;
  item_id?: string | null;
  item_code?: string | null;
  description: string;
  ordered_qty: number;
  already_received: number;
  qty_received: number;
  qty_rejected: number;
  unit_of_measure: string;
  inspection_notes: string;
}

export function GoodsReceiptModal({
  isOpen,
  onClose,
  onSuccess,
  preselectedPOId,
  preselectedPONumber,
  preselectedLines,
}: GoodsReceiptModalProps) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [availablePOs, setAvailablePOs] = useState<any[]>([]);
  const [selectedPOId, setSelectedPOId] = useState<string>(preselectedPOId || "");
  const [isLoadingPOs, setIsLoadingPOs] = useState(false);

  // Form fields
  const [receivedDate, setReceivedDate] = useState(new Date().toISOString().slice(0, 10));
  const [receivedBy, setReceivedBy] = useState("Dock Quality Inspector");
  const [deliveryNoteRef, setDeliveryNoteRef] = useState("");
  const [carrier, setCarrier] = useState("Express Freight Logistics");
  const [notes, setNotes] = useState("");
  const [autoConfirm, setAutoConfirm] = useState(true);

  // Line items
  const [receiptLines, setReceiptLines] = useState<ReceiptLineInput[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load POs if not preselected
  useEffect(() => {
    if (!isOpen) return;

    if (preselectedPOId && preselectedLines) {
      setSelectedPOId(preselectedPOId);
      const lines: ReceiptLineInput[] = preselectedLines.map((l: any, idx: number) => {
        const ordered = parseFloat(l.quantity) || 1;
        const already = parseFloat(l.qty_received) || 0;
        const pending = Math.max(0, ordered - already);
        return {
          po_line_index: l.po_line_index ?? idx,
          item_id: l.item_id || null,
          item_code: l.item_code || null,
          description: l.description || "Supply item",
          ordered_qty: ordered,
          already_received: already,
          qty_received: pending > 0 ? pending : ordered,
          qty_rejected: 0,
          unit_of_measure: l.unit_of_measure || "each",
          inspection_notes: "Inspected at receiving dock. Meets quality standards.",
        };
      });
      setReceiptLines(lines);
      return;
    }

    let isMounted = true;
    async function fetchReceivablePOs() {
      setIsLoadingPOs(true);
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        const res = await fetch("/api/v1/purchase-orders?limit=100", { headers });
        if (res.ok && isMounted) {
          const data = await res.json();
          // Filter receivable POs
          const receivable = (data.items || []).filter((po: any) =>
            ["approved", "sent", "acknowledged", "partially_received"].includes(
              po.status.toLowerCase()
            )
          );
          setAvailablePOs(receivable);
          if (receivable.length > 0 && !selectedPOId) {
            handleSelectPO(receivable[0].id, receivable);
          }
        }
      } catch (err) {
        console.error("Failed to load POs:", err);
      } finally {
        if (isMounted) setIsLoadingPOs(false);
      }
    }

    fetchReceivablePOs();
    return () => {
      isMounted = false;
    };
  }, [isOpen, preselectedPOId, preselectedLines, orgId, getToken]);

  const handleSelectPO = (poId: string, poList = availablePOs) => {
    setSelectedPOId(poId);
    const found = poList.find((p) => p.id === poId);
    if (!found) return;

    const lines: ReceiptLineInput[] = (found.line_items || []).map((l: any, idx: number) => {
      const ordered = parseFloat(l.quantity) || 1;
      const already = parseFloat(l.qty_received) || 0;
      const pending = Math.max(0, ordered - already);
      return {
        po_line_index: l.po_line_index ?? idx,
        item_id: l.item_id || null,
        item_code: l.item_code || null,
        description: l.description || "Supply item",
        ordered_qty: ordered,
        already_received: already,
        qty_received: pending > 0 ? pending : ordered,
        qty_rejected: 0,
        unit_of_measure: l.unit_of_measure || "each",
        inspection_notes: "Inspected at receiving dock. Meets quality standards.",
      };
    });
    setReceiptLines(lines);
  };

  if (!isOpen) return null;

  const handleLineQtyChange = (
    idx: number,
    field: "qty_received" | "qty_rejected" | "inspection_notes",
    val: any
  ) => {
    const updated = [...receiptLines];
    updated[idx] = { ...updated[idx], [field]: val };
    setReceiptLines(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedPOId) {
      setErrorMessage("Please select a Purchase Order to receive goods against.");
      return;
    }

    const totalRec = receiptLines.reduce((acc, l) => acc + (l.qty_received || 0), 0);
    if (totalRec <= 0) {
      setErrorMessage("You must record a received quantity greater than 0.");
      return;
    }

    setIsSubmitting(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        purchase_order_id: selectedPOId,
        received_date: receivedDate,
        received_by: receivedBy || null,
        delivery_note_ref: deliveryNoteRef || null,
        carrier: carrier || null,
        notes: notes || null,
        auto_confirm: autoConfirm,
        line_items: receiptLines.map((l) => ({
          po_line_index: l.po_line_index,
          item_id: l.item_id || null,
          item_code: l.item_code || null,
          description: l.description,
          qty_received: Number(l.qty_received),
          qty_rejected: Number(l.qty_rejected || 0),
          unit_of_measure: l.unit_of_measure,
          inspection_notes: l.inspection_notes || null,
        })),
      };

      const res = await fetch("/api/v1/goods-receipts", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to record goods receipt.");
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to submit goods receipt.");
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
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <PackageCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-neutral-900">
                Record Goods Receipt Note (GRN)
              </h2>
              <p className="text-xs text-neutral-500">
                Verify physical package delivery, inspection and inventory intake
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

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {/* Target Purchase Order */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Purchase Order <span className="text-rose-500">*</span>
              </label>
              {preselectedPONumber ? (
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 font-mono text-xs font-bold text-neutral-800">
                  {preselectedPONumber}
                </div>
              ) : isLoadingPOs ? (
                <div className="flex items-center gap-2 py-2 text-xs text-neutral-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading orders...
                </div>
              ) : (
                <select
                  value={selectedPOId}
                  onChange={(e) => handleSelectPO(e.target.value)}
                  className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-900 focus:border-neutral-900 focus:outline-none font-mono"
                  required
                >
                  <option value="" disabled>Select Purchase Order</option>
                  {availablePOs.map((po) => (
                    <option key={po.id} value={po.id}>
                      {po.po_number} — {po.company_name} (${po.total_amount})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Receipt Date
              </label>
              <Input
                type="date"
                value={receivedDate}
                onChange={(e) => setReceivedDate(e.target.value)}
                className="text-xs border-neutral-200"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Delivery Note / Bill of Lading
              </label>
              <Input
                placeholder="e.g. DN-98421"
                value={deliveryNoteRef}
                onChange={(e) => setDeliveryNoteRef(e.target.value)}
                className="text-xs border-neutral-200 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Carrier / Logistics Provider
              </label>
              <Input
                placeholder="e.g. DHL Express, Maersk"
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                className="text-xs border-neutral-200"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Receiving Inspector / Dock
              </label>
              <Input
                value={receivedBy}
                onChange={(e) => setReceivedBy(e.target.value)}
                className="text-xs border-neutral-200"
              />
            </div>
          </div>

          {/* Line item receipt verification */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-neutral-700">
                Delivered Items & Quality Inspection
              </label>
              <span className="text-[11px] text-neutral-500 font-mono">
                {receiptLines.length} Item(s)
              </span>
            </div>

            <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
              {receiptLines.map((line, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-neutral-200 bg-neutral-50/50 p-3 text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-neutral-900">{line.description}</span>
                      {line.item_code && (
                        <span className="ml-2 font-mono text-[10px] text-neutral-400">
                          SKU: {line.item_code}
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-neutral-500 text-[11px]">
                      Ordered: <strong>{line.ordered_qty}</strong> | Already Received: <strong>{line.already_received}</strong>
                    </div>
                  </div>

                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-6 sm:col-span-3">
                      <label className="text-[10px] uppercase font-bold text-neutral-500 block mb-0.5">
                        Qty Received *
                      </label>
                      <Input
                        type="number"
                        step="any"
                        min="0"
                        value={line.qty_received}
                        onChange={(e) =>
                          handleLineQtyChange(idx, "qty_received", parseFloat(e.target.value) || 0)
                        }
                        className="text-xs bg-white border-neutral-200 font-mono"
                        required
                      />
                    </div>

                    <div className="col-span-6 sm:col-span-3">
                      <label className="text-[10px] uppercase font-bold text-neutral-500 block mb-0.5">
                        Qty Rejected
                      </label>
                      <Input
                        type="number"
                        step="any"
                        min="0"
                        value={line.qty_rejected}
                        onChange={(e) =>
                          handleLineQtyChange(idx, "qty_rejected", parseFloat(e.target.value) || 0)
                        }
                        className="text-xs bg-white border-neutral-200 font-mono text-rose-600"
                      />
                    </div>

                    <div className="col-span-12 sm:col-span-6">
                      <label className="text-[10px] uppercase font-bold text-neutral-500 block mb-0.5">
                        Inspection Notes
                      </label>
                      <Input
                        value={line.inspection_notes}
                        onChange={(e) =>
                          handleLineQtyChange(idx, "inspection_notes", e.target.value)
                        }
                        placeholder="Condition, seal verification, batch #..."
                        className="text-xs bg-white border-neutral-200"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="autoConfirm"
              checked={autoConfirm}
              onChange={(e) => setAutoConfirm(e.target.checked)}
              className="rounded border-neutral-300 text-emerald-600 focus:ring-emerald-600 h-4 w-4"
            />
            <label htmlFor="autoConfirm" className="text-xs text-neutral-700 select-none">
              Immediately confirm inspection and update PO fulfillment status to Received / Partially Received
            </label>
          </div>

          {/* Action buttons */}
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
              className="text-xs bg-emerald-700 text-white hover:bg-emerald-800"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                  Recording Receipt...
                </>
              ) : (
                "Save Goods Receipt Note"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
