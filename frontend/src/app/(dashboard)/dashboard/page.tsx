"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  DollarSign,
  Activity,
  Layers,
  ChevronRight,
  Eye,
  RefreshCw,
  Globe,
  CheckCircle2,
  Gauge,
  ShieldAlert,
  Scale,
  ClipboardList,
  Clock,
  TrendingUp,
  Flame,
} from "lucide-react";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
    country: string | null;
    is_verified?: boolean;
    primary_domain?: string | null;
  };
}

interface ReviewItem {
  id: string;
  status: string;
}

interface MaterialRequestSummaryItem {
  id: string;
  status: string;
  total_estimated_amount?: number | null;
}

interface AlertCountsData {
  total: number;
  critical: number;
  investigating: number;
  resolved: number;
}

interface RiskAssessmentItem {
  id: string;
  org_id: string;
  event_id: string;
  company_id: string;
  impact_score: number;
  severity_band: string;
  confidence: number;
  needs_human_judgment: boolean;
  factors: {
    event_severity?: number;
    dependency_strength?: number;
    evidence_quality?: number;
    urgency_multiplier?: number;
    exposure_multiplier?: number;
    inputs?: Record<string, unknown>;
  };
  model_version: string;
  computed_at: string;
  company_name?: string | null;
  event_summary?: string | null;
  event_type?: string | null;
}

interface RiskSummaryData {
  total_assessed: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  below_threshold_count: number;
  average_impact_score: number;
  needs_human_judgment_count: number;
  top_risks: RiskAssessmentItem[];
}

