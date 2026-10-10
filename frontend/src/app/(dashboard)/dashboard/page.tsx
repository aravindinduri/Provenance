"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Building2,
  DollarSign,
  Activity,
  Sparkles,
  Layers,
  ChevronRight,
  Eye,
  RefreshCw,
  Globe,
  CheckCircle2,
} from "lucide-react";
import { useUIStore } from "@/lib/store/ui-store";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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

export default function DashboardPage(): React.JSX.Element {
  const persona = useUIStore((s) => s.persona);
  const orgId = useUserStore((s) => s.orgId);
  const { getToken } = useAppAuth();

  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [pendingReviews, setPendingReviews] = useState<ReviewItem[]>([]);
  const [healthStatus, setHealthStatus] = useState<string>("ok");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (orgId) headers["x-org-id"] = orgId;

      // 1. Fetch live suppliers
      const supRes = await fetch("/api/v1/suppliers?limit=100", { headers });
      if (supRes.ok) {
        const supData = await supRes.json();
        setSuppliers(supData.data || []);
      } else {
        setSuppliers([]);
      }

      // 2. Fetch pending entity reviews
      const revRes = await fetch("/api/v1/entity-reviews?status=pending", { headers }).catch(() => null);
      if (revRes && revRes.ok) {
        const revData = await revRes.json();
        setPendingReviews(revData.data || []);
      } else {
        setPendingReviews([]);
      }

      // 3. Fetch system health
      const hRes = await fetch("/api/v1/health").catch(() => null);
      if (hRes && hRes.ok) {
        const hData = await hRes.json();
        setHealthStatus(hData.status === "ok" ? "Operational" : "Degraded");
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

  return (
    <div className="space-y-8 animate-in fade-in-50 duration-500">
      {/* ── Page Header & Persona Context Banner ─────────────────────── */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground lg:text-3xl">
            {persona === "risk_manager"
              ? "Supply Chain Risk Intelligence"
              : "Category Procurement & Sourcing"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {persona === "risk_manager"
              ? "External disruption signals mapped deterministically across multi-tier supplier nodes."
              : "Category exposure, should-cost leakage findings, and supplier diversification actions."}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" onClick={() => loadDashboardData()} disabled={isLoading}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/suppliers">
              <Building2 className="mr-1.5 h-3.5 w-3.5" />
              Manage Suppliers
            </Link>
          </Button>
          <Button asChild variant="glow" size="sm">
            <Link href="/investigate">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Ask Investigation Agent
            </Link>
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-muted-foreground hover:text-foreground text-xs underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── KPI Row Computed from Live Database ──────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Monitored Suppliers"
          value={isLoading ? "..." : String(computed.totalSuppliers)}
          subtitle={`${computed.tier1Count} Tier-1 · ${computed.subTierCount} Sub-tier`}
          icon={<Building2 className="h-4 w-4" />}
          accent="blue"
        />
        <MetricCard
          title="High Criticality Nodes"
          value={isLoading ? "..." : String(computed.criticalCount)}
          subtitle={`${computed.singleSourceCount} single-source dependencies`}
          icon={<AlertTriangle className="h-4 w-4" />}
          accent="critical"
        />
        <MetricCard
          title="Total Contract Spend"
          value={isLoading ? "..." : `$${(computed.totalSpend / 1000000).toFixed(2)}M`}
          subtitle={`Across ${computed.countryBreakdown.length} jurisdictions`}
          icon={<DollarSign className="h-4 w-4" />}
          accent="high"
        />
        <MetricCard
          title="Pending Entity Reviews"
          value={isLoading ? "..." : String(pendingReviews.length)}
          subtitle={healthStatus === "Operational" ? "Backend Services Healthy" : "System Degraded"}
          icon={<Activity className="h-4 w-4" />}
          accent="emerald"
        />
      </div>

      {/* ── High Exposure Critical Suppliers from Live Database ───────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Suppliers with Highest Risk Exposure */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle className="text-base">High-Exposure Supplier Registry</CardTitle>
              <CardDescription>
                Tier-1 and Tier-2 suppliers with Criticality 4 or 5 requiring proactive risk monitoring.
              </CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/suppliers" className="text-xs">
                View all ({computed.totalSuppliers}) <ChevronRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <div className="py-8 text-center text-xs text-muted-foreground">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
                Loading live supplier risk telemetry...
              </div>
            ) : computed.criticalSuppliers.length === 0 ? (
              <div className="py-10 text-center text-muted-foreground space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto" />
                <p className="text-sm font-medium text-foreground">No High-Criticality Exposures</p>
                <p className="text-xs max-w-sm mx-auto">
                  All active suppliers in your registry are currently classified below Criticality 4, or no suppliers have been registered yet.
                </p>
                <Button asChild size="sm" variant="outline" className="mt-3">
                  <Link href="/suppliers">Add Suppliers to Registry</Link>
                </Button>
              </div>
            ) : (
              computed.criticalSuppliers.slice(0, 5).map((sup) => (
                <div
                  key={sup.id}
                  className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/30 p-3.5 transition-all hover:bg-muted/70 hover:border-border"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="critical">
                        CRITICALITY {sup.criticality}/5
                      </Badge>
                      <Badge variant="secondary">
                        TIER {sup.tier ?? 1}
                      </Badge>
                      {sup.single_source && (
                        <Badge variant="outline" className="border-destructive/40 text-destructive text-[10px]">
                          SINGLE SOURCE
                        </Badge>
                      )}
                      <span className="text-[11px] font-mono text-muted-foreground">
                        {sup.company.country || "Global"}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                      {sup.company.legal_name}
                    </h3>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                      <span>
                        Category: <strong className="text-foreground">{sup.category || "Unassigned"}</strong>
                      </span>
                      {sup.annual_spend_usd !== null && sup.annual_spend_usd > 0 && (
                        <span>
                          Spend: <strong className="text-foreground">${sup.annual_spend_usd.toLocaleString()}</strong>
                        </span>
                      )}
                      <span className="text-[11px]">
                        Source: {sup.source}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 self-end sm:self-center">
                    <Button asChild variant="outline" size="sm">
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

        {/* Live Jurisdictional Exposure Radar */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {persona === "risk_manager"
                    ? "Jurisdictional Exposure"
                    : "Sourcing Distribution"}
                </CardTitle>
                <Badge variant="secondary" className="capitalize text-[10px]">
                  Live Registry
                </Badge>
              </div>
              <CardDescription>
                Geographic concentration across registered suppliers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5 text-xs">
              {computed.countryBreakdown.length === 0 ? (
                <div className="py-6 text-center text-muted-foreground">
                  <Globe className="h-6 w-6 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-xs">No supplier jurisdictions mapped yet.</p>
                </div>
              ) : (
                computed.countryBreakdown.slice(0, 4).map((item) => (
                  <div key={item.country} className="space-y-1.5">
                    <div className="flex justify-between font-medium">
                      <span>Jurisdiction: {item.country}</span>
                      <span className="font-mono text-primary font-semibold">
                        {item.percentage}% ({item.count} suppliers)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(item.percentage, 4)}%` }}
                      />
                    </div>
                  </div>
                ))
              )}
              <div className="pt-2">
                <Button asChild variant="outline" size="sm" className="w-full">
                  <Link href="/graph">
                    <Layers className="mr-1.5 h-3.5 w-3.5" />
                    Explore Network Topology
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Quick Links & Review Queue */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                Action Items &amp; Review Queue
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                <span className="text-muted-foreground">Pending Entity Matches</span>
                <Badge variant={pendingReviews.length > 0 ? "high" : "secondary"}>
                  {pendingReviews.length} to review
                </Badge>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                <span className="text-muted-foreground">Single-Source Points</span>
                <span className="font-semibold text-foreground">{computed.singleSourceCount} suppliers</span>
              </div>
              <div className="pt-2">
                <Button asChild variant="default" size="sm" className="w-full text-xs">
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
