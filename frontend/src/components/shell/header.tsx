"use client";

import React from "react";
import { Activity } from "lucide-react";
import { PersonaSwitcher } from "./persona-switcher";
import { UserMenu } from "./user-menu";
import { Badge } from "@/components/ui/badge";

export function Header() {
  return (
    <header className="sticky top-0 z-20 flex h-14 w-full items-center justify-between border-b border-border/70 bg-background/80 px-6 backdrop-blur-md">
      {/* Left: Freshness Status Indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="flex items-center gap-1.5 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px] font-medium py-0.5 px-2.5"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <Activity className="h-3 w-3" />
            <span>9 Sources Active</span>
          </Badge>
          <span className="hidden text-xs text-muted-foreground md:inline">
            SLO Freshness: &lt;1h
          </span>
        </div>
      </div>

      {/* Right: Persona Switcher & User Menu */}
      <div className="flex items-center gap-3">
        <PersonaSwitcher />
        <UserMenu />
      </div>
    </header>
  );
}
