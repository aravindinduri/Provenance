"use client";

import React from "react";
import { ShieldAlert, Layers } from "lucide-react";
import { useUIStore, type Persona } from "@/lib/store/ui-store";
import { cn } from "@/lib/utils";

export function PersonaSwitcher({ className }: { className?: string }) {
  const persona = useUIStore((s) => s.persona);
  const setPersona = useUIStore((s) => s.setPersona);

  const personas: {
    id: Persona;
    label: string;
    description: string;
    icon: React.ReactNode;
  }[] = [
    {
      id: "risk_manager",
      label: "Risk Manager",
      description: "External disruptions & exposure",
      icon: <ShieldAlert className="h-4 w-4" />,
    },
    {
      id: "category_manager",
      label: "Category Manager",
      description: "Category spend & sourcing actions",
      icon: <Layers className="h-4 w-4" />,
    },
  ];

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-lg border border-border/70 bg-muted/60 p-1 backdrop-blur-md shadow-inner",
        className
      )}
      role="group"
      aria-label="Persona view switcher"
    >
      {personas.map((p) => {
        const isActive = persona === p.id;
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => setPersona(p.id)}
            className={cn(
              "relative flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-smooth",
              isActive
                ? "bg-background text-foreground shadow-sm ring-1 ring-border/50"
                : "text-muted-foreground hover:text-foreground hover:bg-background/40"
            )}
            title={p.description}
          >
            <span
              className={cn(
                "transition-colors",
                isActive ? "text-primary" : "text-muted-foreground"
              )}
            >
              {p.icon}
            </span>
            <span>{p.label}</span>
          </button>
        );
      })}
    </div>
  );
}