export default function DashboardPage(): React.JSX.Element {
  const orgId = useUserStore((s) => s.orgId);
  const { getToken } = useAppAuth();

  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [pendingReviews, setPendingReviews] = useState<ReviewItem[]>([]);
  const [materialRequests, setMaterialRequests] = useState<MaterialRequestSummaryItem[]>([]);
  const [alertCounts, setAlertCounts] = useState<AlertCountsData>({
    total: 0,
    critical: 0,
    investigating: 0,
    resolved: 0,
  });
  const [riskSummary, setRiskSummary] = useState<RiskSummaryData | null>(null);
  const [healthStatus, setHealthStatus] = useState<string>("ok");
  const [isLoading, setIsLoading] = useState(true);
  const [isRecomputing, setIsRecomputing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      // Fetch all dashboard and analytics data concurrently
      const [supRes, revRes, hRes, riskRes, mrRes, alertCountsRes] = await Promise.all([
        fetch("/api/v1/suppliers?limit=100", { headers }).catch(() => null),
        fetch("/api/v1/entity-reviews?status=pending", { headers }).catch(() => null),
        fetch("/api/v1/health").catch(() => null),
        fetch("/api/v1/risks/summary", { headers }).catch(() => null),
        fetch("/api/v1/material-requests?limit=100", { headers }).catch(() => null),
        fetch("/api/v1/alerts/counts", { headers }).catch(() => null),
      ]);

      // 1. Process live suppliers
      if (supRes && supRes.ok) {
        const supData = await supRes.json();
        setSuppliers(supData.data || []);
      } else {
        setSuppliers([]);
      }

      // 2. Process pending entity reviews
      if (revRes && revRes.ok) {
        const revData = await revRes.json();
        setPendingReviews(revData.data || []);
      } else {
        setPendingReviews([]);
      }

      // 3. Process system health
      if (hRes && hRes.ok) {
        const hData = await hRes.json();
        setHealthStatus(hData.status === "ok" ? "Operational" : "Degraded");
      }

      // 4. Process live deterministic risk engine summary
      if (riskRes && riskRes.ok) {
        const riskData = await riskRes.json();
        setRiskSummary(riskData);
      } else {
        setRiskSummary(null);
      }

      // 5. Process material requests for procurement analytics
      if (mrRes && mrRes.ok) {
        const mrData = await mrRes.json();
        setMaterialRequests(mrData.items || []);
      } else {
        setMaterialRequests([]);
      }

      // 6. Process alert signal counts
      if (alertCountsRes && alertCountsRes.ok) {
        const aData = await alertCountsRes.json();
        setAlertCounts({
          total: aData.total ?? 0,
          critical: aData.critical ?? 0,
          investigating: aData.investigating ?? 0,
          resolved: aData.resolved ?? 0,
        });
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load dashboard intelligence");
    } finally {
      setIsLoading(false);
    }
  }, [orgId, getToken]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleRecompute = async () => {
    setIsRecomputing(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      const res = await fetch("/api/v1/risks/recompute", {
        method: "POST",
        headers,
        body: JSON.stringify({}),
      });
      if (res.ok) {
        await loadDashboardData();
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Recompute failed");
    } finally {
      setIsRecomputing(false);
    }
  };

  // Computed metrics from real database entities
  const computed = useMemo(() => {
    const totalSuppliers = suppliers.length;
    const tier1Count = suppliers.filter((s) => s.tier === 1).length;
    const subTierCount = suppliers.filter((s) => s.tier && s.tier > 1).length;
    const criticalSuppliers = suppliers.filter((s) => (s.criticality ?? 0) >= 4);
    const singleSourceCount = suppliers.filter((s) => s.single_source).length;
    const totalSpend = suppliers.reduce((acc, s) => acc + (s.annual_spend_usd || 0), 0);

    // Dynamic country breakdown from real companies
    const countryMap: Record<string, number> = {};
    suppliers.forEach((s) => {
      const c = s.company.country || "Other";
      countryMap[c] = (countryMap[c] || 0) + 1;
    });

    const countryBreakdown = Object.entries(countryMap)
      .map(([country, count]) => ({
        country,
        count,
        percentage: totalSuppliers > 0 ? Math.round((count / totalSuppliers) * 100) : 0,
      }))
      .sort((a, b) => b.count - a.count);

    return {
      totalSuppliers,
      tier1Count,
      subTierCount,
      criticalCount: criticalSuppliers.length,
      criticalSuppliers,
      singleSourceCount,
      totalSpend,
      countryBreakdown,
    };
  }, [suppliers]);

  // Computed Procurement Requisition Metrics
  const mrMetrics = useMemo(() => {
    const totalCount = materialRequests.length;
    const pendingCount = materialRequests.filter((i) => i.status === "pending_approval").length;
    const approvedCount = materialRequests.filter((i) =>
      ["approved", "ordered", "partially_ordered"].includes(i.status)
    ).length;
    const totalValue = materialRequests.reduce(
      (sum, i) => sum + (i.total_estimated_amount || 0),
      0
    );
    return { totalCount, pendingCount, approvedCount, totalValue };
  }, [materialRequests]);

  return (
    <div className="space-y-8 animate-in fade-in-50 duration-500 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <Gauge className="h-6 w-6 text-[#FA651E]" />
            Enterprise Analytics &amp; Risk Dashboard
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Centralized hub for all multi-tier supply chain analytics, procurement spend pipelines, and deterministic risk telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardData}
            disabled={isLoading}
            className="h-8 text-xs border-neutral-200"
          >
            <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isLoading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-neutral-500 hover:text-neutral-800 text-xs underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── 1. Supplier & Spend Overview KPIs ────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Monitored Suppliers"
          value={isLoading ? "..." : String(computed.totalSuppliers)}
          subtitle={`${computed.tier1Count} Tier-1 · ${computed.subTierCount} Sub-tier`}
          icon={<Gauge className="h-4 w-4" />}
          accent="blue"
          className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs hover:shadow-sm"
        />
        <MetricCard
          title="High Criticality Nodes"
          value={isLoading ? "..." : String(computed.criticalCount)}
          subtitle={`${computed.singleSourceCount} single-source dependencies`}
          icon={<AlertTriangle className="h-4 w-4" />}
          accent="critical"
          className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs hover:shadow-sm"
        />
        <MetricCard
          title="Total Contract Spend"
          value={isLoading ? "..." : `$${(computed.totalSpend / 1000000).toFixed(2)}M`}
          subtitle={`Across ${computed.countryBreakdown.length} jurisdictions`}
          icon={<DollarSign className="h-4 w-4" />}
          accent="high"
          className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs hover:shadow-sm"
        />
        <MetricCard
          title="Pending Entity Reviews"
          value={isLoading ? "..." : String(pendingReviews.length)}
          subtitle={healthStatus === "Operational" ? "Backend Services Healthy" : "System Degraded"}
          icon={<Activity className="h-4 w-4" />}
          accent="emerald"
          className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs hover:shadow-sm"
        />
      </div>

      {/* ── 2. Procurement & Material Requisition Analytics ─────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-[#FA651E]" />
              Procurement &amp; Material Requisition Analytics
            </h2>
            <p className="text-[11px] text-neutral-500">
              Live aggregate metrics across active requisitions, DoA approvals, and spend pipelines.
            </p>
          </div>
          <Button asChild variant="ghost" size="sm" className="h-7 text-xs text-[#FA651E] hover:text-[#E05310]">
            <Link href="/material-requests">
              Open Requisitions Queue <ChevronRight className="ml-1 h-3 w-3" />
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="Total Requisitions"
            value={isLoading ? "..." : String(mrMetrics.totalCount)}
            subtitle="All active requests"
            icon={<ClipboardList className="h-4 w-4 text-[#FA651E]" />}
            accent="default"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="Pending Approval"
            value={isLoading ? "..." : String(mrMetrics.pendingCount)}
            subtitle="Awaiting DoA decision"
            icon={<Clock className="h-4 w-4 text-amber-500" />}
            accent="high"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="Approved / Ordered"
            value={isLoading ? "..." : String(mrMetrics.approvedCount)}
            subtitle="Ready for RFx or PO"
            icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />}
            accent="emerald"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="Est. Requisition Value"
            value={
              isLoading
                ? "..."
                : `$${mrMetrics.totalValue.toLocaleString(undefined, {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                  })}`
            }
            subtitle="Aggregate requisition spend"
            icon={<TrendingUp className="h-4 w-4 text-blue-500" />}
            accent="blue"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
        </div>
      </div>

      {/* ── 3. Regulatory Signals & Disruption Alert Analytics ──────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-900 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-500" />
              Disruption Signals &amp; Alert Telemetry
            </h2>
            <p className="text-[11px] text-neutral-500">
              Live status breakdown of multi-tier regulatory and geopolitical exposure signals.
            </p>
          </div>
          <Button asChild variant="ghost" size="sm" className="h-7 text-xs text-[#FA651E] hover:text-[#E05310]">
            <Link href="/alerts">
              View All Alerts <ChevronRight className="ml-1 h-3 w-3" />
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="Total Monitored Signals"
            value={isLoading ? "..." : String(alertCounts.total)}
            subtitle="Active regulatory notices"
            icon={<AlertTriangle className="h-4 w-4 text-[#FA651E]" />}
            accent="default"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="Critical Shocks"
            value={isLoading ? "..." : String(alertCounts.critical)}
            subtitle="Immediate operational impact"
            icon={<Flame className="h-4 w-4 text-rose-500" />}
            accent="critical"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="In Investigation"
            value={isLoading ? "..." : String(alertCounts.investigating)}
            subtitle="Active root-cause triage"
            icon={<Activity className="h-4 w-4 text-amber-500" />}
            accent="high"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
          <MetricCard
            title="Resolved Signals"
            value={isLoading ? "..." : String(alertCounts.resolved)}
            subtitle="Mitigations applied & verified"
            icon={<CheckCircle2 className="h-4 w-4 text-emerald-500" />}
            accent="emerald"
            className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs"
          />
        </div>
      </div>

      {/* ── 4. Deterministic Risk Engine Telemetry ───────────────────── */}
      <Card className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-neutral-100 gap-3">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base text-neutral-950 font-bold">
                Deterministic Risk Engine
              </CardTitle>
              <Badge variant="secondary" className="rounded-full px-2 text-[10px] font-mono uppercase bg-neutral-100 text-neutral-600">
                Phase 11 · Multiplicative Formula
              </Badge>
            </div>
            <CardDescription className="text-xs text-neutral-500 mt-1">
              Deterministic mathematical scoring: Event Severity × Dependency × Evidence Quality × Urgency × Spend Exposure.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecompute}
              disabled={isRecomputing || isLoading}
              className="rounded-xl border-neutral-200 text-xs shadow-2xs hover:bg-neutral-50"
            >
              <RefreshCw className={cn("mr-1.5 h-3.5 w-3.5", isRecomputing && "animate-spin")} />
              {isRecomputing ? "Recomputing..." : "Run Recompute Scan"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          {isLoading ? (
            <div className="py-6 text-center text-xs text-neutral-400">
              <RefreshCw className="h-4 w-4 animate-spin mx-auto mb-2 text-[#FA651E]" />
              Querying risk model assessments...
            </div>
          ) : !riskSummary || riskSummary.total_assessed === 0 ? (
            <div className="py-8 text-center text-neutral-500 space-y-2">
              <Scale className="h-8 w-8 text-neutral-400 mx-auto" />
              <p className="text-sm font-semibold text-neutral-900">No Risk Assessments Computed Yet</p>
              <p className="text-xs max-w-md mx-auto text-neutral-500">
                External regulatory events will intersect with your supplier topology to deterministically calculate exposure. Click Recompute to scan active events.
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRecompute}
                disabled={isRecomputing}
                className="mt-2 rounded-xl border-neutral-200"
              >
                Trigger First Risk Calculation
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary Stats Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-1">
                <div className="rounded-xl bg-neutral-50 border border-neutral-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-neutral-500">Total Assessed</span>
                  <p className="text-lg font-bold text-neutral-950 font-mono mt-0.5">{riskSummary.total_assessed}</p>
                </div>
                <div className="rounded-xl bg-neutral-50 border border-neutral-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-neutral-500">Avg Impact</span>
                  <p className="text-lg font-bold text-[#FA651E] font-mono mt-0.5">{riskSummary.average_impact_score}</p>
                </div>
                <div className="rounded-xl bg-rose-50/60 border border-rose-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-rose-700">Critical (≥75)</span>
                  <p className="text-lg font-bold text-rose-700 font-mono mt-0.5">{riskSummary.critical_count}</p>
                </div>
                <div className="rounded-xl bg-amber-50/60 border border-amber-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-amber-700">High (55–74)</span>
                  <p className="text-lg font-bold text-amber-700 font-mono mt-0.5">{riskSummary.high_count}</p>
                </div>
                <div className="rounded-xl bg-blue-50/60 border border-blue-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-blue-700">Medium (35–54)</span>
                  <p className="text-lg font-bold text-blue-700 font-mono mt-0.5">{riskSummary.medium_count}</p>
                </div>
                <div className="rounded-xl bg-neutral-50 border border-neutral-200/60 p-3">
                  <span className="text-[10px] uppercase font-mono text-neutral-600">Low (&lt;35)</span>
                  <p className="text-lg font-bold text-neutral-700 font-mono mt-0.5">{riskSummary.low_count}</p>
                </div>
              </div>

              {/* Top Assessed Risks with Multiplicative Factor Breakdown */}
              <div className="space-y-2.5 pt-2">
                <span className="text-xs font-semibold text-neutral-700">Highest Exposure Risk Assessments</span>
                {riskSummary.top_risks.map((risk) => (
                  <div
                    key={risk.id}
                    className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 rounded-xl border border-neutral-200/70 bg-neutral-50/50 hover:bg-neutral-100/50 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            risk.severity_band === "CRITICAL"
                              ? "critical"
                              : risk.severity_band === "HIGH"
                              ? "high"
                              : "secondary"
                          }
                          className="text-[10px] font-mono px-2"
                        >
                          {risk.severity_band} · {risk.impact_score}
                        </Badge>
                        <span className="text-xs font-bold text-neutral-900">
                          {risk.company_name || "Supplier Node"}
                        </span>
                        {risk.needs_human_judgment && (
                          <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700 bg-amber-50">
                            Needs Human Judgment
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-neutral-600">
                        {risk.event_summary || `Triggered by ${risk.event_type || "external signal"}`}
                      </p>
                    </div>

                    {/* Factor Breakdown Chips */}
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-neutral-600">
                      <span className="px-2 py-0.5 rounded bg-white border border-neutral-200" title="Event Severity">
                        EvSev: {risk.factors.event_severity ?? "-"}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white border border-neutral-200" title="Dependency Strength">
                        Dep: {risk.factors.dependency_strength ?? "-"}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white border border-neutral-200" title="Evidence Quality">
                        Evi: {risk.factors.evidence_quality ?? "-"}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white border border-neutral-200" title="Urgency Multiplier">
                        Urg: +{risk.factors.urgency_multiplier ?? "-"}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white border border-neutral-200" title="Exposure Multiplier">
                        Exp: {risk.factors.exposure_multiplier ?? "-"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 5. High Exposure Critical Suppliers from Live Database ────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Suppliers with Highest Risk Exposure */}
        <Card className="lg:col-span-2 rounded-2xl border-neutral-200/80 bg-white shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-neutral-100">
            <div>
              <CardTitle className="text-base text-neutral-950 font-bold">
                High-Exposure Supplier Registry
              </CardTitle>
              <CardDescription className="text-xs text-neutral-500">
                Tier-1 and Tier-2 suppliers with Criticality 4 or 5 requiring proactive risk monitoring.
              </CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm" className="rounded-lg text-neutral-600 hover:text-neutral-900">
              <Link href="/suppliers" className="text-xs">
                View all ({computed.totalSuppliers}) <ChevronRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {isLoading ? (
              <div className="py-8 text-center text-xs text-neutral-400">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-[#FA651E]" />
                Loading live supplier risk telemetry...
              </div>
            ) : computed.criticalSuppliers.length === 0 ? (
              <div className="py-10 text-center text-neutral-500 space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto" />
                <p className="text-sm font-semibold text-neutral-900">No Critical Exposures in View</p>
                <p className="text-xs max-w-sm mx-auto text-neutral-500">
                  All active suppliers in your registry are currently classified below Criticality 4, or no suppliers have been registered yet.
                </p>
                <Button asChild size="sm" variant="outline" className="mt-3 rounded-xl border-neutral-200">
                  <Link href="/suppliers">Add Suppliers to Registry</Link>
                </Button>
              </div>
            ) : (
              computed.criticalSuppliers.slice(0, 5).map((sup) => (
                <div
                  key={sup.id}
                  className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-neutral-200/70 bg-neutral-50/50 p-3.5 transition-all hover:bg-neutral-100/60 hover:border-neutral-300"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="critical" className="rounded-full px-2 text-[10px]">
                        CRITICALITY {sup.criticality}/5
                      </Badge>
                      <Badge variant="secondary" className="rounded-full px-2 text-[10px] bg-neutral-200/80">
                        TIER {sup.tier ?? 1}
                      </Badge>
                      {sup.single_source && (
                        <Badge variant="outline" className="rounded-full px-2 text-[10px] border-rose-300 text-rose-600 bg-rose-50">
                          SINGLE SOURCE
                        </Badge>
                      )}
                      <span className="text-[11px] font-mono text-neutral-500">
                        {sup.company.country || "Global"}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-neutral-900 group-hover:text-[#FA651E] transition-colors">
                      {sup.company.legal_name}
                    </h3>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500">
                      <span>
                        Category: <strong className="text-neutral-800">{sup.category || "Unassigned"}</strong>
                      </span>
                      {sup.annual_spend_usd !== null && sup.annual_spend_usd > 0 && (
                        <span>
                          Spend: <strong className="text-neutral-800">${sup.annual_spend_usd.toLocaleString()}</strong>
                        </span>
                      )}
                      <span className="text-[11px]">
                        Source: {sup.source}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 self-end sm:self-center">
                    <Button asChild variant="outline" size="sm" className="rounded-xl border-neutral-200 bg-white hover:bg-neutral-50 shadow-2xs">
                      <Link href={`/suppliers?search=${encodeURIComponent(sup.company.legal_name)}`}>
                        <Eye className="mr-1.5 h-3.5 w-3.5" />
                        View Dossier
                      </Link>
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Live Jurisdictional Exposure Radar & Review Queue */}
        <div className="space-y-6">
          <Card className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs">
            <CardHeader className="pb-3 border-b border-neutral-100">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base text-neutral-950 font-bold">
                  Jurisdictional Exposure
                </CardTitle>
                <Badge variant="secondary" className="capitalize text-[10px] rounded-full">
                  Live Registry
                </Badge>
              </div>
              <CardDescription className="text-xs text-neutral-500">
                Geographic concentration across registered suppliers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5 pt-4 text-xs">
              {computed.countryBreakdown.length === 0 ? (
                <div className="py-6 text-center text-neutral-400">
                  <Globe className="h-6 w-6 mx-auto mb-2 text-neutral-400" />
                  <p className="text-xs">No supplier jurisdictions mapped yet.</p>
                </div>
              ) : (
                computed.countryBreakdown.slice(0, 4).map((item) => (
                  <div key={item.country} className="space-y-1.5">
                    <div className="flex justify-between font-medium text-neutral-700">
                      <span>Jurisdiction: {item.country}</span>
                      <span className="font-mono text-[#FA651E] font-semibold">
                        {item.percentage}% ({item.count} suppliers)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#FA651E] to-[#E03368] rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(item.percentage, 4)}%` }}
                      />
                    </div>
                  </div>
                ))
              )}
              <div className="pt-2">
                <Button asChild variant="outline" size="sm" className="w-full rounded-xl border-neutral-200 bg-white hover:bg-neutral-50 shadow-2xs">
                  <Link href="/graph">
                    <Layers className="mr-1.5 h-3.5 w-3.5" />
                    Explore Network Topology
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Review Queue Card */}
          <Card className="rounded-2xl border-neutral-200/80 bg-white shadow-2xs">
            <CardHeader className="pb-2 border-b border-neutral-100">
              <CardTitle className="text-xs uppercase tracking-wider text-neutral-500 font-bold font-mono">
                Action Items &amp; Review Queue
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 pt-3 text-xs">
              <div className="flex justify-between items-center py-1.5 border-b border-neutral-100">
                <span className="text-neutral-600">Pending Entity Matches</span>
                <Badge variant={pendingReviews.length > 0 ? "high" : "secondary"} className="rounded-full px-2">
                  {pendingReviews.length} to review
                </Badge>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-neutral-100">
                <span className="text-neutral-600">Single-Source Points</span>
                <span className="font-semibold text-neutral-900">{computed.singleSourceCount} suppliers</span>
              </div>
              <div className="pt-2">
                <Button asChild variant="default" size="sm" className="w-full text-xs rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white shadow-2xs">
                  <Link href="/suppliers/reviews">
                    Resolve Entity Matches ({pendingReviews.length})
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
