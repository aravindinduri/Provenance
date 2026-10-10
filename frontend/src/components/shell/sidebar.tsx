"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  Building2,
  Network,
  Sparkles,
  FileSpreadsheet,
  Settings,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Radio,
  Layers,
} from "lucide-react";
import { useUIStore } from "@/lib/store/ui-store";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  badgeVariant?: "critical" | "high" | "default" | "secondary";
  adminOnly?: boolean;
}

export function Sidebar() {
  const pathname = usePathname();
  const isCollapsed = useUIStore((s) => s.isSidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const isPlatformAdmin = useUserStore((s) => s.isPlatformAdmin);
  const isOnboarded = useUserStore((s) => s.isOnboarded);
  const orgId = useUserStore((s) => s.orgId);
  const { getToken } = useAppAuth();
  const [activeAlertsCount, setActiveAlertsCount] = React.useState<number | null>(null);

  React.useEffect(() => {
    let isMounted = true;
    async function fetchCounts() {
      if (!orgId) return;
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;
        const res = await fetch("/api/v1/alerts/counts", { headers });
        if (res.ok && isMounted) {
          const data = await res.json();
          // Count active/new alerts
          const unhandled = (data.new ?? 0) + (data.acknowledged ?? 0);
          setActiveAlertsCount(unhandled > 0 ? unhandled : null);
        }
      } catch {
        // silent fallback
      }
    }
    fetchCounts();
  }, [orgId, getToken, pathname]);

  const navItems: NavItem[] = [
    {
      title: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      title: "Onboarding",
      href: "/onboarding",
      icon: Layers,
      badge: !isOnboarded ? "Setup" : undefined,
      badgeVariant: "high",
    },
    {
      title: "Alerts",
      href: "/alerts",
      icon: AlertTriangle,
      badge: activeAlertsCount && activeAlertsCount > 0 ? activeAlertsCount : undefined,
      badgeVariant: "critical",
    },
    {
      title: "Suppliers",
      href: "/suppliers",
      icon: Building2,
    },
    {
      title: "Graph",
      href: "/graph",
      icon: Network,
    },
    {
      title: "Investigate",
      href: "/investigate",
      icon: Sparkles,
      badge: "AI",
      badgeVariant: "default",
    },
    {
      title: "Data",
      href: "/data",
      icon: FileSpreadsheet,
    },
    {
      title: "Settings",
      href: "/settings",
      icon: Settings,
    },
    {
      title: "Platform Admin",
      href: "/admin",
      icon: ShieldCheck,
      adminOnly: true,
    },
  ];

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-border/70 bg-card/60 backdrop-blur-xl transition-all duration-300 z-30 select-none",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 items-center justify-between border-b border-border/60 px-3.5">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 overflow-hidden font-semibold tracking-tight"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-glow-primary">
            <Radio className="h-4 w-4 animate-pulse" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-foreground">
                PROVENANCE
              </span>
              <span className="text-[10px] tracking-wider uppercase text-muted-foreground">
                Risk Intelligence
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {navItems
          .filter((item) => !item.adminOnly || isPlatformAdmin)
          .map((item) => {
            const isActive =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-smooth",
                  isActive
                    ? "bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/20"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={isCollapsed ? item.title : undefined}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform group-hover:scale-110",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}
                />
                {!isCollapsed && (
                  <span className="flex-1 truncate">{item.title}</span>
                )}
                {!isCollapsed && item.badge && (
                  <Badge
                    variant={item.badgeVariant ?? "secondary"}
                    className="ml-auto text-[10px] py-0 px-1.5 font-mono"
                  >
                    {item.badge}
                  </Badge>
                )}
              </Link>
            );
          })}
      </nav>

      {/* Collapse Toggle Footer */}
      <div className="border-t border-border/60 p-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className="w-full justify-center text-muted-foreground hover:text-foreground"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <div className="flex items-center gap-2 text-xs">
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse sidebar</span>
            </div>
          )}
        </Button>
      </div>
    </aside>
  );
}
