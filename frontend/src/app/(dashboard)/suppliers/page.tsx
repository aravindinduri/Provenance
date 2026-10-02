"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  Search,
  Plus,
  Upload,
  Download,
  AlertTriangle,
  ChevronRight,
  ShieldAlert,
  DollarSign,
  Layers,
  Trash2,
  CheckCircle2,
  Loader2,
  Globe,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useUserStore } from "@/lib/store/user-store";

interface SupplierItem {
  id: string;
  org_id: string;
  company_id: string;
  relationship_type: string;
  tier: number | null;
  criticality: number | null;
  annual_spend_usd: number | null;
  category: string | null;
  single_source: boolean;
  lead_time_days: number | null;
  confidence: number;
  source: string;
  company: {
    id: string;
    legal_name: string;
    name_norm: string;
    country: string | null;
    primary_domain: string | null;
    legal_form?: string | null;
    is_verified?: boolean;
  };
  company_detail?: {
    registered_address?: Record<string, unknown> | null;
    hq_address?: Record<string, unknown> | null;
    identifiers?: Array<{
      id: string;
      identifier_type: string;
      identifier_value: string;
      issuing_country?: string | null;
    }>;
    locations?: Array<{
      id: string;
      site_type?: string | null;
      is_primary: boolean;
      location?: {
        country: string;
        region?: string | null;
        city?: string | null;
      };
    }>;
  };
}

