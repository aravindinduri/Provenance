"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Package,
  Search,
  Plus,
  Edit2,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Tag,
  DollarSign,
  Clock,
} from "lucide-react";
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
import { DocumentStatusBadge } from "@/components/procurement/document-status-badge";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";

export interface ItemMasterRecord {
  id: string;
  org_id: string;
  item_code: string;
  name: string;
  description?: string | null;
  category?: string | null;
  unit_of_measure?: string | null;
  default_unit_price?: number | null;
  currency?: string | null;
  preferred_supplier_id?: string | null;
  lead_time_days?: number | null;
  min_order_qty?: number | null;
  is_active: boolean;
  created_at: string;
}

export function ItemCatalog({ onItemsLoaded }: { onItemsLoaded?: (items: ItemMasterRecord[]) => void } = {}) {
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [items, setItems] = useState<ItemMasterRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  // Create/Edit Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<ItemMasterRecord | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form values
  const [formItemCode, setFormItemCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formCategory, setFormCategory] = useState("Raw Materials");
  const [formUoM, setFormUoM] = useState("units");
  const [formPrice, setFormPrice] = useState("100.00");
  const [formCurrency, setFormCurrency] = useState("USD");
  const [formLeadTime, setFormLeadTime] = useState("14");
  const [formMinOrder, setFormMinOrder] = useState("1");
  const [formIsActive, setFormIsActive] = useState(true);

  const loadItems = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      let url = "/api/v1/items?limit=100";
      if (searchTerm.trim()) {
        url += `&q=${encodeURIComponent(searchTerm.trim())}`;
      }
      if (selectedCategory !== "all") {
        url += `&category=${encodeURIComponent(selectedCategory)}`;
      }

      const res = await fetch(url, { headers });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load catalog items (HTTP ${res.status})`);
      }

      const data = await res.json();
      const loaded = data.items || [];
      setItems(loaded);
      if (onItemsLoaded) {
        onItemsLoaded(loaded);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load catalog items");
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, searchTerm, selectedCategory, getToken, onItemsLoaded]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const openCreateModal = () => {
    setEditingItem(null);
    setFormItemCode("");
    setFormName("");
    setFormDescription("");
    setFormCategory("Raw Materials");
    setFormUoM("units");
    setFormPrice("100.00");
    setFormCurrency("USD");
    setFormLeadTime("14");
    setFormMinOrder("1");
    setFormIsActive(true);
    setFormError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (item: ItemMasterRecord) => {
    setEditingItem(item);
    setFormItemCode(item.item_code);
    setFormName(item.name);
    setFormDescription(item.description || "");
    setFormCategory(item.category || "General");
    setFormUoM(item.unit_of_measure || "units");
    setFormPrice(item.default_unit_price != null ? String(item.default_unit_price) : "0");
    setFormCurrency(item.currency || "USD");
    setFormLeadTime(item.lead_time_days != null ? String(item.lead_time_days) : "0");
    setFormMinOrder(item.min_order_qty != null ? String(item.min_order_qty) : "1");
    setFormIsActive(item.is_active);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formItemCode.trim() || !formName.trim()) {
      setFormError("Item Code and Name are required");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const payload = {
        item_code: formItemCode.trim(),
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        category: formCategory.trim() || undefined,
        unit_of_measure: formUoM.trim() || undefined,
        default_unit_price: parseFloat(formPrice) || undefined,
        currency: formCurrency,
        lead_time_days: parseInt(formLeadTime, 10) || undefined,
        min_order_qty: parseFloat(formMinOrder) || undefined,
        is_active: formIsActive,
      };

      let res: Response;
      if (editingItem) {
        res = await fetch(`/api/v1/items/${editingItem.id}`, {
          method: "PATCH",
          headers,
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch("/api/v1/items", {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to save item (HTTP ${res.status})`);
      }

      setIsModalOpen(false);
      loadItems();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to save item");
    } finally {
      setIsSubmitting(false);
    }
  };

  const categories = ["all", "Raw Materials", "Components", "Packaging", "MRO", "Finished Goods"];

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-lg px-2.5 py-1 text-xs transition-colors whitespace-nowrap capitalize ${
                selectedCategory === cat
                  ? "bg-neutral-900 text-white font-semibold shadow-2xs"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200/80"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-60">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-neutral-400" />
            <Input
              type="text"
              placeholder="Search code or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 pl-8 text-xs bg-white"
            />
          </div>
          <Button
            size="sm"
            onClick={openCreateModal}
            className="h-8 shrink-0 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs font-medium"
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            Add Item
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Catalog Table */}
      <div className="rounded-xl border border-neutral-200/80 bg-white overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-center text-neutral-400">
            <Loader2 className="h-6 w-6 animate-spin text-[#FA651E] mb-2" />
            <span className="text-xs">Loading items from material master...</span>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-50 text-[#FA651E] mb-3">
              <Package className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-neutral-900">No Items in Catalog</h3>
            <p className="mt-1 max-w-sm text-xs text-neutral-500">
              {searchTerm || selectedCategory !== "all"
                ? "No catalog items match the query."
                : "No items registered yet in your material master. Add your first item to enable catalog selection in Material Requests."}
            </p>
            {!searchTerm && selectedCategory === "all" && (
              <Button
                size="sm"
                onClick={openCreateModal}
                className="mt-4 bg-[#FA651E] hover:bg-[#E05310] text-white text-xs shadow-2xs"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Add First Item
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-neutral-200/80 bg-neutral-50/80 text-neutral-500 font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 font-semibold">Item Code</th>
                  <th className="px-4 py-3 font-semibold">Name &amp; Description</th>
                  <th className="px-3 py-3 font-semibold">Category</th>
                  <th className="px-3 py-3 font-semibold">UoM</th>
                  <th className="px-3 py-3 font-semibold">Lead Time</th>
                  <th className="px-4 py-3 font-semibold text-right">Default Unit Price</th>
                  <th className="px-3 py-3 font-semibold text-center">Status</th>
                  <th className="px-4 py-3 font-semibold text-right">Edit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-neutral-50/60 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-neutral-900">
                      {item.item_code}
                    </td>

                    <td className="px-4 py-3">
                      <div className="font-semibold text-neutral-900">{item.name}</div>
                      {item.description && (
                        <div className="text-[11px] text-neutral-400 line-clamp-1">{item.description}</div>
                      )}
                    </td>

                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1 rounded bg-neutral-100 px-2 py-0.5 text-[11px] text-neutral-700 font-mono">
                        <Tag className="h-2.5 w-2.5" />
                        {item.category || "General"}
                      </span>
                    </td>

                    <td className="px-3 py-3 text-neutral-600 font-mono text-[11px]">
                      {item.unit_of_measure || "units"}
                    </td>

                    <td className="px-3 py-3 text-neutral-600 font-mono text-[11px]">
                      {item.lead_time_days ? (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-neutral-400" />
                          {item.lead_time_days} days
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>

                    <td className="px-4 py-3 text-right font-mono font-bold text-neutral-900">
                      {item.currency || "USD"}{" "}
                      {Number(item.default_unit_price || 0).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>

                    <td className="px-3 py-3 text-center">
                      <DocumentStatusBadge status={item.is_active ? "active" : "inactive"} size="sm" />
                    </td>

                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEditModal(item)}
                        className="h-7 w-7 p-0 text-neutral-400 hover:text-neutral-900"
                        title="Edit Item"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-semibold">
              <Package className="h-4 w-4 text-[#FA651E]" />
              {editingItem ? `Edit Item: ${editingItem.item_code}` : "New Catalog Item"}
            </DialogTitle>
            <DialogDescription className="text-xs text-neutral-500">
              Register standard materials and items into your catalog for automatic pricing and requisitioning.
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSaveItem} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Item Code *</label>
                <Input
                  placeholder="e.g., STL-304-2MM"
                  value={formItemCode}
                  onChange={(e) => setFormItemCode(e.target.value.toUpperCase())}
                  required
                  disabled={!!editingItem}
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Category</label>
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none"
                >
                  <option value="Raw Materials">Raw Materials</option>
                  <option value="Components">Components</option>
                  <option value="Packaging">Packaging</option>
                  <option value="MRO">MRO</option>
                  <option value="Finished Goods">Finished Goods</option>
                </select>
              </div>

              <div className="col-span-2 space-y-1">
                <label className="text-xs font-medium text-neutral-700">Item Name *</label>
                <Input
                  placeholder="e.g., Stainless Steel Sheet 304, 2mm"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
              </div>

              <div className="col-span-2 space-y-1">
                <label className="text-xs font-medium text-neutral-700">Description</label>
                <Textarea
                  placeholder="Technical specifications, dimensions, tolerances..."
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="min-h-16 text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Unit of Measure</label>
                <Input
                  placeholder="e.g., sheets, kg, meters"
                  value={formUoM}
                  onChange={(e) => setFormUoM(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Default Price</label>
                <Input
                  type="number"
                  step="any"
                  placeholder="100.00"
                  value={formPrice}
                  onChange={(e) => setFormPrice(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Currency</label>
                <select
                  value={formCurrency}
                  onChange={(e) => setFormCurrency(e.target.value)}
                  className="w-full h-8 rounded-md border border-neutral-300 bg-white px-2.5 text-xs text-neutral-800 focus:outline-none font-mono"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="INR">INR</option>
                  <option value="GBP">GBP</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-700">Lead Time (Days)</label>
                <Input
                  type="number"
                  placeholder="14"
                  value={formLeadTime}
                  onChange={(e) => setFormLeadTime(e.target.value)}
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="activeItemCheck"
                checked={formIsActive}
                onChange={(e) => setFormIsActive(e.target.checked)}
                className="h-4 w-4 rounded border-neutral-300 text-[#FA651E] focus:ring-[#FA651E]"
              />
              <label htmlFor="activeItemCheck" className="text-xs text-neutral-700">
                Item is Active for Procurement
              </label>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-neutral-100">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmitting}
                className="bg-[#FA651E] hover:bg-[#E05310] text-white shadow-2xs"
              >
                {isSubmitting && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                {editingItem ? "Update Item" : "Create Item"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
