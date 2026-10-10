"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  Flame,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  Clock,
  ExternalLink,
  Search,
  Sparkles,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight,
  Info,
  Check,
  X,
  FileText,
  Building2,
  Globe,
  Tag,
  ArrowUpRight,
  HelpCircle,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { cn } from "@/lib/utils";

interface AlertEvidenceItem {
  id: string;
  evidence_type: string;
  source_name?: string | null;
  source_url?: string | null;
  source_type?: string | null;
  retrieved_at?: string | null;
  excerpt?: string | null;
  display_order?: number;
}

interface AlertActionItem {
  id: string;
  user_id: string;
  action: string;
  note?: string | null;
  created_at: string;
}

interface AlertItem {
  id: string;
  org_id: string;
  risk_assessment_id: string;
  event_id: string;
  company_id: string;
  headline: string;
  explanation?: string | null;
  why_it_matters?: string | null;
  recommendations?: string[] | null;
  severity_band: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  impact_score: number;
  confidence: number;
  needs_human_judgment?: boolean;
  target_personas?: string[];
  category?: string | null;
  status: "new" | "acknowledged" | "investigating" | "escalated" | "dismissed" | "resolved";
  dismissed_reason?: string | null;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
  company_name?: string | null;
  company_country?: string | null;
  company_domain?: string | null;
  evidence?: AlertEvidenceItem[];
  actions?: AlertActionItem[];
}

interface AlertCounts {
  total: number;
  new: number;
  acknowledged: number;
  investigating: number;
  escalated: number;
  resolved: number;
  dismissed: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export default function AlertsPage() {
  const router = useRouter();
  const { getToken } = useAppAuth();
  const orgId = useUserStore((s) => s.orgId);

  // Data states
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [counts, setCounts] = useState<AlertCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [scanNotification, setScanNotification] = useState<string | null>(null);

  // Filtering states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  // Dossier modal state
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Workflow action prompt state
  const [promptAction, setPromptAction] = useState<"dismissed" | "resolved" | null>(null);
  const [promptNote, setPromptNote] = useState("");

  // Helper for auth headers
  const getAuthHeaders = useCallback(
    async (includeJson: boolean = false) => {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (includeJson) headers["Content-Type"] = "application/json";
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;
      return headers;
    },
    [getToken, orgId]
  );

  // Fetch alerts with current filters
  const fetchAlerts = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.append("status", statusFilter);
      if (severityFilter !== "all") params.append("severity", severityFilter);
      if (categoryFilter !== "all") params.append("category", categoryFilter);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());
      params.append("limit", "100");

      const [alertsRes, countsRes] = await Promise.all([
        fetch(`/api/v1/alerts?${params.toString()}`, { headers }),
        fetch("/api/v1/alerts/counts", { headers }),
      ]);

      if (!alertsRes.ok) {
        const err = await alertsRes.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load alerts");
      }

      const alertsData = await alertsRes.json();
      setAlerts(alertsData.data || []);

