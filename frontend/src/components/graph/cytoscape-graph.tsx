"use client";

import React, { useEffect, useRef, useCallback } from "react";
import cytoscape, { Core, EventObject, LayoutOptions } from "cytoscape";
import dagre from "cytoscape-dagre";
import coseBilkent from "cytoscape-cose-bilkent";

// Register Cytoscape layout extensions once in browser runtime
if (typeof window !== "undefined") {
  try {
    cytoscape.use(dagre);
  } catch {
    // already registered
  }
  try {
    cytoscape.use(coseBilkent);
  } catch {
    // already registered
  }
}

export interface GraphNodeData {
  id: string;
  entity_id?: string | null;
  label: string;
  type: string; // "organization" | "company" | "location"
  country?: string | null;
  risk_level?: string; // "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
  risk_score?: number | null;
  annual_spend_usd?: number | null;
  criticality?: number | null;
  tier?: number | null;
  category?: string | null;
  single_source?: boolean;
  metadata?: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  tier?: number | null;
  criticality?: number | null;
  annual_spend_usd?: number | null;
  confidence?: number;
  source_type?: string;
  single_source?: boolean;
  lead_time_days?: number | null;
}

interface CytoscapeGraphProps {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  layoutName: "dagre" | "cose-bilkent" | "concentric";
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  highlightedPathNodeIds?: string[];
  highlightedPathEdgeIds?: string[];
  onSelectNode: (node: GraphNodeData | null) => void;
  onSelectEdge: (edge: GraphEdgeData | null) => void;
  searchTerm?: string;
}

