"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  FileQuestion,
  Check,
  ChevronRight,
  ChevronLeft,
  Calendar,
  Building2,
  Percent,
  Plus,
  Trash2,
  AlertCircle,
  Loader2,
  ShieldAlert,
  Send,
  Save,
  CheckCircle2,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

interface MaterialRequestOption {
  id: string;
  mr_number: string;
  title: string;
  status: string;
  total_estimated_amount?: number | null;
  currency?: string | null;
}

interface SupplierOption {
  id: string;
  legal_name: string;
  country?: string | null;
  tier?: number | null;
  criticality?: number | null;
  category?: string | null;
  risk_score?: number | null;
}

interface CriterionItem {
  criterion: string;
  weight: number;
  description: string;
}

export function RFxCreationWizard() {
  const router = useRouter();
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form State
  const [rfxType, setRfxType] = useState<"rfq" | "rfp" | "rfi" | "rft">("rfq");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("IT & Cloud Infrastructure");
  const [selectedMrId, setSelectedMrId] = useState<string>("");
  const [deadlineDays, setDeadlineDays] = useState(14);
  const [customDeadlineDate, setCustomDeadlineDate] = useState("");

  // Criteria State
  const [criteria, setCriteria] = useState<CriterionItem[]>([
    { criterion: "Price", weight: 40, description: "Total cost and unit pricing competitiveness" },
    { criterion: "Quality", weight: 25, description: "Technical specifications and QA standards compliance" },
    { criterion: "Delivery", weight: 20, description: "Fulfillment speed and lead-time guarantees" },
    { criterion: "Risk", weight: 15, description: "Financial health, geopolitical and sanctions risk rating" },
  ]);

  // Suppliers State
  const [availableSuppliers, setAvailableSuppliers] = useState<SupplierOption[]>([]);
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<string[]>([]);
  const [availableMrs, setAvailableMrs] = useState<MaterialRequestOption[]>([]);
  const [isLoadingReferences, setIsLoadingReferences] = useState(true);

  // Load live reference data: material requests & suppliers
  useEffect(() => {
    let isMounted = true;
    async function fetchReferences() {
      setIsLoadingReferences(true);
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        // Fetch live material requests
        const mrRes = await fetch("/api/v1/material-requests?limit=50", { headers });
        if (mrRes.ok && isMounted) {
          const mrData = await mrRes.json();
          setAvailableMrs(mrData.items || []);
        }

        // Fetch live suppliers from suppliers endpoint
        const supRes = await fetch("/api/v1/suppliers?limit=50", { headers });
        if (supRes.ok && isMounted) {
          const supData = await supRes.json();
          const mapped = (supData.items || []).map((s: any) => ({
            id: s.company_id || s.id,
            legal_name: s.legal_name || s.name,
            country: s.country,
            tier: s.tier,
            criticality: s.criticality,
            category: s.category,
            risk_score: s.composite_risk_score ?? s.active_risk_score,
          }));
          setAvailableSuppliers(mapped);
          // Pre-select top 3 suppliers by default for convenience
          if (mapped.length > 0) {
            setSelectedSupplierIds(mapped.slice(0, 3).map((m: SupplierOption) => m.id));
          }
        }
      } catch (err) {
        console.error("Failed to load reference data", err);
      } finally {
        if (isMounted) setIsLoadingReferences(false);
      }
    }
    fetchReferences();
    return () => {
      isMounted = false;
    };
  }, [orgId, getToken]);

  // When MR is selected, auto-populate title if empty
  const handleSelectMr = (mrId: string) => {
    setSelectedMrId(mrId);
    const found = availableMrs.find((m) => m.id === mrId);
    if (found && !title) {
      setTitle(`${rfxType.toUpperCase()} for ${found.title}`);
    }
  };

  // Criteria calculations
  const totalWeight = criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0);
  const isWeightValid = totalWeight === 100;

  const handleUpdateCriterion = (index: number, field: keyof CriterionItem, val: any) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], [field]: val };
    setCriteria(updated);
  };

  const handleAddCriterion = () => {
    setCriteria([
      ...criteria,
      { criterion: "ESG & Compliance", weight: 10, description: "Regulatory & environmental compliance" },
    ]);
  };

  const handleRemoveCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const toggleSupplier = (supId: string) => {
    setSelectedSupplierIds((prev) =>
      prev.includes(supId) ? prev.filter((id) => id !== supId) : [...prev, supId]
    );
  };

  // Submission handler
  const handleSubmit = async (publishImmediate: boolean) => {
    if (!title.trim()) {
      setErrorMessage("Event title is required.");
      setCurrentStep(1);
      return;
    }
    if (!isWeightValid) {
      setErrorMessage("Evaluation criteria weights must add up to exactly 100%.");
      setCurrentStep(2);
      return;
    }
    if (selectedSupplierIds.length === 0) {
      setErrorMessage("Please select at least one supplier to invite.");
      setCurrentStep(3);
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

      // Calculate deadline
      let submission_deadline: string | null = null;
      if (customDeadlineDate) {
        submission_deadline = new Date(customDeadlineDate).toISOString();
      } else {
        const d = new Date();
        d.setDate(d.getDate() + deadlineDays);
        submission_deadline = d.toISOString();
      }

      const payload = {
        rfx_type: rfxType,
        title: title.trim(),
        description: description.trim() || null,
        material_request_id: selectedMrId || null,
        category: category || null,
        evaluation_criteria: criteria.map((c) => ({
          criterion: c.criterion,
          weight: Number(c.weight),
          description: c.description || null,
        })),
        submission_deadline,
        supplier_ids: selectedSupplierIds,
      };

      const res = await fetch("/api/v1/rfx", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to create RFx event");
      }

      const created = await res.json();

      if (publishImmediate && created.id) {
        await fetch(`/api/v1/rfx/${created.id}/publish`, {
          method: "POST",
          headers,
        });
      }

      router.push(`/rfx/${created.id}`);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Error creating sourcing event");
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    { number: 1, label: "Event Scope" },
    { number: 2, label: "Evaluation Criteria" },
    { number: 3, label: "Supplier Invitations" },
    { number: 4, label: "Review & Publish" },
  ];

  return (
    <div className="space-y-6">
      {/* Step Indicator Header */}
      <div className="rounded-xl border border-neutral-200/80 bg-white/90 backdrop-blur-md p-4 shadow-xs">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          {steps.map((st, idx) => (
            <React.Fragment key={st.number}>
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-all",
                    currentStep === st.number
                      ? "bg-[#FA651E] text-white shadow-xs"
                      : currentStep > st.number
                      ? "bg-emerald-600 text-white"
                      : "bg-neutral-100 text-neutral-400"
                  )}
                >
                  {currentStep > st.number ? <Check className="h-4 w-4" /> : st.number}
                </div>
                <span
                  className={cn(
                    "text-xs hidden sm:inline font-medium",
                    currentStep === st.number ? "text-neutral-900 font-semibold" : "text-neutral-500"
                  )}
                >
                  {st.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div className="flex-1 h-0.5 mx-2 sm:mx-4 bg-neutral-200" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {errorMessage && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
          <div>
            <span className="font-semibold">Notice:</span> {errorMessage}
          </div>
        </div>
      )}

      {/* Step 1: Scope & Basic Info */}
      {currentStep === 1 && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-6 shadow-xs space-y-6 max-w-3xl mx-auto">
          <div>
            <h2 className="text-base font-bold text-neutral-900">Step 1: Event Type & Scope</h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              Select sourcing methodology and define procurement requirements.
            </p>
          </div>

          {/* Sourcing Event Type Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-700">Sourcing Event Type</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                {
                  type: "rfq",
                  name: "RFQ",
                  desc: "Request for Quotation",
                  detail: "Competitive price, lead time & terms for well-defined specs.",
                },
                {
                  type: "rfp",
                  name: "RFP",
                  desc: "Request for Proposal",
                  detail: "Solution approach + commercial proposals for complex scope.",
                },
                {
                  type: "rfi",
                  name: "RFI",
                  desc: "Request for Info",
                  detail: "Market research & capability qualification without buy commitment.",
                },
                {
                  type: "rft",
                  name: "RFT",
                  desc: "Tender / ITT",
                  detail: "Formal competitive bidding with strict specification gates.",
                },
              ].map((opt) => (
                <div
                  key={opt.type}
                  onClick={() => setRfxType(opt.type as any)}
                  className={cn(
                    "rounded-xl border p-3 cursor-pointer transition-all",
                    rfxType === opt.type
                      ? "border-[#FA651E] bg-[#FFF2EB]/40 ring-1 ring-[#FA651E]"
                      : "border-neutral-200 hover:border-neutral-300 bg-white"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-neutral-900">{opt.name}</span>
                    {rfxType === opt.type && <Check className="h-3.5 w-3.5 text-[#FA651E]" />}
                  </div>
                  <div className="text-[11px] font-medium text-neutral-600 mt-1">{opt.desc}</div>
                  <div className="text-[10px] text-neutral-400 mt-1 leading-snug">{opt.detail}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Link to Approved Material Request */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700 flex items-center gap-1.5">
              <span>Link Purchase Requisition (Optional)</span>
              <span className="text-[10px] text-neutral-400 font-normal">
                Auto-links item specs & approvals
              </span>
            </label>
            <select
              value={selectedMrId}
              onChange={(e) => handleSelectMr(e.target.value)}
              className="w-full h-9 rounded-lg border border-neutral-200 bg-white px-3 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400"
            >
              <option value="">-- No linked requisition (standalone sourcing) --</option>
              {availableMrs.map((mr) => (
                <option key={mr.id} value={mr.id}>
                  {mr.mr_number} — {mr.title} ({mr.status.replace("_", " ")})
                  {mr.total_estimated_amount ? ` ~ ${mr.currency || "USD"} ${mr.total_estimated_amount.toLocaleString()}` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700">
              Event Title <span className="text-red-500">*</span>
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Sourcing 500x Stainless Steel Sheets 304 or Core Switch Infrastructure"
              className="h-9 text-xs"
            />
          </div>

          {/* Category & Deadline Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full h-9 rounded-lg border border-neutral-200 bg-white px-3 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400"
              >
                <option value="IT & Cloud Infrastructure">IT & Cloud Infrastructure</option>
                <option value="Raw Materials & Metals">Raw Materials & Metals</option>
                <option value="Packaging & Warehousing">Packaging & Warehousing</option>
                <option value="Electronics & Components">Electronics & Components</option>
                <option value="Logistics & Freight Services">Logistics & Freight Services</option>
                <option value="Facilities & Industrial Supplies">Facilities & Industrial Supplies</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-700">Submission Window</label>
              <select
                value={deadlineDays}
                onChange={(e) => setDeadlineDays(Number(e.target.value))}
                className="w-full h-9 rounded-lg border border-neutral-200 bg-white px-3 text-xs text-neutral-800 focus:outline-none focus:ring-1 focus:ring-neutral-400"
              >
                <option value={7}>7 Days (Fast-track RFQ)</option>
                <option value={14}>14 Days (Standard sourcing cycle)</option>
                <option value={21}>21 Days (Complex RFP / solutions)</option>
                <option value={30}>30 Days (Global / Public tender)</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-700">Scope of Work & Notes</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Detail line-item tolerances, required delivery locations, Incoterms, and certifications needed..."
              className="text-xs resize-none"
            />
          </div>

          <div className="flex justify-end pt-2">
            <Button
              onClick={() => {
                if (!title.trim()) {
                  setErrorMessage("Please enter an event title before continuing.");
                  return;
                }
                setErrorMessage(null);
                setCurrentStep(2);
              }}
              className="bg-neutral-900 hover:bg-neutral-800 text-white text-xs h-8 px-4"
            >
              Continue to Criteria
              <ChevronRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Evaluation Criteria Matrix */}
      {currentStep === 2 && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-6 shadow-xs space-y-6 max-w-3xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-neutral-900">Step 2: Weighted Evaluation Criteria</h2>
              <p className="text-xs text-neutral-500 mt-0.5">
                The comparison engine uses these weights to deterministically rank incoming quotes.
              </p>
            </div>
            <div
              className={cn(
                "px-3 py-1 rounded-full text-xs font-mono font-bold border",
                isWeightValid
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : "bg-rose-50 text-rose-700 border-rose-300"
              )}
            >
              Total Weight: {totalWeight}% {isWeightValid ? "✓" : "(Must equal 100%)"}
            </div>
          </div>

          <div className="space-y-3">
            {criteria.map((item, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-neutral-200 bg-neutral-50/50 p-3.5 space-y-2"
              >
                <div className="flex items-center gap-3">
                  <div className="w-1/3">
                    <Input
                      value={item.criterion}
                      onChange={(e) => handleUpdateCriterion(idx, "criterion", e.target.value)}
                      placeholder="Criterion name"
                      className="h-8 text-xs font-semibold bg-white"
                    />
                  </div>
                  <div className="w-28 flex items-center gap-1">
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      value={item.weight}
                      onChange={(e) => handleUpdateCriterion(idx, "weight", e.target.value)}
                      className="h-8 text-xs font-mono text-right bg-white"
                    />
                    <span className="text-xs text-neutral-500 font-bold">%</span>
                  </div>
                  <div className="flex-1">
                    <Input
                      value={item.description}
                      onChange={(e) => handleUpdateCriterion(idx, "description", e.target.value)}
                      placeholder="Guidance or scoring methodology..."
                      className="h-8 text-xs bg-white text-neutral-600"
                    />
                  </div>
                  {criteria.length > 2 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRemoveCriterion(idx)}
                      className="h-8 w-8 p-0 text-neutral-400 hover:text-rose-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleAddCriterion}
              className="text-xs h-8 border-dashed border-neutral-300 text-neutral-600"
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Add Evaluation Criterion
            </Button>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(1)}
                className="text-xs h-8"
              >
                <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                Back
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  if (!isWeightValid) {
                    setErrorMessage(`Weights currently sum to ${totalWeight}%. Please adjust so they equal 100%.`);
                    return;
                  }
                  setErrorMessage(null);
                  setCurrentStep(3);
                }}
                className="bg-neutral-900 hover:bg-neutral-800 text-white text-xs h-8 px-4"
              >
                Continue to Suppliers
                <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Supplier Discovery & Screening */}
      {currentStep === 3 && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-6 shadow-xs space-y-6 max-w-3xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-neutral-900">Step 3: Supplier Selection & Invitations</h2>
              <p className="text-xs text-neutral-500 mt-0.5">
                Invite vetted suppliers from your registry. Active risk alerts are surfaced below.
              </p>
            </div>
            <div className="text-xs font-medium text-neutral-600">
              Selected: <span className="font-bold text-[#FA651E]">{selectedSupplierIds.length}</span> vendors
            </div>
          </div>

          {isLoadingReferences ? (
            <div className="py-12 text-center text-neutral-400">
              <Loader2 className="h-6 w-6 animate-spin mx-auto text-neutral-400 mb-2" />
              <span className="text-xs">Loading approved supplier registry...</span>
            </div>
          ) : availableSuppliers.length === 0 ? (
            <div className="py-10 text-center rounded-xl border border-dashed border-neutral-200 p-6">
              <Building2 className="h-8 w-8 text-neutral-300 mx-auto mb-2" />
              <p className="text-xs font-medium text-neutral-800">No suppliers registered in your tenant graph</p>
              <p className="text-[11px] text-neutral-400 max-w-xs mx-auto mt-1">
                You can add suppliers via the Suppliers module or upload contract master data.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-neutral-100 border border-neutral-200 rounded-xl overflow-hidden max-h-96 overflow-y-auto">
              {availableSuppliers.map((sup) => {
                const isSelected = selectedSupplierIds.includes(sup.id);
                return (
                  <div
                    key={sup.id}
                    onClick={() => toggleSupplier(sup.id)}
                    className={cn(
                      "flex items-center justify-between p-3.5 cursor-pointer transition-colors text-xs",
                      isSelected ? "bg-[#FFF2EB]/30" : "hover:bg-neutral-50/70"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "h-4 w-4 rounded border flex items-center justify-center transition-colors",
                          isSelected
                            ? "border-[#FA651E] bg-[#FA651E] text-white"
                            : "border-neutral-300 bg-white"
                        )}
                      >
                        {isSelected && <Check className="h-3 w-3 stroke-[3]" />}
                      </div>

                      <div>
                        <div className="font-semibold text-neutral-900">{sup.legal_name}</div>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-neutral-500">
                          {sup.country && <span>Country: {sup.country}</span>}
                          {sup.tier && <span>Tier {sup.tier}</span>}
                          {sup.category && <span className="text-neutral-400">• {sup.category}</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {sup.risk_score !== undefined && sup.risk_score !== null && (
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded text-[10px] font-mono font-semibold",
                            sup.risk_score > 60
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : sup.risk_score > 30
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          )}
                        >
                          Risk: {sup.risk_score}/100
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentStep(2)}
              className="text-xs h-8"
            >
              <ChevronLeft className="mr-1 h-3.5 w-3.5" />
              Back
            </Button>
            <Button
              size="sm"
              onClick={() => {
                if (selectedSupplierIds.length === 0) {
                  setErrorMessage("Please select at least 1 supplier to invite before proceeding.");
                  return;
                }
                setErrorMessage(null);
                setCurrentStep(4);
              }}
              className="bg-neutral-900 hover:bg-neutral-800 text-white text-xs h-8 px-4"
            >
              Review & Summary
              <ChevronRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 4: Summary & Publish */}
      {currentStep === 4 && (
        <div className="rounded-xl border border-neutral-200/80 bg-white p-6 shadow-xs space-y-6 max-w-3xl mx-auto">
          <div>
            <h2 className="text-base font-bold text-neutral-900">Step 4: Review Sourcing Package</h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              Confirm specifications and choose to either publish directly or save as draft.
            </p>
          </div>

          <div className="rounded-xl border border-neutral-200 bg-neutral-50/50 p-4 space-y-3.5 text-xs">
            <div className="flex items-start justify-between">
              <div>
                <span className="font-mono text-[10px] uppercase font-bold text-[#FA651E] bg-[#FFF2EB] px-2 py-0.5 rounded">
                  {rfxType.toUpperCase()}
                </span>
                <h3 className="text-sm font-bold text-neutral-900 mt-1">{title}</h3>
                <p className="text-neutral-500 text-[11px] mt-0.5">
                  Category: {category} • Window: {deadlineDays} Days
                </p>
              </div>
            </div>

            {description && (
              <div className="border-t border-neutral-200/70 pt-2 text-neutral-600">
                <span className="font-semibold text-neutral-700">Scope:</span> {description}
              </div>
            )}

            <div className="border-t border-neutral-200/70 pt-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <span className="font-semibold text-neutral-700 block mb-1">
                  Evaluation Criteria Weights:
                </span>
                <div className="space-y-1">
                  {criteria.map((c, idx) => (
                    <div key={idx} className="flex justify-between text-[11px] text-neutral-600">
                      <span>{c.criterion}</span>
                      <span className="font-mono font-bold text-neutral-800">{c.weight}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <span className="font-semibold text-neutral-700 block mb-1">
                  Invited Suppliers ({selectedSupplierIds.length}):
                </span>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {selectedSupplierIds.map((id) => {
                    const sup = availableSuppliers.find((s) => s.id === id);
                    return (
                      <div key={id} className="text-[11px] text-neutral-600 truncate">
                        • {sup ? sup.legal_name : id}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentStep(3)}
              className="text-xs h-8"
              disabled={isSubmitting}
            >
              <ChevronLeft className="mr-1 h-3.5 w-3.5" />
              Back
            </Button>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleSubmit(false)}
                disabled={isSubmitting}
                className="text-xs h-8 border-neutral-300"
              >
                <Save className="mr-1.5 h-3.5 w-3.5" />
                Save Draft
              </Button>
              <Button
                size="sm"
                onClick={() => handleSubmit(true)}
                disabled={isSubmitting}
                className="bg-[#FA651E] hover:bg-[#E05310] text-white text-xs h-8 font-semibold shadow-xs"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Publishing...
                  </>
                ) : (
                  <>
                    <Send className="mr-1.5 h-3.5 w-3.5" />
                    Publish Sourcing Event
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