      if (countsRes.ok) {
        const countsData = await countsRes.json();
        setCounts(countsData);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load alerts");
      setAlerts([]);
    } finally {
      setIsLoading(false);
    }
  }, [orgId, statusFilter, severityFilter, categoryFilter, searchQuery, getAuthHeaders]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Run risk scan over tenant suppliers
  const handleRunScan = async () => {
    setIsScanning(true);
    setScanNotification(null);
    setErrorMsg(null);
    try {
      const headers = await getAuthHeaders(true);
      const res = await fetch("/api/v1/alerts/scan", {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Scan request failed");
      }
      const data = await res.json();
      setScanNotification(data.message || `Scanned suppliers successfully.`);
      await fetchAlerts();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to run risk scan");
    } finally {
      setIsScanning(false);
    }
  };

  // Record workflow action (acknowledge, investigate, escalate, dismiss, resolve)
  const handleAlertAction = async (action: string, note?: string) => {
    if (!selectedAlert) return;
    setActionLoading(true);
    try {
      const headers = await getAuthHeaders(true);
      const res = await fetch(`/api/v1/alerts/${selectedAlert.id}/actions`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          action,
          note: note?.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to record alert action");
      }
      const updatedAlert: AlertItem = await res.json();
      setSelectedAlert(updatedAlert);
      setPromptAction(null);
      setPromptNote("");
      // Update in list
      setAlerts((prev) => prev.map((a) => (a.id === updatedAlert.id ? updatedAlert : a)));
      // Re-fetch counts
      const countsRes = await fetch("/api/v1/alerts/counts", { headers });
      if (countsRes.ok) {
        setCounts(await countsRes.json());
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to execute action");
    } finally {
      setActionLoading(false);
    }
  };

  // Distinct categories available in current list
  const availableCategories = useMemo(() => {
    const set = new Set<string>();
    alerts.forEach((a) => {
      if (a.category) set.add(a.category);
    });
    return Array.from(set);
  }, [alerts]);

  const getSeverityBadgeVariant = (sev: string): "critical" | "high" | "medium" | "low" => {
    const s = sev.toUpperCase();
    if (s === "CRITICAL") return "critical";
    if (s === "HIGH") return "high";
    if (s === "MEDIUM") return "medium";
    return "low";
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "new":
        return <Badge variant="critical">New Signal</Badge>;
      case "acknowledged":
        return <Badge variant="secondary">Acknowledged</Badge>;
      case "investigating":
        return <Badge variant="high">Investigating</Badge>;
      case "escalated":
        return <Badge variant="destructive">Escalated</Badge>;
      case "resolved":
        return <Badge variant="live">Resolved</Badge>;
      case "dismissed":
        return <Badge variant="outline">Dismissed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-amber-500" />
            Alerts & Signal Stream
          </h1>
          <p className="text-sm text-muted-foreground">
            Real-time regulatory, trade sanctions, and supply disruption warnings across your supplier base.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAlerts()}
            disabled={isLoading}
            className="gap-1.5"
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={handleRunScan}
            disabled={isScanning}
            className="gap-1.5 shadow-sm"
          >
            <Sparkles className={cn("h-4 w-4 text-amber-300", isScanning && "animate-spin")} />
            {isScanning ? "Running Risk Scan..." : "Run Risk Scan"}
          </Button>
        </div>
      </div>

      {/* Notifications */}
      {scanNotification && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-600 dark:text-emerald-400">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            <span>{scanNotification}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:bg-emerald-500/20"
            onClick={() => setScanNotification(null)}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            <span>{errorMsg}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:bg-red-500/20"
            onClick={() => setErrorMsg(null)}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {/* Metric Cards KPI Row (Dynamically Computed) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Signals"
          value={counts?.total ?? alerts.length}
          subtitle="Monitored supply chain signals"
          icon={<AlertTriangle className="h-4 w-4" />}
          accent="default"
        />
        <MetricCard
          title="Critical Exposures"
          value={counts?.critical ?? alerts.filter((a) => a.severity_band === "CRITICAL").length}
          subtitle="Immediate operational impact"
          icon={<Flame className="h-4 w-4" />}
          accent="critical"
        />
        <MetricCard
          title="In Investigation"
          value={counts?.investigating ?? alerts.filter((a) => a.status === "investigating").length}
          subtitle="Active root-cause triage"
          icon={<Sparkles className="h-4 w-4" />}
          accent="high"
        />
        <MetricCard
          title="Resolved"
          value={counts?.resolved ?? alerts.filter((a) => a.status === "resolved").length}
          subtitle="Mitigations applied & verified"
          icon={<CheckCircle2 className="h-4 w-4" />}
          accent="emerald"
        />
      </div>

      {/* Filter Toolbar & Status Tabs */}
      <Card className="glass-panel p-4">
        <div className="flex flex-col gap-4">
          {/* Status Tabs */}
          <div className="flex flex-wrap items-center gap-1 border-b border-border/60 pb-3">
            {[
              { id: "all", label: "All Alerts", count: counts?.total ?? alerts.length },
              { id: "new", label: "New Signals", count: counts?.new ?? 0 },
              { id: "acknowledged", label: "Acknowledged", count: counts?.acknowledged ?? 0 },
              { id: "investigating", label: "Investigating", count: counts?.investigating ?? 0 },
              { id: "resolved", label: "Resolved", count: counts?.resolved ?? 0 },
              { id: "dismissed", label: "Dismissed", count: counts?.dismissed ?? 0 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  statusFilter === tab.id
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                <span>{tab.label}</span>
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.2 text-[10px]",
                    statusFilter === tab.id
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {/* Search & Faceted Filter Controls */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search alerts by headline, supplier, or excerpt..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs h-9"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Severity Pill Filter */}
              <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-lg border border-border/40 text-xs">
                <span className="text-[11px] text-muted-foreground px-2">Severity:</span>
                {["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={cn(
                      "px-2 py-0.5 rounded text-[11px] font-medium transition-colors",
                      severityFilter === sev
                        ? "bg-background text-foreground shadow-sm border border-border/60"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {sev === "all" ? "All" : sev}
                  </button>
                ))}
              </div>

              {/* Category Filter if categories exist */}
              {availableCategories.length > 0 && (
                <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-lg border border-border/40 text-xs">
                  <span className="text-[11px] text-muted-foreground px-2">Category:</span>
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="bg-transparent text-[11px] text-foreground border-none outline-none cursor-pointer pr-2"
                  >
                    <option value="all" className="bg-background text-foreground">
                      All Categories
                    </option>
                    {availableCategories.map((cat) => (
                      <option key={cat} value={cat} className="bg-background text-foreground">
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Main Alert List Feed */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-5 w-20" />
                </div>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <div className="flex items-center gap-3 pt-2">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-28" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : alerts.length === 0 ? (
        /* Authentic Empty State — Strict Zero Fake Data Compliance */
        <Card className="glass-panel p-12 text-center border-dashed">
          <CardHeader className="flex flex-col items-center gap-3 pb-2">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              <ShieldCheck className="h-7 w-7" />
            </div>
            <CardTitle className="text-xl">No Active Supply Chain Alerts</CardTitle>
            <CardDescription className="max-w-md mx-auto text-xs leading-relaxed">
              {searchQuery || statusFilter !== "all" || severityFilter !== "all"
                ? "No alerts match your current filter parameters. Try resetting your search or filter pills."
                : "Your monitored suppliers currently have no detected trade sanctions, regulatory filings, or GDELT disruption signals."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-2">
            <p className="text-xs text-muted-foreground/80 max-w-lg mx-auto">
              Provenance continuously evaluates official OFAC SDN lists, Federal Register trade rules, EUR-Lex customs advisories, and global supply signals against your tenant graph.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearchQuery("");
                  setStatusFilter("all");
                  setSeverityFilter("all");
                  setCategoryFilter("all");
                }}
              >
                Clear Filters
              </Button>
              <Button size="sm" onClick={handleRunScan} disabled={isScanning} className="gap-1.5">
                <Sparkles className="h-4 w-4" />
                {isScanning ? "Evaluating Suppliers..." : "Run Diagnostic Risk Scan"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        /* Alert Cards List */
        <div className="space-y-4">
          {alerts.map((alert) => (
            <Card
              key={alert.id}
              className={cn(
                "group relative overflow-hidden transition-all duration-200 hover:shadow-md border-border/80",
                alert.severity_band === "CRITICAL" && "hover:border-red-500/40",
                alert.severity_band === "HIGH" && "hover:border-orange-500/40"
              )}
            >
              <CardContent className="p-5">
                <div className="flex flex-col gap-3">
                  {/* Row 1: Badges & Impact Score */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={getSeverityBadgeVariant(alert.severity_band)}>
                        {alert.severity_band}
                      </Badge>
                      {getStatusBadge(alert.status)}
                      {alert.needs_human_judgment && (
                        <Badge variant="needs-review" className="gap-1">
                          <HelpCircle className="h-3 w-3" />
                          Needs Judgment
                        </Badge>
                      )}
                      {alert.company_name && (
                        <div className="flex items-center gap-1.5 rounded-full border border-border/60 bg-muted/30 px-2.5 py-0.5 text-xs text-muted-foreground">
                          <Building2 className="h-3 w-3" />
                          <span className="font-medium text-foreground">{alert.company_name}</span>
                          {alert.company_country && (
                            <span className="text-[10px] uppercase font-mono text-muted-foreground">
                              ({alert.company_country})
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-foreground">{alert.impact_score}</span>
                        <span>/100 Impact</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        <span>{new Date(alert.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Row 2: Headline */}
                  <div>
                    <h3
                      onClick={() => setSelectedAlert(alert)}
                      className="text-base font-semibold text-foreground hover:text-primary transition-colors cursor-pointer"
                    >
                      {alert.headline}
                    </h3>
                    {alert.explanation && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                        {alert.explanation}
                      </p>
                    )}
                  </div>

                  {/* Row 3: Meta & Actions Footer */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/40 text-xs">
                    <div className="flex flex-wrap items-center gap-3 text-muted-foreground">
                      {alert.category && (
                        <div className="flex items-center gap-1">
                          <Tag className="h-3 w-3" />
                          <span>{alert.category}</span>
                        </div>
                      )}
                      {alert.evidence && alert.evidence.length > 0 && (
                        <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3 w-3" />
                          <span>{alert.evidence.length} Evidence Source(s)</span>
                        </div>
                      )}
                      {alert.actions && alert.actions.length > 0 && (
                        <span>{alert.actions.length} Action Audit Record(s)</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {alert.status === "new" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs gap-1"
                          onClick={async () => {
                            setSelectedAlert(alert);
                            await handleAlertAction("acknowledged");
                          }}
                        >
                          <Check className="h-3.5 w-3.5" />
                          Acknowledge
                        </Button>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-8 text-xs gap-1"
                        onClick={() => setSelectedAlert(alert)}
                      >
                        View Dossier & Evidence
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Alert Dossier & Resolution Dialog */}
      <Dialog open={!!selectedAlert} onOpenChange={(open) => !open && setSelectedAlert(null)}>
        {selectedAlert && (
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={getSeverityBadgeVariant(selectedAlert.severity_band)}>
                  {selectedAlert.severity_band}
                </Badge>
                {getStatusBadge(selectedAlert.status)}
                {selectedAlert.needs_human_judgment && (
                  <Badge variant="needs-review">Needs Human Judgment</Badge>
                )}
                <div className="ml-auto text-xs text-muted-foreground">
                  Score: <strong className="text-foreground">{selectedAlert.impact_score}</strong>/100
                </div>
              </div>
              <DialogTitle className="text-lg leading-snug">{selectedAlert.headline}</DialogTitle>
              <DialogDescription className="text-xs">
                Detected on {new Date(selectedAlert.created_at).toLocaleString()} | Target:{" "}
                <strong className="text-foreground">{selectedAlert.company_name || "Supplier"}</strong>
                {selectedAlert.company_country && ` (${selectedAlert.company_country})`}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5 py-3 text-xs leading-relaxed">
              {/* Section: Explanation & Why it matters */}
              <div className="space-y-3 rounded-lg border border-border/60 bg-muted/20 p-4">
                <div>
                  <h4 className="font-semibold text-foreground mb-1 flex items-center gap-1.5">
                    <Info className="h-3.5 w-3.5 text-primary" />
                    Root Cause & Regulatory Exposure
                  </h4>
                  <p className="text-muted-foreground">{selectedAlert.explanation}</p>
                </div>

                {selectedAlert.why_it_matters && (
                  <div>
                    <h4 className="font-semibold text-foreground mb-1">Why It Matters to Tenant</h4>
                    <p className="text-muted-foreground">{selectedAlert.why_it_matters}</p>
                  </div>
                )}
              </div>

              {/* Section: Recommended Actions */}
              {selectedAlert.recommendations && selectedAlert.recommendations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                    Recommended Mitigations
                  </h4>
                  <ul className="space-y-1.5 pl-2">
                    {selectedAlert.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-muted-foreground">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                          {idx + 1}
                        </span>
                        <span>{typeof rec === "string" ? rec : JSON.stringify(rec)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Section: Evidence Chain (Rule 9 proof) */}
              <div className="space-y-2">
                <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-blue-500" />
                  Supporting Evidence Chain ({selectedAlert.evidence?.length || 0})
                </h4>
                {selectedAlert.evidence && selectedAlert.evidence.length > 0 ? (
                  <div className="space-y-2">
                    {selectedAlert.evidence.map((ev) => (
                      <div
                        key={ev.id}
                        className="rounded-md border border-border/60 bg-background/50 p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-medium text-foreground">{ev.source_name || "Evidence Source"}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {ev.evidence_type}
                          </Badge>
                        </div>
                        {ev.excerpt && (
                          <blockquote className="border-l-2 border-primary/40 pl-2 italic text-muted-foreground text-[11px]">
                            &ldquo;{ev.excerpt}&rdquo;
                          </blockquote>
                        )}
                        {ev.source_url && (
                          <a
                            href={ev.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline pt-0.5"
                          >
                            <span>Open Source Record</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-[11px]">No external evidence rows recorded.</p>
                )}
              </div>

              {/* Section: Action Audit Log */}
              {selectedAlert.actions && selectedAlert.actions.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-foreground flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-amber-500" />
                    Action History & Audit Trail
                  </h4>
                  <div className="space-y-1.5 rounded-md border border-border/40 bg-muted/10 p-2.5">
                    {selectedAlert.actions.map((act) => (
                      <div key={act.id} className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <div>
                          <span className="font-medium capitalize text-foreground">{act.action}</span>
                          {act.note && <span className="ml-1 text-muted-foreground/80">— &ldquo;{act.note}&rdquo;</span>}
                        </div>
                        <span className="text-[10px]">{new Date(act.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Note Prompt (for Dismiss or Resolve) */}
              {promptAction && (
                <div className="rounded-lg border border-border bg-accent/40 p-3 space-y-2">
                  <h5 className="font-semibold text-foreground">
                    {promptAction === "dismissed" ? "Reason for Dismissing Alert" : "Resolution & Mitigation Notes"}
                  </h5>
                  <Input
                    placeholder={
                      promptAction === "dismissed"
                        ? "e.g., Dual sourcing verified, exposure below risk threshold..."
                        : "e.g., Alternative supplier contracted, safety stock increased to 60 days..."
                    }
                    value={promptNote}
                    onChange={(e) => setPromptNote(e.target.value)}
                    className="text-xs h-8"
                  />
                  <div className="flex justify-end gap-2 pt-1">
                    <Button variant="ghost" size="sm" onClick={() => setPromptAction(null)}>
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      disabled={actionLoading}
                      onClick={() => handleAlertAction(promptAction, promptNote)}
                    >
                      {actionLoading ? "Saving..." : `Confirm ${promptAction}`}
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* Workflow Action Buttons Footer */}
            <DialogFooter className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  router.push(`/investigate?q=${encodeURIComponent(`Investigate risk alert: ${selectedAlert.headline}`)}`);
                }}
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                Launch AI Investigation
              </Button>

              <div className="flex flex-wrap items-center gap-2">
                {selectedAlert.status !== "acknowledged" && selectedAlert.status !== "resolved" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={actionLoading}
                    onClick={() => handleAlertAction("acknowledged")}
                  >
                    Acknowledge
                  </Button>
                )}
                {selectedAlert.status !== "investigating" && selectedAlert.status !== "resolved" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={actionLoading}
                    onClick={() => handleAlertAction("investigating")}
                  >
                    Investigating
                  </Button>
                )}
                {selectedAlert.status !== "escalated" && selectedAlert.status !== "resolved" && (
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={actionLoading}
                    onClick={() => handleAlertAction("escalated")}
                  >
                    Escalate
                  </Button>
                )}
                {selectedAlert.status !== "dismissed" && selectedAlert.status !== "resolved" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={actionLoading}
                    onClick={() => setPromptAction("dismissed")}
                  >
                    Dismiss
                  </Button>
                )}
                {selectedAlert.status !== "resolved" && (
                  <Button
                    size="sm"
                    disabled={actionLoading}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => setPromptAction("resolved")}
                  >
                    Resolve Alert
                  </Button>
                )}
              </div>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