export function CytoscapeGraph({
  nodes,
  edges,
  layoutName,
  selectedNodeId,
  selectedEdgeId,
  highlightedPathNodeIds = [],
  highlightedPathEdgeIds = [],
  onSelectNode,
  onSelectEdge,
  searchTerm = "",
}: CytoscapeGraphProps): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Initialize and update Cytoscape instance
  useEffect(() => {
    if (!containerRef.current) return;

    // Check if HTML5 2D Canvas is supported without throwing (jsdom test environment guard)
    try {
      const testCanvas = document.createElement("canvas");
      const ctx = testCanvas.getContext("2d");
      if (!ctx) return;
    } catch {
      return;
    }

    // Convert nodes to Cytoscape elements
    const cyNodes = nodes.map((node) => {
      // Calculate node size based on spend or type
      let size = 44;
      if (node.type === "organization") {
        size = 62;
      } else if (node.annual_spend_usd) {
        // Log scale spend from 40px to 74px
        const spend = Number(node.annual_spend_usd);
        size = Math.min(74, Math.max(40, 36 + Math.log10(Math.max(1000, spend)) * 4.5));
      }

      return {
        group: "nodes" as const,
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          country: node.country || "",
          risk_level: node.risk_level || "UNKNOWN",
          risk_score: node.risk_score ?? null,
          spend: node.annual_spend_usd ?? 0,
          tier: node.tier ?? (node.type === "organization" ? 0 : 1),
          criticality: node.criticality ?? 3,
          single_source: node.single_source ? "yes" : "no",
          size,
          raw: node,
        },
      };
    });

    // Convert edges to Cytoscape elements
    const cyEdges = edges.map((edge) => {
      const crit = edge.criticality ?? 3;
      const width = Math.min(5, Math.max(1.5, 1.2 + crit * 0.7));
      const isDashed = (edge.confidence ?? 1.0) < 0.85 || edge.source_type === "inferred";

      return {
        group: "edges" as const,
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          relationship_type: edge.relationship_type,
          tier: edge.tier,
          criticality: crit,
          confidence: edge.confidence ?? 1.0,
          line_width: width,
          is_dashed: isDashed ? "yes" : "no",
          raw: edge,
        },
      };
    });

    // Destroy existing instance before creating a new one
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...cyNodes, ...cyEdges],
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        // ── Core Node Base ──────────────────────────────────────────
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "system-ui, -apple-system, sans-serif",
            "font-size": "10px",
            "font-weight": 600,
            "text-valign": "bottom",
            "text-margin-y": 6,
            color: "#94a3b8",
            "text-outline-color": "#090d16",
            "text-outline-width": 2,
            "text-max-width": "110px",
            "text-wrap": "ellipsis",
            width: "data(size)",
            height: "data(size)",
            "border-width": 2,
            "border-opacity": 0.9,
            "transition-property": "background-color, border-color, width, height, opacity",
            "transition-duration": 0.25,
          },
        },
        // ── Node Types & Colors ─────────────────────────────────────
        {
          selector: "node[type = 'organization']",
          style: {
            shape: "round-hexagon",
            "background-color": "#7c3aed",
            "border-color": "#c4b5fd",
            "border-width": 3,
            color: "#f1f5f9",
            "font-size": "11px",
            "font-weight": 700,
          },
        },
        {
          selector: "node[type = 'location']",
          style: {
            shape: "diamond",
            "background-color": "#0284c7",
            "border-color": "#38bdf8",
            "border-width": 2,
            color: "#bae6fd",
          },
        },
        {
          selector: "node[type = 'company'][risk_level = 'CRITICAL']",
          style: {
            shape: "ellipse",
            "background-color": "#dc2626",
            "border-color": "#f87171",
            color: "#fecaca",
          },
        },
        {
          selector: "node[type = 'company'][risk_level = 'HIGH']",
          style: {
            shape: "ellipse",
            "background-color": "#ea580c",
            "border-color": "#fb923c",
            color: "#ffedd5",
          },
        },
        {
          selector: "node[type = 'company'][risk_level = 'MEDIUM']",
          style: {
            shape: "ellipse",
            "background-color": "#d97706",
            "border-color": "#fcd34d",
            color: "#fef3c7",
          },
        },
        {
          selector: "node[type = 'company'][risk_level = 'LOW']",
          style: {
            shape: "ellipse",
            "background-color": "#16a34a",
            "border-color": "#4ade80",
            color: "#dcfce7",
          },
        },
        {
          selector: "node[type = 'company'][risk_level = 'UNKNOWN']",
          style: {
            shape: "ellipse",
            "background-color": "#334155",
            "border-color": "#64748b",
            color: "#cbd5e1",
          },
        },
        // Single Source indicator
        {
          selector: "node[single_source = 'yes']",
          style: {
            "border-style": "double",
            "border-width": 4,
          },
        },
        // ── Edges ───────────────────────────────────────────────────
        {
          selector: "edge",
          style: {
            width: "data(line_width)",
            "line-color": "#475569",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#475569",
            "curve-style": "bezier",
            "arrow-scale": 0.85,
            opacity: 0.65,
            "transition-property": "line-color, target-arrow-color, width, opacity",
            "transition-duration": 0.25,
          },
        },
        {
          selector: "edge[is_dashed = 'yes']",
          style: {
            "line-style": "dashed",
          },
        },
        {
          selector: "edge[relationship_type = 'supplies_to']",
          style: {
            "line-color": "#3b82f6",
            "target-arrow-color": "#3b82f6",
            opacity: 0.8,
          },
        },
        {
          selector: "edge[relationship_type = 'sub_supplies_to']",
          style: {
            "line-color": "#6366f1",
            "target-arrow-color": "#6366f1",
            opacity: 0.75,
          },
        },
        {
          selector: "edge[relationship_type = 'owned_by']",
          style: {
            "line-color": "#a855f7",
            "target-arrow-color": "#a855f7",
            opacity: 0.7,
          },
        },
        {
          selector: "edge[relationship_type = 'located_in']",
          style: {
            "line-color": "#06b6d4",
            "target-arrow-color": "#06b6d4",
            opacity: 0.6,
          },
        },
        // ── Active / Selected / Hover States ────────────────────────
        {
          selector: ".node-selected",
          style: {
            "border-color": "#facc15",
            "border-width": 4,
            "z-index": 990,
          },
        },
        {
          selector: ".edge-selected",
          style: {
            "line-color": "#facc15",
            "target-arrow-color": "#facc15",
            width: 4.5,
            opacity: 1,
            "z-index": 990,
          },
        },
        {
          selector: ".path-node",
          style: {
            "border-color": "#38bdf8",
            "border-width": 4,
            "z-index": 998,
          },
        },
        {
          selector: ".path-edge",
          style: {
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            width: 5,
            opacity: 1,
            "z-index": 998,
          },
        },
        {
          selector: ".dimmed",
          style: {
            opacity: 0.15,
          },
        },
        {
          selector: ".search-highlight",
          style: {
            "border-color": "#ec4899",
            "border-width": 5,
            "z-index": 995,
          },
        },
      ],
    });

    // Run layout
    let layoutConfig: LayoutOptions;
    if (layoutName === "dagre") {
      layoutConfig = {
        name: "dagre",
        rankDir: "TB",
        nodeSep: 65,
        rankSep: 85,
        animate: true,
        animationDuration: 500,
      } as LayoutOptions;
    } else if (layoutName === "cose-bilkent") {
      layoutConfig = {
        name: "cose-bilkent",
        animate: true,
        animationDuration: 600,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 110,
      } as LayoutOptions;
    } else {
      layoutConfig = {
        name: "concentric",
        concentric: (node: { data: (key: string) => number }) => 10 - (node.data("tier") || 1),
        levelWidth: () => 1,
        animate: true,
        animationDuration: 500,
      } as LayoutOptions;
    }

    cy.layout(layoutConfig).run();

    // Event listeners
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      const raw = node.data("raw") as GraphNodeData;
      onSelectNode(raw);
      onSelectEdge(null);
    });

    cy.on("tap", "edge", (evt: EventObject) => {
      const edge = evt.target;
      const raw = edge.data("raw") as GraphEdgeData;
      onSelectEdge(raw);
      onSelectNode(null);
    });

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectNode(null);
        onSelectEdge(null);
      }
    });

    // Hover spotlight behavior
    cy.on("mouseover", "node", (evt: EventObject) => {
      const node = evt.target;
      const neighborhood = node.neighborhood().add(node);
      cy.elements().not(neighborhood).addClass("dimmed");
    });

    cy.on("mouseout", "node", () => {
      cy.elements().removeClass("dimmed");
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges, layoutName, onSelectNode, onSelectEdge]);

  // Handle Selection Highlights
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      cy.elements().removeClass("node-selected edge-selected path-node path-edge");

      if (selectedNodeId) {
        cy.getElementById(selectedNodeId).addClass("node-selected");
      }
      if (selectedEdgeId) {
        cy.getElementById(selectedEdgeId).addClass("edge-selected");
      }

      // Highlight path nodes and edges
      for (const nid of highlightedPathNodeIds) {
        cy.getElementById(nid).addClass("path-node");
      }
      for (const eid of highlightedPathEdgeIds) {
        cy.getElementById(eid).addClass("path-edge");
      }
    });
  }, [selectedNodeId, selectedEdgeId, highlightedPathNodeIds, highlightedPathEdgeIds]);

  // Handle Search Highlights
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      cy.nodes().removeClass("search-highlight");
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matches = cy.nodes().filter((node) => {
          const label = String(node.data("label") || "").toLowerCase();
          const country = String(node.data("country") || "").toLowerCase();
          return label.includes(query) || country.includes(query);
        });

        matches.addClass("search-highlight");
        if (matches.length > 0) {
          cy.animate({
            center: { eles: matches.first() },
            duration: 400,
            zoom: Math.max(cy.zoom(), 1.2),
          });
        }
      }
    });
  }, [searchTerm]);

  // Exposed viewport controls
  const handleZoomIn = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  }, []);

  const handleFit = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 35);
    }
  }, []);

  return (
    <div className="relative w-full h-full min-h-[580px] rounded-xl overflow-hidden bg-slate-950/70 border border-slate-800/80 shadow-inner">
      {/* Cytoscape Canvas */}
      <div ref={containerRef} className="w-full h-full min-h-[580px]" />

      {/* Floating Canvas Controls HUD */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1.5 p-1.5 rounded-lg bg-slate-900/85 backdrop-blur-md border border-slate-700/60 shadow-lg text-xs">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="px-2.5 py-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors font-mono"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="px-2.5 py-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors font-mono"
        >
          -
        </button>
        <button
          onClick={handleFit}
          title="Fit View"
          className="px-2.5 py-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors"
        >
          Fit
        </button>
      </div>

      {/* Legend Badge */}
      <div className="absolute top-4 left-4 z-20 hidden sm:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-900/85 backdrop-blur-md border border-slate-700/60 shadow-lg text-[11px] text-slate-300">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
          <span>Critical</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" />
          <span>High</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span>Medium</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
          <span>Low</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-purple-600 inline-block" />
          <span>Org</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rotate-45 bg-cyan-500 inline-block" />
          <span>Site</span>
        </div>
      </div>
    </div>
  );
}
