"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  PlusCircle,
  Globe,
  Search,
  AlertTriangle,
  RefreshCw,
  Check,
  ShieldCheck,
  Activity,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAppAuth } from "@/lib/auth/clerk-adapter";

export interface CandidateItem {
  company_id: string;
  legal_name: string;
  country?: string | null;
  primary_domain?: string | null;
  similarity: number;
}

export interface ReviewItem {
  id: string;
  org_id?: string | null;
  raw_name: string;
  context: {
    country?: string | null;
    domain?: string | null;
    [key: string]: unknown;
  };
  candidates: CandidateItem[];
  suggested_company_id?: string | null;
  suggested_company?: {
    id: string;
    legal_name: string;
    country?: string | null;
    primary_domain?: string | null;
  } | null;
  ai_confidence?: number | null;
  ai_reasoning?: string | null;
  status: "pending" | "resolved" | "rejected" | "new_entity";
  resolved_company_id?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

export function EntityReviewQueue(): React.JSX.Element {
  const { getToken } = useAppAuth();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [searchTerm, setSearchTerm] = useState("");
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Playground state
  const [isPlaygroundOpen, setIsPlaygroundOpen] = useState(false);
  const [testName, setTestName] = useState("");
  const [testCountry, setTestCountry] = useState("");
  const [testDomain, setTestDomain] = useState("");
  const [isResolvingTest, setIsResolvingTest] = useState(false);
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);

