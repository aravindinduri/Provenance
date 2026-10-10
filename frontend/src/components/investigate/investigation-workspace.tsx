"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Sparkles,
  Search,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Globe,
  Cpu,
  ArrowRight,
  ExternalLink,
  Clock,
  Zap,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";

export interface InvestigationCitation {
  id: string;
  citation_type: "supplier" | "company" | "event" | "graph_edge" | "document";
  title: string;
  details: string;
  country?: string | null;
  confidence: number;
  url?: string | null;
  metadata?: Record<string, unknown>;
}

export interface InvestigationTraceStep {
  step_id: string;
  name: string;
  action: string;
  status: "completed" | "executing" | "skipped" | "failed";
  details?: string | null;
  duration_ms: number;
}

export interface InvestigationResponse {
  id: string;
  query: string;
  summary: string;
  detailed_analysis: string;
  risk_level: "critical" | "high" | "medium" | "low" | "informational";
  recommended_actions: string[];
  key_findings: string[];
  citations: InvestigationCitation[];
  execution_trace: InvestigationTraceStep[];
  model: string;
  provider: string;
  latency_ms: number;
  created_at: string;
}

export interface SuggestionItem {
  id: string;
  title: string;
  prompt: string;
  category: "exposure" | "disruption" | "concentration" | "deep_tier";
  icon: string;
}