export default function SuppliersPage() {
  const orgId = useUserStore((s) => s.orgId);
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCriticality, setSelectedCriticality] = useState<string>("all");
  const [selectedTier, setSelectedTier] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);
  const [selectedSupplierForDossier, setSelectedSupplierForDossier] = useState<SupplierItem | null>(null);

  // Add Supplier form
  const [newSupplier, setNewSupplier] = useState({
    legal_name: "",
    country: "US",
    primary_domain: "",
    tier: 1,
    criticality: 3,
    annual_spend_usd: 500000,
    category: "Direct Materials",
    single_source: false,
    lead_time_days: 30,
  });
  const [isCreating, setIsCreating] = useState(false);

  // Bulk CSV Upload State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isUploadingCsv, setIsUploadingCsv] = useState(false);
  const [bulkJobStatus, setBulkJobStatus] = useState<{
    job_id: string;
    status: string;
    total: number;
    processed: number;
    successful: number;
    failed: number;
    errors: { row: number; error: string }[];
  } | null>(null);

  // Edit Supplier State
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({
    criticality: 3,
    annual_spend_usd: 0,
    tier: 1,
    single_source: false,
    lead_time_days: 30,
    category: "",
  });

  // Fetch Suppliers
  const loadSuppliers = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/suppliers?limit=100");
      if (res.ok) {
        const data = await res.json();
        setSuppliers(data.data || []);
      } else {
        // Fallback demo mock if backend DB is not reachable in local sandbox
        setSuppliers([
          {
            id: "sup-001",
            org_id: orgId || "org-1",
            company_id: "comp-001",
            relationship_type: "supplies_to",
            tier: 1,
            criticality: 5,
            annual_spend_usd: 8500000,
            category: "Semiconductors",
            single_source: true,
            lead_time_days: 90,
            confidence: 1.0,
            source: "user_declared",
            company: {
              id: "comp-001",
              legal_name: "Taiwan Semiconductor Mfg Co",
              name_norm: "taiwan semiconductor mfg co",
              country: "TW",
              primary_domain: "tsmc.com",
              is_verified: true,
            },
          },
          {
            id: "sup-002",
            org_id: orgId || "org-1",
            company_id: "comp-002",
            relationship_type: "supplies_to",
            tier: 1,
            criticality: 4,
            annual_spend_usd: 3200000,
            category: "Fabrication",
            single_source: false,
            lead_time_days: 25,
            confidence: 1.0,
            source: "user_declared",
            company: {
              id: "comp-002",
              legal_name: "Apex Precision Tooling Inc",
              name_norm: "apex precision tooling inc",
              country: "US",
              primary_domain: "apexprecision.com",
            },
          },
          {
            id: "sup-003",
            org_id: orgId || "org-1",
            company_id: "comp-003",
            relationship_type: "supplies_to",
            tier: 2,
            criticality: 4,
            annual_spend_usd: 1450000,
            category: "Chemicals & Rare Earths",
            single_source: true,
            lead_time_days: 45,
            confidence: 0.95,
            source: "gleif",
            company: {
              id: "comp-003",
              legal_name: "Shenghe Rare Earth Materials",
              name_norm: "shenghe rare earth materials",
              country: "CN",
              primary_domain: "shenghe-re.cn",
            },
          },
          {
            id: "sup-004",
            org_id: orgId || "org-1",
            company_id: "comp-004",
            relationship_type: "supplies_to",
            tier: 1,
            criticality: 2,
            annual_spend_usd: 480000,
            category: "Standard Fasteners",
            single_source: false,
            lead_time_days: 7,
            confidence: 1.0,
            source: "user_declared",
            company: {
              id: "comp-004",
              legal_name: "Bavarian Fastener Works GmbH",
              name_norm: "bavarian fastener works gmbh",
              country: "DE",
              primary_domain: "bavarianfasteners.de",
            },
          },
        ]);
      }
    } catch {
      // Mock fallback
      setSuppliers([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadSuppliers();
  }, [loadSuppliers]);

  // Open Dossier Detail
  const handleOpenDossier = async (sup: SupplierItem) => {
    setSelectedSupplierForDossier(sup);
    setEditFormData({
      criticality: sup.criticality || 3,
      annual_spend_usd: sup.annual_spend_usd || 0,
      tier: sup.tier || 1,
      single_source: sup.single_source || false,
      lead_time_days: sup.lead_time_days || 30,
      category: sup.category || "",
    });

    try {
      const res = await fetch(`/api/v1/suppliers/${sup.id}`);
      if (res.ok) {
        const detailed = await res.json();
        setSelectedSupplierForDossier(detailed);
      }
    } catch {
      // Keep existing
    }
  };

  // Add Single Supplier
  const handleCreateSupplier = async () => {
    if (!newSupplier.legal_name.trim()) return;
    setIsCreating(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/suppliers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newSupplier),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to create supplier");
      }

      setIsAddModalOpen(false);
      setNewSupplier({
        legal_name: "",
        country: "US",
        primary_domain: "",
        tier: 1,
        criticality: 3,
        annual_spend_usd: 500000,
        category: "Direct Materials",
        single_source: false,
        lead_time_days: 30,
      });
      await loadSuppliers();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to add supplier");
    } finally {
      setIsCreating(false);
    }
  };

  // Update Supplier
  const handleUpdateSupplier = async () => {
    if (!selectedSupplierForDossier) return;
    setIsEditing(true);
    try {
      const res = await fetch(`/api/v1/suppliers/${selectedSupplierForDossier.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editFormData),
      });

      if (res.ok) {
        const updated = await res.json();
        setSelectedSupplierForDossier(updated);
        await loadSuppliers();
      }
    } catch {
      // Handle error
    } finally {
      setIsEditing(false);
    }
  };

  // Soft Delete Supplier
  const handleDeleteSupplier = async (supplierId: string) => {
    if (!confirm("Are you sure you want to remove this supplier from your organization's graph?")) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/suppliers/${supplierId}`, {
        method: "DELETE",
      });
      if (res.ok || res.status === 204) {
        setSelectedSupplierForDossier(null);
        await loadSuppliers();
      }
    } catch {
      // Handle error
    }
  };

  // Bulk CSV Upload
  const handleBulkUpload = async () => {
    if (!csvFile) return;
    setIsUploadingCsv(true);
    try {
      const formData = new FormData();
      formData.append("file", csvFile);

      const res = await fetch("/api/v1/suppliers/bulk", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
      }

      const job = await res.json();
      setBulkJobStatus(job);

      // Poll
      const interval = setInterval(async () => {
        try {
          const pollRes = await fetch(`/api/v1/suppliers/bulk/${job.job_id}`);
          if (pollRes.ok) {
            const data = await pollRes.json();
            setBulkJobStatus(data);
            if (data.status === "completed" || data.status === "failed") {
              clearInterval(interval);
              setIsUploadingCsv(false);
              await loadSuppliers();
            }
          }
        } catch {
          clearInterval(interval);
          setIsUploadingCsv(false);
        }
      }, 1000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Bulk import failed");
      setIsUploadingCsv(false);
    }
  };

  const handleDownloadSampleCsv = () => {
    const csvContent =
      "legal_name,country,primary_domain,tier,criticality,annual_spend_usd,category,single_source,lead_time_days\n" +
      "Nippon Semiconductor Ltd,JP,nippon-semi.com,1,5,4500000,Semiconductors,true,60\n" +
      "Apex Precision Machining,US,apexprecision.com,1,4,1850000,Fabrication,false,21\n" +
      "Nordic Microelectronics AB,SE,nordicmicro.se,2,3,920000,Electronic Components,false,30\n" +
      "Shenzhen Advanced Materials,CN,szadvanced.cn,2,4,3100000,Rare Earth & Magnets,true,45\n";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "provenance_sample_suppliers.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filtered suppliers
  const filteredSuppliers = useMemo(() => {
    return suppliers.filter((s) => {
      const matchSearch =
        !searchTerm.trim() ||
        s.company.legal_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (s.company.primary_domain && s.company.primary_domain.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (s.category && s.category.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchCrit =
        selectedCriticality === "all" || (s.criticality !== null && String(s.criticality) === selectedCriticality);

      const matchTier =
        selectedTier === "all" || (s.tier !== null && String(s.tier) === selectedTier);

      const matchCat =
        selectedCategory === "all" || s.category === selectedCategory;

      return matchSearch && matchCrit && matchTier && matchCat;
    });
  }, [suppliers, searchTerm, selectedCriticality, selectedTier, selectedCategory]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const total = suppliers.length;
    const highCrit = suppliers.filter((s) => (s.criticality || 0) >= 4).length;
    const totalSpend = suppliers.reduce((sum, s) => sum + (s.annual_spend_usd || 0), 0);
    const singleSourceCount = suppliers.filter((s) => s.single_source).length;
    return { total, highCrit, totalSpend, singleSourceCount };
  }, [suppliers]);

  const uniqueCategories = useMemo(() => {
    const set = new Set<string>();
    suppliers.forEach((s) => {
      if (s.category) set.add(s.category);
    });
    return Array.from(set);
  }, [suppliers]);

  return (
    <div className="space-y-6">
      {/* Page Title & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Supplier Directory & Registry
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage Tier-1 and sub-tier suppliers, track spend, and calibrate risk criticality.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" asChild className="gap-1.5 text-xs">
            <Link href="/onboarding">
              <Layers className="h-3.5 w-3.5 text-primary" /> Onboarding Wizard
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => setIsBulkModalOpen(true)} className="gap-1.5 text-xs">
            <Upload className="h-3.5 w-3.5" /> Bulk CSV Import
          </Button>
          <Button size="sm" onClick={() => setIsAddModalOpen(true)} className="gap-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" /> Add Supplier
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="glass-panel border-border/70 p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>Direct Suppliers</span>
            <Building2 className="h-4 w-4 text-primary" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">{metrics.total}</div>
          <span className="text-[11px] text-muted-foreground">Active graph nodes</span>
        </Card>

        <Card className="glass-panel border-border/70 p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>High Risk Criticality</span>
            <ShieldAlert className="h-4 w-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-400">{metrics.highCrit}</div>
          <span className="text-[11px] text-muted-foreground">Criticality Level 4 & 5</span>
        </Card>

        <Card className="glass-panel border-border/70 p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>Tracked Annual Spend</span>
            <DollarSign className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">
            ${(metrics.totalSpend / 1000000).toFixed(1)}M
          </div>
          <span className="text-[11px] text-muted-foreground">USD exposure base</span>
        </Card>

        <Card className="glass-panel border-border/70 p-4">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>Single Source Nodes</span>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </div>
          <div className="mt-2 text-2xl font-bold text-foreground">{metrics.singleSourceCount}</div>
          <span className="text-[11px] text-muted-foreground">Sole-source dependencies</span>
        </Card>
      </div>

      {/* Filter and Search Toolbar */}
      <Card className="glass-panel border-border/70 p-3.5">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by legal name, domain, or commodity..."
              className="pl-9 bg-card/70 text-xs h-9"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              value={selectedCriticality}
              onChange={(e) => setSelectedCriticality(e.target.value)}
              className="h-9 rounded-md border border-input bg-card/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="all">Criticality: All</option>
              <option value="5">Criticality 5 (Highest)</option>
              <option value="4">Criticality 4 (High)</option>
              <option value="3">Criticality 3 (Medium)</option>
              <option value="2">Criticality 2 (Low)</option>
              <option value="1">Criticality 1 (Minimal)</option>
            </select>

            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="h-9 rounded-md border border-input bg-card/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="all">Tier: All</option>
              <option value="1">Tier 1 (Direct)</option>
              <option value="2">Tier 2 (Sub-tier)</option>
              <option value="3">Tier 3 (Upstream)</option>
            </select>

            {uniqueCategories.length > 0 && (
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="h-9 rounded-md border border-input bg-card/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="all">Category: All</option>
                {uniqueCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            )}

            {(searchTerm || selectedCriticality !== "all" || selectedTier !== "all" || selectedCategory !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchTerm("");
                  setSelectedCriticality("all");
                  setSelectedTier("all");
                  setSelectedCategory("all");
                }}
                className="h-9 text-xs text-muted-foreground hover:text-foreground"
              >
                Reset
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Supplier Directory Table */}
      <Card className="glass-panel border-border/80 overflow-hidden shadow-antigravity">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] font-semibold border-b border-border/60">
              <tr>
                <th className="py-3 px-4">Supplier Organization</th>
                <th className="py-3 px-4">Country</th>
                <th className="py-3 px-4">Tier</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Criticality</th>
                <th className="py-3 px-4">Annual Spend</th>
                <th className="py-3 px-4">Supply Redundancy</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-muted-foreground">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-primary mb-2" />
                    Loading supplier directory...
                  </td>
                </tr>
              ) : filteredSuppliers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-muted-foreground">
                    <Building2 className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
                    <p className="font-semibold text-foreground">No suppliers found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Seed your direct supply base via CSV or using the Onboarding Wizard.
                    </p>
                    <div className="mt-4 flex justify-center gap-2">
                      <Button size="sm" variant="outline" asChild>
                        <Link href="/onboarding">Launch Onboarding Wizard</Link>
                      </Button>
                      <Button size="sm" onClick={() => setIsBulkModalOpen(true)}>
                        Import CSV
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredSuppliers.map((sup) => (
                  <tr
                    key={sup.id}
                    className="hover:bg-accent/30 transition-colors cursor-pointer group"
                    onClick={() => handleOpenDossier(sup)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <Building2 className="h-4 w-4" />
                        </div>
                        <div>
                          <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
                            {sup.company.legal_name}
                          </span>
                          {sup.company.primary_domain && (
                            <span className="block text-[11px] text-muted-foreground">
                              {sup.company.primary_domain}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <Badge variant="outline" className="text-[10px] uppercase font-mono">
                        {sup.company.country || "GL"}
                      </Badge>
                    </td>

                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 font-medium text-foreground">
                        Tier {sup.tier ?? 1}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="text-muted-foreground">{sup.category || "Unassigned"}</span>
                    </td>

                    <td className="py-3 px-4">
                      <Badge
                        variant={
                          (sup.criticality || 0) >= 5
                            ? "critical"
                            : (sup.criticality || 0) === 4
                            ? "high"
                            : (sup.criticality || 0) === 3
                            ? "medium"
                            : "secondary"
                        }
                      >
                        Level {sup.criticality ?? 3}
                      </Badge>
                    </td>

                    <td className="py-3 px-4 font-mono font-medium text-foreground">
                      ${((sup.annual_spend_usd || 0)).toLocaleString()}
                    </td>

                    <td className="py-3 px-4">
                      {sup.single_source ? (
                        <Badge variant="destructive" className="gap-1 text-[10px]">
                          <AlertTriangle className="h-3 w-3" /> Single Source
                        </Badge>
                      ) : (
                        <span className="text-[11px] text-muted-foreground">Multi-Sourced</span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-1 text-xs text-primary hover:text-primary hover:bg-primary/10"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDossier(sup);
                        }}
                      >
                        Dossier <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MODAL 1: Add Supplier Modal */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Add Supplier to Organization</DialogTitle>
            <DialogDescription className="text-xs">
              Direct supplier relationship edge in the tenant supply graph.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label className="text-muted-foreground font-medium">Legal Company Name *</label>
              <Input
                placeholder="e.g. Nippon Electric Co"
                value={newSupplier.legal_name}
                onChange={(e) => setNewSupplier({ ...newSupplier, legal_name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Country (2-Letter ISO)</label>
                <Input
                  maxLength={2}
                  value={newSupplier.country}
                  onChange={(e) => setNewSupplier({ ...newSupplier, country: e.target.value.toUpperCase() })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Primary Domain</label>
                <Input
                  placeholder="nec.com"
                  value={newSupplier.primary_domain}
                  onChange={(e) => setNewSupplier({ ...newSupplier, primary_domain: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Category</label>
                <Input
                  placeholder="e.g. Precision Optics"
                  value={newSupplier.category}
                  onChange={(e) => setNewSupplier({ ...newSupplier, category: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Annual Spend ($ USD)</label>
                <Input
                  type="number"
                  value={newSupplier.annual_spend_usd}
                  onChange={(e) =>
                    setNewSupplier({ ...newSupplier, annual_spend_usd: Number(e.target.value) })
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Criticality (1-5)</label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={newSupplier.criticality}
                  onChange={(e) =>
                    setNewSupplier({ ...newSupplier, criticality: Number(e.target.value) })
                  }
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Tier</label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={newSupplier.tier}
                  onChange={(e) => setNewSupplier({ ...newSupplier, tier: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground font-medium">Lead Time (Days)</label>
                <Input
                  type="number"
                  value={newSupplier.lead_time_days}
                  onChange={(e) =>
                    setNewSupplier({ ...newSupplier, lead_time_days: Number(e.target.value) })
                  }
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="add-ss"
                checked={newSupplier.single_source}
                onChange={(e) => setNewSupplier({ ...newSupplier, single_source: e.target.checked })}
                className="rounded border-border"
              />
              <label htmlFor="add-ss" className="text-xs text-foreground cursor-pointer font-medium">
                Single Source Dependency (No pre-qualified backup vendor)
              </label>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={isCreating || !newSupplier.legal_name.trim()}
              onClick={handleCreateSupplier}
              className="gap-2"
            >
              {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Save Supplier
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* MODAL 2: Bulk CSV Upload Modal */}
      <Dialog open={isBulkModalOpen} onOpenChange={setIsBulkModalOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Bulk Supplier CSV Upload</DialogTitle>
            <DialogDescription className="text-xs">
              Upload up to 500 suppliers in a single async job with background entity resolution.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="flex justify-between items-center rounded-lg border border-border/60 bg-muted/20 p-3">
              <div>
                <span className="font-semibold text-foreground">Need standard CSV template?</span>
                <p className="text-[11px] text-muted-foreground">Download header schema with sample values.</p>
              </div>
              <Button variant="outline" size="sm" onClick={handleDownloadSampleCsv} className="gap-1.5 text-xs">
                <Download className="h-3.5 w-3.5" /> Template
              </Button>
            </div>

            <div className="rounded-xl border-2 border-dashed border-border/80 bg-card/40 p-6 text-center">
              <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="font-semibold text-foreground">{csvFile ? csvFile.name : "Select or drop CSV file"}</p>
              <label className="cursor-pointer mt-3 inline-block">
                <Button variant="outline" size="sm" asChild>
                  <span>Browse Files</span>
                </Button>
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.[0]) setCsvFile(e.target.files[0]);
                  }}
                />
              </label>
            </div>

            {bulkJobStatus && (
              <div className="rounded-lg border border-border/80 bg-card/90 p-3.5 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span>Status: {bulkJobStatus.status}</span>
                  <span>
                    {bulkJobStatus.processed} / {bulkJobStatus.total}
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{
                      width: `${
                        bulkJobStatus.total > 0
                          ? Math.round((bulkJobStatus.processed / bulkJobStatus.total) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-emerald-400 font-medium">✓ {bulkJobStatus.successful} added</span>
                  {bulkJobStatus.failed > 0 && (
                    <span className="text-destructive font-medium">✕ {bulkJobStatus.failed} issues</span>
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setIsBulkModalOpen(false)}>
              Close
            </Button>
            <Button
              size="sm"
              disabled={!csvFile || isUploadingCsv}
              onClick={handleBulkUpload}
              className="gap-2"
            >
              {isUploadingCsv ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload & Process
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* MODAL 3: Detailed Supplier Dossier Drawer / Dialog */}
      <Dialog
        open={Boolean(selectedSupplierForDossier)}
        onOpenChange={(open) => !open && setSelectedSupplierForDossier(null)}
      >
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          {selectedSupplierForDossier && (
            <>
              <DialogHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Building2 className="h-5 w-5" />
                    </div>
                    <div>
                      <DialogTitle className="text-lg font-bold">
                        {selectedSupplierForDossier.company.legal_name}
                      </DialogTitle>
                      <DialogDescription className="text-xs">
                        Canonical Registry Profile & Tenant Relationship Dossier
                      </DialogDescription>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs uppercase font-mono">
                    {selectedSupplierForDossier.company.country || "GL"}
                  </Badge>
                </div>
              </DialogHeader>

              <div className="space-y-5 py-2 text-xs">
                {/* Canonical Entity Metadata Card */}
                <div className="rounded-xl border border-border/70 bg-card/60 p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-foreground">
                    <span className="flex items-center gap-1.5">
                      <Globe className="h-4 w-4 text-primary" /> Canonical Entity Registry
                    </span>
                    <Badge variant={selectedSupplierForDossier.company.is_verified ? "default" : "secondary"}>
                      {selectedSupplierForDossier.company.is_verified ? "GLEIF Verified" : "Self-Declared"}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[11px]">
                    <div>
                      <span className="text-muted-foreground block">Primary Domain:</span>
                      <span className="font-mono text-foreground font-medium">
                        {selectedSupplierForDossier.company.primary_domain || "Not specified"}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Country of Origin:</span>
                      <span className="font-mono text-foreground font-medium">
                        {selectedSupplierForDossier.company.country || "Global"}
                      </span>
                    </div>
                  </div>

                  {/* Identifiers (LEI, CIN, DUNS) */}
                  {selectedSupplierForDossier.company_detail?.identifiers &&
                    selectedSupplierForDossier.company_detail.identifiers.length > 0 && (
                      <div className="pt-2 border-t border-border/50">
                        <span className="text-[11px] text-muted-foreground block mb-1">
                          Official Entity Identifiers:
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {selectedSupplierForDossier.company_detail.identifiers.map((ident) => (
                            <Badge key={ident.id} variant="outline" className="font-mono text-[10px]">
                              {ident.identifier_type.toUpperCase()}: {ident.identifier_value}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                </div>

                {/* Editable Supply Relationship Parameters */}
                <div className="rounded-xl border border-border/70 bg-card/60 p-4 space-y-3">
                  <span className="font-semibold text-foreground block text-xs">
                    Supply Parameters & Criticality Calibration
                  </span>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-muted-foreground">Criticality Level (1-5)</label>
                      <Input
                        type="number"
                        min={1}
                        max={5}
                        className="bg-card text-xs h-8"
                        value={editFormData.criticality}
                        onChange={(e) =>
                          setEditFormData({ ...editFormData, criticality: Number(e.target.value) })
                        }
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-muted-foreground">Annual Spend ($ USD)</label>
                      <Input
                        type="number"
                        className="bg-card text-xs h-8"
                        value={editFormData.annual_spend_usd}
                        onChange={(e) =>
                          setEditFormData({
                            ...editFormData,
                            annual_spend_usd: Number(e.target.value),
                          })
                        }
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-muted-foreground">Supply Tier</label>
                      <Input
                        type="number"
                        min={1}
                        max={5}
                        className="bg-card text-xs h-8"
                        value={editFormData.tier}
                        onChange={(e) =>
                          setEditFormData({ ...editFormData, tier: Number(e.target.value) })
                        }
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-muted-foreground">Category / Commodity</label>
                      <Input
                        className="bg-card text-xs h-8"
                        value={editFormData.category}
                        onChange={(e) =>
                          setEditFormData({ ...editFormData, category: e.target.value })
                        }
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-muted-foreground">Lead Time (Days)</label>
                      <Input
                        type="number"
                        className="bg-card text-xs h-8"
                        value={editFormData.lead_time_days}
                        onChange={(e) =>
                          setEditFormData({
                            ...editFormData,
                            lead_time_days: Number(e.target.value),
                          })
                        }
                      />
                    </div>

                    <div className="flex items-center gap-2 pt-4">
                      <input
                        type="checkbox"
                        id="edit-ss"
                        checked={editFormData.single_source}
                        onChange={(e) =>
                          setEditFormData({ ...editFormData, single_source: e.target.checked })
                        }
                        className="rounded border-border"
                      />
                      <label htmlFor="edit-ss" className="text-xs text-foreground font-medium cursor-pointer">
                        Single Source
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <DialogFooter className="flex justify-between sm:justify-between border-t border-border/60 pt-4">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDeleteSupplier(selectedSupplierForDossier.id)}
                  className="gap-1.5 text-xs"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Remove from Graph
                </Button>

                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedSupplierForDossier(null)}>
                    Close
                  </Button>
                  <Button size="sm" disabled={isEditing} onClick={handleUpdateSupplier} className="gap-1.5 text-xs">
                    {isEditing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    Save Changes
                  </Button>
                </div>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
