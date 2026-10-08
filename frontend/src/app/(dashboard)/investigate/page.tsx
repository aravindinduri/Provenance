"use client";

import React from "react";
import { InvestigationWorkspace } from "@/components/investigate/investigation-workspace";

export default function InvestigatePage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            AI Investigation Agent
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-normal bg-primary/10 text-primary border border-primary/20">
              Agent 4 Active
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Autonomous multi-tier evidence gathering, price-claim verification, and geopolitical exposure tracing.
          </p>
        </div>
      </div>

      {/* Main Agentic Workspace */}
      <InvestigationWorkspace />
    </div>
  );
}
