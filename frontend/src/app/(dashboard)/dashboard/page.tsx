"use client";

import React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Building2,
  DollarSign,
  Activity,
  Sparkles,
  ExternalLink,
  Layers,
  ChevronRight,
  Eye,
  Flag,
} from "lucide-react";
import { useUIStore } from "@/lib/store/ui-store";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const persona = useUIStore((s) => s.persona);

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

      {/* ── KPI Row (Architecture Part S) ─────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Active Critical Alerts"
          value="4"
          subtitle="2 require immediate review"
          icon={<AlertTriangle className="h-4 w-4" />}
          accent="critical"
          change={{ value: "+2 today", isPositive: false }}
        />
        <MetricCard
          title="Monitored Suppliers"
          value="128"
          subtitle="94 Tier-1 · 34 Sub-tier"
          icon={<Building2 className="h-4 w-4" />}
          accent="blue"
          change={{ value: "+12 seeded", isPositive: true }}
        />
        <MetricCard
          title="Total Spend Exposed"
          value="$14.2M"
          subtitle="Across 3 high-impact jurisdictions"
          icon={<DollarSign className="h-4 w-4" />}
          accent="high"
        />
        <MetricCard
          title="Data Freshness"
          value="100%"
          subtitle="All 9 Tier-1 sources &lt;1h"
          icon={<Activity className="h-4 w-4" />}
          accent="emerald"
          change={{ value: "SLO met", isPositive: true }}
        />
      </div>

      {/* ── Flagship Callout: Regulatory Overlap (Architecture Part S) ──── */}
      <div className="relative overflow-hidden rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent p-6 shadow-glow-amber backdrop-blur-md">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <Badge variant="high" className="font-mono">
                REGULATORY OVERLAP DETECTED
              </Badge>
              <Badge variant="live">LIVE</Badge>
            </div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              Price-Claim Variance coincides with BIS Export Restriction
            </h2>
            <p className="text-xs text-muted-foreground max-w-2xl">
              Supplier <strong className="text-foreground">Apex Micro-Optics (Taiwan)</strong> submitted a
              +14% material surcharge while their sub-tier substrate source was designated under recent
              export restrictions. Immediate resourcing or contract price review recommended.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href="/alerts/alt-2026-0901">
                <Eye className="mr-1.5 h-3.5 w-3.5" />
                View Evidence Chain
              </Link>
            </Button>
            <Button asChild variant="default" size="sm">
              <Link href="/alerts">
                <Flag className="mr-1.5 h-3.5 w-3.5" />
                Escalate
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* ── Active Risk Alerts & Evidence Chain Preview ────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Alerts Feed */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle className="text-base">Active Exposure Alerts</CardTitle>
              <CardDescription>
                External signals with deterministic intersection into your supply graph.
              </CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link href="/alerts" className="text-xs">
                View all (18) <ChevronRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                id: "alt-001",
                severity: "critical" as const,
                title: "OFAC SDN Designation: Global Rare-Earth Logistics Co.",
                jurisdiction: "US / CN",
                supplier: "Apex Micro-Optics (Tier-2 Sub-supplier)",
                spendExposed: "$4.8M",
                source: "OFAC Sanctions List Service",
                sourceType: "live" as const,
                date: "2 hours ago",
              },
              {
                id: "alt-002",
                severity: "high" as const,
                title: "DGFT Public Notice 32/2026: Export quota restricted on Graphite Compounds",
                jurisdiction: "IN",
                supplier: "Bharat Carbon Synthetics Ltd",
                spendExposed: "$3.2M",
                source: "DGFT Trade Notifications",
                sourceType: "live" as const,
                date: "4 hours ago",
              },
              {
                id: "alt-003",
                severity: "needs-review" as const,
                title: "Financial Distress Filing: Sub-tier Wafer Foundry insolvency disclosure",
                jurisdiction: "DE",
                supplier: "Silicon Components GmbH",
                spendExposed: "$1.5M",
                source: "EUR-Lex Official Journal",
                sourceType: "cached" as const,
                date: "1 day ago",
              },
            ].map((alert) => (
              <div
                key={alert.id}
                className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/30 p-3.5 transition-all hover:bg-muted/70 hover:border-border"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={alert.severity}>
                      {alert.severity === "needs-review"
                        ? "Needs Human Judgment"
                        : alert.severity.toUpperCase()}
                    </Badge>
                    <Badge variant={alert.sourceType}>
                      {alert.sourceType.toUpperCase()}
                    </Badge>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {alert.jurisdiction}
                    </span>
                    <span className="text-[11px] text-muted-foreground ml-auto">
                      {alert.date}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                    {alert.title}
                  </h3>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                    <span>
                      Supplier: <strong className="text-foreground">{alert.supplier}</strong>
                    </span>
                    <span>
                      Spend: <strong className="text-foreground">{alert.spendExposed}</strong>
                    </span>
                    <span className="text-[11px]">
                      Source: {alert.source}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 self-end sm:self-center">
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/alerts/${alert.id}`}>
                      View Evidence
                    </Link>
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Persona-Driven Insight Panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {persona === "risk_manager"
                    ? "External Risk Radar"
                    : "Category Recommendations"}
                </CardTitle>
                <Badge variant="secondary" className="capitalize text-[10px]">
                  {persona.replace("_", " ")}
                </Badge>
              </div>
              <CardDescription>
                {persona === "risk_manager"
                  ? "Jurisdictional risk exposure distribution."
                  : "Prescriptive resourcing considerations (recommend only)."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5 text-xs">
              {persona === "risk_manager" ? (
                <>
                  <div className="space-y-2">
                    <div className="flex justify-between font-medium">
                      <span>China / East Asia</span>
                      <span className="font-mono text-destructive">68% Exposure</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: "68%" }} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between font-medium">
                      <span>India / South Asia</span>
                      <span className="font-mono text-amber-500">24% Exposure</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: "24%" }} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between font-medium">
                      <span>European Union</span>
                      <span className="font-mono text-blue-500">8% Exposure</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: "8%" }} />
                    </div>
                  </div>
                  <div className="pt-2">
                    <Button asChild variant="outline" size="sm" className="w-full">
                      <Link href="/graph">
                        <Layers className="mr-1.5 h-3.5 w-3.5" />
                        Explore Network Graph
                      </Link>
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div className="p-3 rounded-lg border border-border/80 bg-muted/40 space-y-1.5">
                    <div className="flex items-center justify-between font-semibold">
                      <span>Semiconductors &amp; Optics</span>
                      <Badge variant="critical">High Urgency</Badge>
                    </div>
                    <p className="text-muted-foreground text-[11px]">
                      Pre-qualify secondary foundry in Vietnam or EU. Surcharge buffer recommended.
                    </p>
                  </div>
                  <div className="p-3 rounded-lg border border-border/80 bg-muted/40 space-y-1.5">
                    <div className="flex items-center justify-between font-semibold">
                      <span>Raw Graphite &amp; Carbon</span>
                      <Badge variant="medium">Medium</Badge>
                    </div>
                    <p className="text-muted-foreground text-[11px]">
                      Consolidate POs before DGFT policy enactment on Oct 15.
                    </p>
                  </div>
                  <div className="pt-2">
                    <Button asChild variant="outline" size="sm" className="w-full">
                      <Link href="/data">
                        <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                        Upload Spend Documents
                      </Link>
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats on Ingestion Engine */}
          <Card className="border-border/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                Official Ingestion Feeds
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">OFAC SLS &amp; Sanctions</span>
                <span className="text-emerald-500 font-medium">Sync: 12m ago</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">GDELT DOC 2.0 (Global News)</span>
                <span className="text-emerald-500 font-medium">Rate: 6s Token Bucket</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">Federal Register &amp; EUR-Lex</span>
                <span className="text-emerald-500 font-medium">Sync: 35m ago</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">India DGFT &amp; data.gov.in</span>
                <span className="text-emerald-500 font-medium">Sync: 50m ago</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