  const fetchReviews = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const url = statusFilter === "all"
        ? "/api/v1/entity-reviews"
        : `/api/v1/entity-reviews?status=${statusFilter}`;
      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        setReviews(data.data || []);
      } else {
        setReviews([]);
      }
    } catch (err) {
      console.error("Failed to fetch entity reviews:", err);
      setReviews([]);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, getToken]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const handleResolveAction = async (
    reviewId: string,
    action: "match" | "reject" | "create_new",
    companyId?: string
  ) => {
    setActionLoadingId(reviewId);
    try {
      const token = await getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/v1/entity-reviews/${reviewId}/resolve`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          action,
          company_id: companyId,
        }),
      });
      if (res.ok) {
        await fetchReviews();
      }
    } catch (err) {
      console.error("Failed to resolve review item:", err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRunPlaygroundCascade = async () => {
    if (!testName.trim()) return;
    setIsResolvingTest(true);
    setTestResult(null);
    try {
      const res = await fetch("/api/v1/companies/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: testName.trim(),
          country: testCountry.trim() || undefined,
          domain: testDomain.trim() || undefined,
          auto_review: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
      }
    } catch (err) {
      console.error("Failed to resolve test entity:", err);
    } finally {
      setIsResolvingTest(false);
    }
  };

  const filteredReviews = reviews.filter((r) =>
    r.raw_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = reviews.filter((r) => r.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-card/60 backdrop-blur-xl border border-border/60 shadow-subtle hover:border-primary/40 transition-smooth">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Pending Reviews
            </span>
            <AlertTriangle className="h-4 w-4 text-amber-500 animate-pulse" />
          </div>
          <p className="mt-2 text-2xl font-bold font-mono text-foreground">
            {pendingCount}
          </p>
          <span className="text-[11px] text-muted-foreground">
            Awaiting human adjudication
          </span>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-xl border border-border/60 shadow-subtle hover:border-primary/40 transition-smooth">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              AI Service
            </span>
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <p className="mt-2 text-2xl font-bold font-mono text-foreground">
            Google Gemini
          </p>
          <span className="text-[11px] text-muted-foreground">
            Interchangeable (Stage 6 Agent)
          </span>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-xl border border-border/60 shadow-subtle hover:border-primary/40 transition-smooth">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Pre-Filter Efficiency
            </span>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="mt-2 text-2xl font-bold font-mono text-emerald-500">
            ≥ 80%
          </p>
          <span className="text-[11px] text-muted-foreground">
            Resolved deterministically (Stages 1-5)
          </span>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-xl border border-border/60 shadow-subtle hover:border-primary/40 transition-smooth flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Test Resolution
            </span>
            <Activity className="h-4 w-4 text-blue-500" />
          </div>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 w-full text-xs font-semibold border-primary/30 hover:bg-primary/10"
            onClick={() => setIsPlaygroundOpen(true)}
          >
            Launch ER Playground
          </Button>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-card/40 p-3 rounded-xl border border-border/60">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search raw mentions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 text-xs bg-background/50 border-border/60"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {(["pending", "resolved", "new_entity", "rejected", "all"] as const).map((st) => (
            <Button
              key={st}
              size="sm"
              variant={statusFilter === st ? "default" : "ghost"}
              className="text-xs h-7 px-3 capitalize"
              onClick={() => setStatusFilter(st)}
            >
              {st.replace("_", " ")}
            </Button>
          ))}
          <Button
            size="sm"
            variant="outline"
            className="h-7 w-7 p-0"
            onClick={fetchReviews}
            title="Refresh list"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Reviews List */}
      {isLoading ? (
        <div className="py-16 text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary opacity-60" />
          <p className="mt-3 text-xs text-muted-foreground">Loading resolution review items...</p>
        </div>
      ) : filteredReviews.length === 0 ? (
        <Card className="py-16 text-center border-dashed border-border/80 bg-card/30">
          <CheckCircle2 className="h-10 w-10 mx-auto text-emerald-500/80 mb-3" />
          <h3 className="text-sm font-semibold text-foreground">Review Queue Clean</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
            No items in the review queue matching the selected filter. Ingested entities are matching cleanly or already resolved.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredReviews.map((item) => {
            const isPending = item.status === "pending";
            const isCurrentActing = actionLoadingId === item.id;
            return (
              <Card
                key={item.id}
                className="p-5 bg-card/70 backdrop-blur-xl border border-border/70 shadow-sm hover:border-primary/40 transition-smooth"
              >
                <div className="flex flex-col lg:flex-row gap-6 justify-between">
                  {/* Left Column: Mention & AI Adjudication */}
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-muted text-muted-foreground uppercase">
                        Unresolved Mention
                      </span>
                      <h3 className="text-base font-bold text-foreground tracking-tight">
                        {item.raw_name}
                      </h3>
                      <Badge
                        variant={
                          item.status === "pending"
                            ? "critical"
                            : item.status === "resolved"
                            ? "default"
                            : "secondary"
                        }
                        className="text-[10px] capitalize"
                      >
                        {item.status.replace("_", " ")}
                      </Badge>
                    </div>

                    {/* Metadata Context */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                      {item.context?.country ? (
                        <div className="flex items-center gap-1 font-mono">
                          <Globe className="h-3.5 w-3.5" />
                          <span>Country: {String(item.context.country)}</span>
                        </div>
                      ) : null}
                      {item.context?.domain ? (
                        <div className="flex items-center gap-1 font-mono">
                          <span>Domain: {String(item.context.domain)}</span>
                        </div>
                      ) : null}
                      <span className="text-[11px] text-muted-foreground/60">
                        Queued: {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {/* Gemini AI Recommendation Box */}
                    {item.ai_reasoning && (
                      <div className="mt-3 p-3.5 rounded-lg bg-primary/5 border border-primary/20 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                            <Sparkles className="h-3.5 w-3.5" />
                            <span>Gemini AI Adjudication</span>
                          </div>
                          {item.ai_confidence !== null && item.ai_confidence !== undefined && (
                            <Badge variant="outline" className="text-[10px] font-mono border-primary/30 text-primary">
                              {Math.round(item.ai_confidence * 100)}% Confidence
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-foreground/90 italic leading-relaxed">
                          &ldquo;{item.ai_reasoning}&rdquo;
                        </p>
                        {item.suggested_company && (
                          <div className="text-xs text-muted-foreground flex items-center gap-2 pt-1 border-t border-primary/10">
                            <span>Suggested Canonical Match:</span>
                            <span className="font-semibold text-foreground">
                              {item.suggested_company.legal_name}
                            </span>
                            {item.suggested_company.country && (
                              <span className="font-mono text-[10px] px-1 bg-muted rounded">
                                {item.suggested_company.country}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Right Column: Candidates & Actions */}
                  <div className="w-full lg:w-96 flex flex-col justify-between border-t lg:border-t-0 lg:border-l border-border/60 pt-4 lg:pt-0 lg:pl-6 space-y-4">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                        Top Candidates ({item.candidates?.length || 0})
                      </h4>
                      <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                        {item.candidates && item.candidates.length > 0 ? (
                          item.candidates.map((cand) => (
                            <div
                              key={cand.company_id}
                              className="p-2.5 rounded-lg border border-border/50 bg-background/50 hover:bg-muted/40 transition-smooth flex items-center justify-between text-xs"
                            >
                              <div className="flex flex-col truncate pr-2">
                                <span className="font-semibold text-foreground truncate">
                                  {cand.legal_name}
                                </span>
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  {cand.country || "Global"} • {cand.primary_domain || "No domain"}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono font-bold text-primary">
                                  {Math.round(cand.similarity * 100)}%
                                </span>
                                {isPending && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-6 px-2 text-[10px]"
                                    disabled={isCurrentActing}
                                    onClick={() =>
                                      handleResolveAction(item.id, "match", cand.company_id)
                                    }
                                  >
                                    Match
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-muted-foreground italic py-2">
                            No similarity candidates found in canonical registry.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action Bar for Pending Reviews */}
                    {isPending && (
                      <div className="pt-2 border-t border-border/40 flex flex-wrap gap-2">
                        {item.suggested_company_id && (
                          <Button
                            size="sm"
                            className="text-xs flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
                            disabled={isCurrentActing}
                            onClick={() =>
                              handleResolveAction(
                                item.id,
                                "match",
                                item.suggested_company_id!
                              )
                            }
                          >
                            <Check className="h-3.5 w-3.5 mr-1" />
                            Accept AI Match
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs flex-1 border-border/80 hover:bg-muted"
                          disabled={isCurrentActing}
                          onClick={() => handleResolveAction(item.id, "create_new")}
                        >
                          <PlusCircle className="h-3.5 w-3.5 mr-1 text-emerald-500" />
                          New Company
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-xs text-destructive hover:bg-destructive/10"
                          disabled={isCurrentActing}
                          onClick={() => handleResolveAction(item.id, "reject")}
                        >
                          <XCircle className="h-3.5 w-3.5 mr-1" />
                          Reject
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ER Cascade Interactive Playground Modal */}
      <Dialog open={isPlaygroundOpen} onOpenChange={setIsPlaygroundOpen}>
        <DialogContent className="sm:max-w-xl bg-card border-border/80">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              Entity Resolution Cascade Playground
            </DialogTitle>
            <DialogDescription className="text-xs">
              Test how raw supplier mentions traverse the 7-stage cascade (Stages 1-5 deterministic, Stage 6 Gemini AI, Stage 7 Review Queue).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Mention / Legal Name *</label>
              <Input
                placeholder="e.g. Microsoft Corp., Inc. or MSFT Ireland"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                className="text-xs"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Country Code (Optional)</label>
                <Input
                  placeholder="e.g. US, DE, IN"
                  maxLength={2}
                  value={testCountry}
                  onChange={(e) => setTestCountry(e.target.value.toUpperCase())}
                  className="text-xs uppercase"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Domain (Optional)</label>
                <Input
                  placeholder="e.g. microsoft.com"
                  value={testDomain}
                  onChange={(e) => setTestDomain(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>

            <Button
              className="w-full text-xs font-semibold"
              disabled={isResolvingTest || !testName.trim()}
              onClick={handleRunPlaygroundCascade}
            >
              {isResolvingTest ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
                  Running 7-Stage Cascade...
                </>
              ) : (
                "Run Cascade Live"
              )}
            </Button>

            {/* Test Result Display */}
            {testResult && (
              <div className="mt-4 p-4 rounded-xl bg-background/80 border border-border/80 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">Result:</span>
                    <Badge
                      variant={testResult.matched ? "default" : "critical"}
                      className="text-[10px]"
                    >
                      {testResult.matched ? "MATCHED" : "UNRESOLVED / REVIEW"}
                    </Badge>
                  </div>
                  <span className="text-xs font-mono font-semibold text-primary">
                    Stage {String(testResult.stage)} ({String(testResult.match_method)})
                  </span>
                </div>

                <div className="text-xs space-y-1 text-muted-foreground">
                  <p>
                    <span className="font-semibold text-foreground">Confidence: </span>
                    <span className="font-mono">{Number(testResult.confidence || 0).toFixed(2)}</span>
                  </p>
                  <p>
                    <span className="font-semibold text-foreground">Reasoning: </span>
                    {String(testResult.reasoning || "None")}
                  </p>
                  {Boolean(testResult.company) && (
                    <p>
                      <span className="font-semibold text-foreground">Matched Entity: </span>
                      {(testResult.company as { legal_name: string }).legal_name}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => setIsPlaygroundOpen(false)}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