export function InvestigationWorkspace(): React.JSX.Element {
  const orgId = useUserStore((s) => s.orgId);
  const { getToken } = useAppAuth();
  const [query, setQuery] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<InvestigationResponse | null>(null);
  const [history, setHistory] = useState<InvestigationResponse[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [activeTab, setActiveTab] = useState<"analysis" | "citations" | "trace">("analysis");

  const resultsEndRef = useRef<HTMLDivElement>(null);

  // Fetch dynamic tenant suggestions from live API
  useEffect(() => {
    async function loadSuggestions(): Promise<void> {
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        const res = await fetch("/api/v1/investigate/suggestions", { credentials: "include", headers });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setSuggestions(data);
          }
        } else {
          setSuggestions([]);
        }
      } catch {
        setSuggestions([]);
      }
    }
    loadSuggestions();
  }, [orgId, getToken]);

  const handleExecuteQuery = useCallback(
    async (queryText: string): Promise<void> => {
      const trimmed = queryText.trim();
      if (!trimmed || isLoading) return;

      setIsLoading(true);
      setErrorMessage(null);
      try {
        const token = await getToken();
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;

        const res = await fetch("/api/v1/investigate/query", {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify({
            query: trimmed,
            conversation_history: history.slice(-3).map((h) => ({
              role: "assistant",
              content: h.summary,
            })),
          }),
        });

        if (res.ok) {
          const data: InvestigationResponse = await res.json();
          setCurrentResponse(data);
          setHistory((prev) => [data, ...prev]);
          setQuery("");
        } else {
          const errData = await res.json().catch(() => ({}));
          console.error("Investigation error:", errData);
          setErrorMessage(errData.detail || errData.title || `Investigation request failed with HTTP ${res.status}`);
        }
      } catch (err: unknown) {
        console.error("Investigation request failed:", err);
        setErrorMessage(err instanceof Error ? err.message : "Failed to connect to investigation service");
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, orgId, history, getToken]
  );

  const getRiskBadgeVariant = (
    level: string
  ): "critical" | "high" | "medium" | "low" => {
    switch (level.toLowerCase()) {
      case "critical":
        return "critical";
      case "high":
        return "high";
      case "medium":
        return "medium";
      default:
        return "low";
    }
  };

  const getCategoryIcon = (iconName: string): React.JSX.Element => {
    switch (iconName) {
      case "Globe":
        return <Globe className="w-3.5 h-3.5 text-blue-500" />;
      case "ShieldAlert":
        return <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />;
      case "Cpu":
        return <Cpu className="w-3.5 h-3.5 text-emerald-500" />;
      default:
        return <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner & AI Engine Metadata */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-primary/10 via-background to-secondary/10 border border-primary/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
            <Sparkles className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold tracking-tight text-foreground">
                Provenance Agentic Investigation Engine
              </h2>
              <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/30 font-mono">
                Gemini 1.5 Flash
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Autonomous evidence gathering, multi-tier graph traversal, and zero vendor lock-in AI verification.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3 text-emerald-500" />
            RLS Tenant Scoped
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-primary" />
            Live Trace Engine
          </span>
        </div>
      </div>

      {/* Query Bar & Suggestions */}
      <Card className="p-4 bg-card/80 backdrop-blur-xl border border-border/80 shadow-md">
        <div className="space-y-3">
          {errorMessage && (
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="text-muted-foreground hover:text-foreground text-xs underline ml-2"
              >
                Dismiss
              </button>
            </div>
          )}
          <div className="relative flex items-center">
            <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Ask anything about your supply base (e.g. 'Which suppliers are exposed to Taiwan trade restrictions?')"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleExecuteQuery(query);
                }
              }}
              disabled={isLoading}
              className="w-full h-12 pl-10 pr-24 rounded-lg bg-background/90 border border-input text-sm text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-smooth"
            />
            <div className="absolute right-2">
              <Button
                size="sm"
                onClick={() => handleExecuteQuery(query)}
                disabled={isLoading || !query.trim()}
                className="h-8 px-3 text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-medium gap-1.5 shadow-sm"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <span>Investigate</span>
                    <Send className="w-3 h-3" />
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Quick Investigation Prompt Chips */}
          <div className="flex items-center gap-2 pt-1 overflow-x-auto no-scrollbar">
            <span className="text-[11px] font-medium text-muted-foreground whitespace-nowrap">Suggested:</span>
            {suggestions.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setQuery(item.prompt);
                  handleExecuteQuery(item.prompt);
                }}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-muted/60 hover:bg-muted border border-border/60 hover:border-primary/40 text-muted-foreground hover:text-foreground transition-smooth whitespace-nowrap shadow-xs"
              >
                {getCategoryIcon(item.icon)}
                <span>{item.title}</span>
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Main Results Workspace */}
      {currentResponse ? (
        <div className="space-y-6 animate-fadeIn">
          {/* Response Header Card */}
          <Card className="p-6 bg-card/70 backdrop-blur-xl border border-border/80 shadow-md space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/40 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant={getRiskBadgeVariant(currentResponse.risk_level)} className="text-xs uppercase font-bold tracking-wider">
                    {currentResponse.risk_level} Risk Exposure
                  </Badge>
                  <span className="text-xs text-muted-foreground font-mono">
                    Latency: {currentResponse.latency_ms}ms
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    Engine: {currentResponse.provider.toUpperCase()} ({currentResponse.model})
                  </span>
                </div>
                <h3 className="text-lg font-bold text-foreground tracking-tight">
                  {currentResponse.query}
                </h3>
              </div>

              {/* View Switcher Tabs */}
              <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-lg border border-border/40">
                <button
                  type="button"
                  onClick={() => setActiveTab("analysis")}
                  className={`px-3 py-1 rounded text-xs font-medium transition-smooth ${activeTab === "analysis"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  Analysis & Findings
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("citations")}
                  className={`px-3 py-1 rounded text-xs font-medium transition-smooth ${activeTab === "citations"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  Evidence Citations ({currentResponse.citations.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("trace")}
                  className={`px-3 py-1 rounded text-xs font-medium transition-smooth ${activeTab === "trace"
                      ? "bg-background text-foreground shadow-xs font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  Execution Trace ({currentResponse.execution_trace.length})
                </button>
              </div>
            </div>

            {/* TAB 1: Analysis & Findings */}
            {activeTab === "analysis" && (
              <div className="space-y-5">
                {/* Executive Summary */}
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Executive Intelligence Summary</span>
                  </div>
                  <p className="text-sm font-medium text-foreground leading-relaxed">
                    {currentResponse.summary}
                  </p>
                </div>

                {/* Key Findings Grid */}
                {currentResponse.key_findings.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      Key Corroborated Findings
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {currentResponse.key_findings.map((finding, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-card border border-border/60 text-xs text-foreground/90 flex items-start gap-2 shadow-xs"
                        >
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                          <span>{finding}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Detailed Analysis (Markdown Render) */}
                <div className="space-y-2 pt-2 border-t border-border/40">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Detailed Graph & Signal Breakdown
                  </h4>
                  <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">
                    {currentResponse.detailed_analysis}
                  </div>
                </div>

                {/* Recommended Mitigation Actions */}
                {currentResponse.recommended_actions.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-border/40">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      Actionable Mitigation Directives
                    </h4>
                    <div className="space-y-2">
                      {currentResponse.recommended_actions.map((act, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2.5 p-3 rounded-lg bg-secondary/20 border border-secondary/40 text-xs text-foreground"
                        >
                          <ArrowRight className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                          <span>{act}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Evidence Citations */}
            {activeTab === "citations" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    All findings are strictly cited to primary internal graph records or authoritative external regulatory signals.
                  </p>
                  <span className="text-xs font-mono text-muted-foreground">
                    {currentResponse.citations.length} Verified Sources
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentResponse.citations.map((citation) => (
                    <Card
                      key={citation.id}
                      className="p-3.5 bg-background/80 border border-border/70 hover:border-primary/40 transition-smooth space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Badge variant="outline" className="text-[10px] capitalize font-mono">
                            {citation.citation_type}
                          </Badge>
                          {citation.country && (
                            <Badge variant="secondary" className="text-[10px] font-mono">
                              {citation.country}
                            </Badge>
                          )}
                        </div>
                        <span className="text-[11px] font-mono text-emerald-500 font-semibold">
                          {Math.round(citation.confidence * 100)}% Conf
                        </span>
                      </div>

                      <div>
                        <h5 className="text-xs font-bold text-foreground">
                          {citation.title}
                        </h5>
                        <p className="text-[11px] text-muted-foreground mt-0.5 leading-normal">
                          {citation.details}
                        </p>
                      </div>

                      {citation.url && (
                        <div className="pt-1 border-t border-border/30">
                          <a
                            href={citation.url}
                            className="text-[10px] text-primary hover:underline flex items-center gap-1"
                          >
                            <span>Inspect Node Details</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: Execution Trace (LangGraph Style) */}
            {activeTab === "trace" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-border/40">
                  <p className="text-xs text-muted-foreground">
                    Chronological audit trace of agent reasoning, graph querying, and LLM invocation.
                  </p>
                  <span className="text-xs font-mono text-muted-foreground">
                    Total: {currentResponse.latency_ms}ms
                  </span>
                </div>

                <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border/60">
                  {currentResponse.execution_trace.map((step, idx) => (
                    <div key={step.step_id} className="relative group">
                      {/* Step Marker Dot */}
                      <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-background border-2 border-primary flex items-center justify-center text-[10px] font-bold text-primary shadow-xs">
                        {idx + 1}
                      </div>

                      <div className="p-3 rounded-lg bg-background/60 border border-border/60 hover:border-primary/30 transition-smooth space-y-1">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <h5 className="text-xs font-bold text-foreground">
                              {step.name}
                            </h5>
                            <Badge variant="outline" className="text-[9px] text-emerald-500 border-emerald-500/30 uppercase">
                              {step.status}
                            </Badge>
                          </div>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {step.duration_ms}ms
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          {step.action}
                        </p>
                        {step.details && (
                          <div className="p-1.5 rounded bg-muted/40 font-mono text-[10px] text-foreground/80 mt-1">
                            {step.details}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      ) : (
        /* Empty State / Welcome Guide */
        <Card className="p-10 text-center bg-card/50 backdrop-blur-md border border-dashed border-border/80 space-y-4">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-inner">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3 className="text-base font-bold text-foreground">
              Autonomous Investigation Ready
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Inquire in natural language to interrogate your supplier graph, correlate real-time regulatory notices, or evaluate geopolitical exposure. Powered by Google Gemini with strict evidence citations.
            </p>
          </div>
          {suggestions.length > 0 && (
            <div className="pt-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleExecuteQuery(suggestions[0].prompt)}
                className="text-xs border-primary/30 hover:bg-primary/10 text-primary gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Run Suggested: {suggestions[0].title}</span>
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* Investigation Session History */}
      {history.length > 1 && (
        <div className="space-y-3 pt-4 border-t border-border/40">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Session Investigation History
          </h4>
          <div className="space-y-2">
            {history.slice(1).map((item) => (
              <div
                key={item.id}
                onClick={() => setCurrentResponse(item)}
                className="p-3 rounded-lg bg-card/60 border border-border/60 hover:border-primary/40 cursor-pointer flex items-center justify-between text-xs transition-smooth"
              >
                <div className="flex items-center gap-2">
                  <Badge variant={getRiskBadgeVariant(item.risk_level)} className="text-[10px] uppercase">
                    {item.risk_level}
                  </Badge>
                  <span className="font-medium text-foreground truncate max-w-lg">
                    {item.query}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground">
                  {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div ref={resultsEndRef} />
    </div>
  );
}
