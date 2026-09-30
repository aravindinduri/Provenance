import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: {
    value: string;
    isPositive?: boolean;
  };
  icon?: React.ReactNode;
  accent?: "default" | "critical" | "high" | "emerald" | "blue";
}

export function MetricCard({
  title,
  value,
  subtitle,
  change,
  icon,
  accent = "default",
  className,
  ...props
}: MetricCardProps) {
  const accentGlow = {
    default: "hover:border-primary/40 hover:shadow-glow-primary",
    critical: "hover:border-red-500/40 hover:shadow-glow-rose",
    high: "hover:border-amber-500/40 hover:shadow-glow-amber",
    emerald: "hover:border-emerald-500/40",
    blue: "hover:border-blue-500/40 hover:shadow-glow-primary",
  }[accent];

  const accentBadge = {
    default: "bg-primary/10 text-primary",
    critical: "bg-red-500/10 text-red-500 dark:text-red-400",
    high: "bg-amber-500/10 text-amber-500 dark:text-amber-400",
    emerald: "bg-emerald-500/10 text-emerald-500 dark:text-emerald-400",
    blue: "bg-blue-500/10 text-blue-500 dark:text-blue-400",
  }[accent];

  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-300",
        accentGlow,
        className
      )}
      {...props}
    >
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
          {icon && (
            <div className={cn("p-2 rounded-lg transition-colors", accentBadge)}>
              {icon}
            </div>
          )}
        </div>

        <div className="mt-3 flex items-baseline gap-2">
          <div className="text-3xl font-bold tracking-tight">{value}</div>
          {change && (
            <span
              className={cn(
                "text-xs font-semibold px-1.5 py-0.5 rounded",
                change.isPositive
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "bg-red-500/10 text-red-600 dark:text-red-400"
              )}
            >
              {change.value}
            </span>
          )}
        </div>

        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
