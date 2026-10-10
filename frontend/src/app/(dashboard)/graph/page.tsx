"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  GitFork,
  Search,
  Layers,
  AlertTriangle,
  Building2,
  ExternalLink,
  RefreshCw,
  Info,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CytoscapeGraph,
  GraphNodeData,
  GraphEdgeData,
} from "@/components/graph/cytoscape-graph";
import { useAppAuth } from "@/lib/auth/clerk-adapter";

export default function GraphPage(): React.JSX.Element {
  const { getToken } = useAppAuth();
  const [nodes, setNodes] = useState<GraphNodeData[]>([]);
  const [edges, setEdges] = useState<GraphEdgeData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [layoutName, setLayoutName] = useState<"dagre" | "cose-bilkent" | "concentric">("dagre");

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTier, setSelectedTier] = useState<string>("all");
  const [selectedRisk, setSelectedRisk] = useState<string>("all");
  const [selectedRelType, setSelectedRelType] = useState<string>("all");
  const [depthLimit, setDepthLimit] = useState<number>(3);

  // Selection & Path Discovery State
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdgeData | null>(null);
  const [isTracingPath, setIsTracingPath] = useState(false);
  const [pathData, setPathData] = useState<{
    paths: Array<{
      depth: number;
      path_confidence: number;
      explanation: string;
      nodes: GraphNodeData[];
      edges: GraphEdgeData[];
    }>;
    summary: string;
  } | null>(null);

  // Highlighted path elements on Cytoscape
  const [highlightedPathNodeIds, setHighlightedPathNodeIds] = useState<string[]>([]);
  const [highlightedPathEdgeIds, setHighlightedPathEdgeIds] = useState<string[]>([]);

  // Load Graph from Backend API
  const loadGraph = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const typeParam = selectedRelType !== "all" ? `&types=${selectedRelType}` : "";
      const res = await fetch(`/api/v1/graph?depth=${depthLimit}&limit=300${typeParam}`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
      } else {
        const errData = await res.json().catch(() => ({}));
        setErrorMsg(errData.detail || `Failed to load graph data (HTTP ${res.status})`);
        setNodes([]);
        setEdges([]);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load graph data");
      setNodes([]);
      setEdges([]);
    } finally {
      setIsLoading(false);
    }
  }, [depthLimit, selectedRelType, getToken]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Expand a Node 1 Hop via API
  const handleExpandNode = async (node: GraphNodeData) => {
    if (!node.entity_id) return;
    setIsLoading(true);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const res = await fetch(`/api/v1/graph?root=${node.entity_id}&depth=1&limit=50`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        const existingNodeIds = new Set(nodes.map((n) => n.id));
        const newNodes = (data.nodes || []).filter((n: GraphNodeData) => !existingNodeIds.has(n.id));

        const existingEdgeIds = new Set(edges.map((e) => e.id));
        const newEdges = (data.edges || []).filter((e: GraphEdgeData) => !existingEdgeIds.has(e.id));

        setNodes((prev) => [...prev, ...newNodes]);
        setEdges((prev) => [...prev, ...newEdges]);
      }
    } catch {
      // Keep existing nodes
    } finally {
      setIsLoading(false);
    }
  };

  // Find Path to Current Org Root via API
  const handleFindPaths = async (fromNode: GraphNodeData) => {
    if (!fromNode.entity_id) return;
    setIsTracingPath(true);
    setHighlightedPathNodeIds([]);
    setHighlightedPathEdgeIds([]);
    try {
      const token = await getToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const res = await fetch(`/api/v1/graph/paths?from=${fromNode.entity_id}&depth=${depthLimit}`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        setPathData(data);
        if (data.paths && data.paths.length > 0) {
          const topPath = data.paths[0];
          const nodeIds = topPath.nodes.map((n: GraphNodeData) => n.id);
          const edgeIds = topPath.edges.map((e: GraphEdgeData) => e.id);
          setHighlightedPathNodeIds(nodeIds);
          setHighlightedPathEdgeIds(edgeIds);
        }
      } else {
        setPathData({
          paths: [],
          summary: `No verified path detected between ${fromNode.label} and organization root within ${depthLimit} hops.`,
        });
      }
    } catch {
      setPathData({
        paths: [],
        summary: `No direct or multi-tier path detected within ${depthLimit} hops.`,
      });
    } finally {
      setIsTracingPath(false);
    }
  };

  // Filtered elements
  const filteredNodes = useMemo(() => {
    return nodes.filter((node) => {
      // Tier filter
      if (selectedTier !== "all") {
        if (selectedTier === "3") {
          if ((node.tier ?? 0) < 3) return false;
        } else {
          if (node.tier !== Number(selectedTier)) return false;
        }
      }
      // Risk filter
      if (selectedRisk !== "all") {
        if (node.risk_level?.toLowerCase() !== selectedRisk.toLowerCase()) return false;
      }
      // Search term
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchesLabel = node.label.toLowerCase().includes(term);
        const matchesCountry = node.country?.toLowerCase().includes(term);
        const matchesCategory = node.category?.toLowerCase().includes(term);
        if (!matchesLabel && !matchesCountry && !matchesCategory) return false;
      }
      return true;
    });
  }, [nodes, selectedTier, selectedRisk, searchTerm]);

  // Keep edges that connect two visible nodes
  const filteredEdges = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((edge) => {
      if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return false;
      if (selectedRelType !== "all" && edge.relationship_type !== selectedRelType) return false;
      return true;
    });
  }, [edges, filteredNodes, selectedRelType]);

  // Summary Metrics computed from actual API nodes
  const metrics = useMemo(() => {
    const tier1Count = nodes.filter((n) => n.tier === 1).length;
    const tier2Count = nodes.filter((n) => n.tier === 2).length;
    const deepTierCount = nodes.filter((n) => (n.tier ?? 0) >= 3).length;
    const totalSpend = nodes.reduce((acc, n) => acc + (n.annual_spend_usd || 0), 0);
    const criticalCount = nodes.filter((n) => (n.criticality ?? 0) >= 4).length;
    const singleSourceCount = nodes.filter((n) => n.single_source).length;

    return {
      totalNodes: nodes.length,
      totalEdges: edges.length,
      tier1Count,
      tier2Count,
      deepTierCount,
      totalSpend,
      criticalCount,
      singleSourceCount,
    };
  }, [nodes, edges]);

  return (
    <div className="space-y-6">
      {/* ── Page Header ────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground lg:text-3xl">
              Supply Chain Graph Visualizer
            </h1>
            <Badge variant="outline" className="font-mono text-xs bg-primary/10 text-primary border-primary/20">
              Phase 7 Topology Engine
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Interactive multi-tier network graph showing direct suppliers, sub-tier dependencies, and ownership links.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => loadGraph()} disabled={isLoading}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh Graph
          </Button>
          <Button asChild size="sm" variant="default">
            <Link href="/suppliers">
              <Building2 className="mr-1.5 h-3.5 w-3.5" />
              Manage Suppliers
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

      {/* ── KPI Row Computed from Live Graph ──────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">Total Entities</p>
          <p className="text-xl font-bold text-foreground mt-0.5">{metrics.totalNodes}</p>
          <span className="text-[10px] text-muted-foreground">{metrics.totalEdges} active edges</span>
        </Card>
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">Direct Suppliers</p>
          <p className="text-xl font-bold text-foreground mt-0.5">{metrics.tier1Count}</p>
          <span className="text-[10px] text-blue-500 font-medium">Direct contracts</span>
        </Card>
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">Sub-tier Network</p>
          <p className="text-xl font-bold text-foreground mt-0.5">{metrics.tier2Count + metrics.deepTierCount}</p>
          <span className="text-[10px] text-amber-500 font-medium">Sub-suppliers &amp; raw materials</span>
        </Card>
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">Single Points of Failure</p>
          <p className="text-xl font-bold text-foreground mt-0.5">{metrics.singleSourceCount}</p>
          <span className="text-[10px] text-amber-500 font-medium">Single source dependencies</span>
        </Card>
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">High / Critical Risk</p>
          <p className="text-xl font-bold text-destructive mt-0.5">{metrics.criticalCount}</p>
          <span className="text-[10px] text-destructive/80 font-medium">Criticality 4 or 5</span>
        </Card>
        <Card className="p-3 bg-card/60 backdrop-blur-sm border-border/80">
          <p className="text-xs text-muted-foreground">Spend Mapped</p>
          <p className="text-xl font-bold text-foreground mt-0.5">
            ${(metrics.totalSpend / 1000000).toFixed(1)}M
          </p>
          <span className="text-[10px] text-muted-foreground">{metrics.singleSourceCount} single source</span>
        </Card>
      </div>

      {/* ── Filter & Layout Toolbar ─────────────────────────────────── */}
      <Card className="p-4 bg-card/80 backdrop-blur-md border-border/80 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[260px]">
            {/* Search */}
            <div className="relative min-w-[200px] flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                type="text"
                placeholder="Search companies by name or country..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 h-9 text-xs"
              />
            </div>

            {/* Tier Filter */}
            <Select value={selectedTier} onValueChange={setSelectedTier}>
              <SelectTrigger className="w-[120px] h-9 text-xs">
                <SelectValue placeholder="Tier" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="1">Tier 1</SelectItem>
                <SelectItem value="2">Tier 2</SelectItem>
                <SelectItem value="3">Tier 3+</SelectItem>
              </SelectContent>
            </Select>

            {/* Risk Filter */}
            <Select value={selectedRisk} onValueChange={setSelectedRisk}>
              <SelectTrigger className="w-[125px] h-9 text-xs">
                <SelectValue placeholder="Risk Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Risks</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>

            {/* Relationship Type */}
            <Select value={selectedRelType} onValueChange={setSelectedRelType}>
              <SelectTrigger className="w-[140px] h-9 text-xs">
                <SelectValue placeholder="Edge Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Edges</SelectItem>
                <SelectItem value="supplies_to">Supplies To</SelectItem>
                <SelectItem value="sub_supplies_to">Sub-supplies To</SelectItem>
                <SelectItem value="owned_by">Owned By (GLEIF)</SelectItem>
                <SelectItem value="operates_site">Operates Site</SelectItem>
              </SelectContent>
            </Select>

            {/* Depth Limit */}
            <Select value={String(depthLimit)} onValueChange={(val) => setDepthLimit(Number(val))}>
              <SelectTrigger className="w-[110px] h-9 text-xs">
                <SelectValue placeholder="Depth" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 Hop</SelectItem>
                <SelectItem value="2">2 Hops</SelectItem>
                <SelectItem value="3">3 Hops</SelectItem>
                <SelectItem value="4">4 Hops</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Layout Controls */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground mr-1">Layout:</span>
            <div className="inline-flex rounded-lg border border-border p-0.5 bg-muted/40">
              {(["dagre", "cose-bilkent", "concentric"] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLayoutName(l)}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    layoutName === l
                      ? "bg-purple-600 text-white shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {l === "dagre" ? "Hierarchy (Dagre)" : l === "cose-bilkent" ? "Clusters (Cose)" : "Radial"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* ── Main Workspace: Cytoscape Canvas & Details Inspector ────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Cytoscape Graph Canvas */}
        <div className="lg:col-span-3 space-y-4">
          <Card className="relative overflow-hidden border-border/80 shadow-md">
            {isLoading && (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/60 backdrop-blur-xs">
                <div className="flex flex-col items-center gap-2 p-4 rounded-xl bg-card border border-border shadow-lg">
                  <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                  <p className="text-xs font-medium text-foreground">Loading topology...</p>
                </div>
              </div>
            )}

            {!isLoading && nodes.length === 0 ? (
              <div className="h-[620px] flex flex-col items-center justify-center p-8 text-center bg-muted/10">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4">
                  <Layers className="h-7 w-7" />
                </div>
                <h3 className="text-base font-semibold text-foreground">No Graph Nodes Detected</h3>
                <p className="text-xs text-muted-foreground max-w-sm mt-1.5 mb-5">
                  There are currently no supplier nodes or relationships in this organization&apos;s graph.
                  Add suppliers to visualize your multi-tier supply chain network.
                </p>
                <div className="flex items-center gap-2.5">
                  <Button asChild size="sm">
                    <Link href="/suppliers">
                      <Building2 className="mr-1.5 h-3.5 w-3.5" />
                      Add Suppliers
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => loadGraph()}>
                    <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                    Retry Fetch
                  </Button>
                </div>
              </div>
            ) : (
              <CytoscapeGraph
                nodes={filteredNodes}
                edges={filteredEdges}
                layoutName={layoutName}
                selectedNodeId={selectedNode?.id ?? null}
                selectedEdgeId={selectedEdge?.id ?? null}
                onSelectNode={(node) => {
                  setSelectedNode(node);
                  setSelectedEdge(null);
                }}
                onSelectEdge={(edge) => {
                  setSelectedEdge(edge);
                  setSelectedNode(null);
                }}
                highlightedPathNodeIds={highlightedPathNodeIds}
                highlightedPathEdgeIds={highlightedPathEdgeIds}
                searchTerm={searchTerm}
              />
            )}

            {/* Floating Quick Legend */}
            <div className="absolute bottom-3 left-3 z-10 flex flex-wrap items-center gap-2 rounded-lg bg-background/80 p-2 text-[10px] font-medium backdrop-blur-md border border-border/60 text-muted-foreground shadow-sm">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-blue-500" /> Tier 1
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-500" /> Tier 2
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-purple-500" /> Tier 3+
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-red-500" /> Critical Risk
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500" /> Site / Facility
              </span>
            </div>
          </Card>

          {/* Path Finding Explanation Card */}
          {pathData && (
            <Card className="p-4 border-primary/30 bg-primary/5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
                      Exposure Path Discovery
                    </h3>
                  </div>
                  <p className="text-xs text-foreground font-medium">{pathData.summary}</p>
                  {pathData.paths.length > 0 && (
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {pathData.paths[0].explanation}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setPathData(null);
                    setHighlightedPathNodeIds([]);
                    setHighlightedPathEdgeIds([]);
                  }}
                  className="text-xs h-7 text-muted-foreground hover:text-foreground"
                >
                  Clear
                </Button>
              </div>
            </Card>
          )}
        </div>

        {/* Details & Action Inspector */}
        <div className="space-y-4">
          {selectedNode ? (
            <Card className="p-5 border-border/80 shadow-md space-y-4">
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Badge variant={selectedNode.risk_level?.toLowerCase() === "critical" ? "critical" : "secondary"}>
                    {selectedNode.type?.toUpperCase()} · TIER {selectedNode.tier ?? "?"}
                  </Badge>
                  {selectedNode.country && (
                    <span className="text-xs font-mono text-muted-foreground">{selectedNode.country}</span>
                  )}
                </div>
                <h3 className="text-base font-bold text-foreground tracking-tight pt-1">
                  {selectedNode.label}
                </h3>
                {selectedNode.category && (
                  <p className="text-xs text-muted-foreground">{selectedNode.category}</p>
                )}
              </div>

              <div className="space-y-2 pt-2 border-t border-border/60 text-xs">
                {selectedNode.annual_spend_usd != null && selectedNode.annual_spend_usd > 0 && (
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Annual Spend:</span>
                    <span className="font-semibold text-foreground">
                      ${selectedNode.annual_spend_usd.toLocaleString()}
                    </span>
                  </div>
                )}
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Criticality Level:</span>
                  <span className="font-semibold text-foreground">
                    {selectedNode.criticality ? `${selectedNode.criticality}/5` : "Unrated"}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Single Source:</span>
                  <span className={`font-semibold ${selectedNode.single_source ? "text-destructive" : "text-foreground"}`}>
                    {selectedNode.single_source ? "Yes (Vulnerable)" : "No"}
                  </span>
                </div>
                {selectedNode.risk_score != null && (
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Risk Index:</span>
                    <span className="font-mono font-semibold text-destructive">
                      {selectedNode.risk_score.toFixed(1)} / 100
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2 pt-3 border-t border-border/60">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full justify-between text-xs"
                  onClick={() => handleExpandNode(selectedNode)}
                  disabled={isLoading}
                >
                  <span>Expand Dependencies (1 Hop)</span>
                  <ArrowRight className="h-3 w-3" />
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  className="w-full justify-between text-xs"
                  onClick={() => handleFindPaths(selectedNode)}
                  disabled={isTracingPath}
                >
                  <span>{isTracingPath ? "Tracing Path..." : "Trace Path to Organization"}</span>
                  <GitFork className="h-3 w-3" />
                </Button>
                {selectedNode.entity_id && (
                  <Button asChild size="sm" variant="ghost" className="w-full text-xs text-muted-foreground">
                    <Link href={`/suppliers?search=${encodeURIComponent(selectedNode.label)}`}>
                      <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                      View Full Dossier
                    </Link>
                  </Button>
                )}
              </div>
            </Card>
          ) : selectedEdge ? (
            <Card className="p-5 border-border/80 shadow-md space-y-4">
              <div className="space-y-1">
                <Badge variant="outline" className="font-mono text-xs">
                  RELATIONSHIP EDGE
                </Badge>
                <h3 className="text-sm font-bold text-foreground pt-1">
                  {selectedEdge.relationship_type.replace(/_/g, " ").toUpperCase()}
                </h3>
              </div>
              <div className="space-y-2 pt-2 border-t border-border/60 text-xs">
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Source Entity:</span>
                  <span className="font-medium text-foreground">{selectedEdge.source}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Target Entity:</span>
                  <span className="font-medium text-foreground">{selectedEdge.target}</span>
                </div>
                {selectedEdge.annual_spend_usd && (
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Contract Spend:</span>
                    <span className="font-semibold text-foreground">
                      ${selectedEdge.annual_spend_usd.toLocaleString()}
                    </span>
                  </div>
                )}
                {selectedEdge.confidence != null && (
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Confidence:</span>
                    <span className="font-mono text-emerald-500">
                      {(selectedEdge.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card className="p-5 border-dashed border-border/80 text-center space-y-3 bg-muted/20">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted mx-auto text-muted-foreground">
                <Info className="h-5 w-5" />
              </div>
              <div className="space-y-1.5 text-left">
                <h3 className="text-xs font-semibold text-foreground text-center">Topology Navigator</h3>
                <p className="text-[11px] text-muted-foreground">
                  Click any company node to inspect connections or trace supply chain paths.
                </p>
                <div className="space-y-1 pt-1 text-[11px] text-muted-foreground border-t border-border/40">
                  <p>• Red nodes: Critical/High external risk exposure</p>
                  <p>• Purple hexagon: Your organization anchor</p>
                  <p>• Blue/green links: Direct supplier relationships</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
