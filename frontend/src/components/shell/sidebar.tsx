"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Gauge,
  Network,
  Sparkles,
  Building2,
  AlertTriangle,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Bell,
  MessageSquare,
  Plus,
  Trash2,
  ClipboardList,
  Package,
  FileQuestion,
  FileText,
  ShoppingCart,
  PackageCheck,
  Receipt,
} from "lucide-react";
import { useUIStore } from "@/lib/store/ui-store";
import { useUserStore } from "@/lib/store/user-store";
import { useAppAuth } from "@/lib/auth/clerk-adapter";
import { useConversationStore, formatRelativeTime } from "@/lib/store/conversation-store";
import { ProvenanceLogo } from "@/components/landing/ProvenanceLogo";
import { UserMenu } from "./user-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  badgeVariant?: "critical" | "high" | "default" | "secondary" | "ai";
  adminOnly?: boolean;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const isCollapsed = useUIStore((s) => s.isSidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const isPlatformAdmin = useUserStore((s) => s.isPlatformAdmin);
  const orgId = useUserStore((s) => s.orgId);
  const { getToken } = useAppAuth();
  const [activeAlertsCount, setActiveAlertsCount] = useState<number | null>(null);

  const conversations = useConversationStore((s) => s.conversations);
  const activeConversationId = useConversationStore((s) => s.activeConversationId);
  const selectConversation = useConversationStore((s) => s.selectConversation);
  const createConversation = useConversationStore((s) => s.createConversation);
  const deleteConversation = useConversationStore((s) => s.deleteConversation);

  React.useEffect(() => {
    let isMounted = true;
    async function fetchCounts() {
      try {
        const token = await getToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (orgId) headers["x-org-id"] = orgId;
        const res = await fetch("/api/v1/alerts/counts", { headers });
        if (res.ok && isMounted) {
          const data = await res.json();
          const unhandled = (data.new ?? 0) + (data.acknowledged ?? 0);
          setActiveAlertsCount(unhandled > 0 ? unhandled : null);
        }
      } catch {
        // silent fallback
      }
    }
    fetchCounts();
    return () => {
      isMounted = false;
    };
  }, [orgId, getToken]);

  const navItems: NavItem[] = [
    {
      title: "Trace",
      href: "/trace",
      icon: Sparkles,
      badge: "Agent",
      badgeVariant: "ai",
    },
    {
      title: "Dashboard",
      href: "/dashboard",
      icon: Gauge,
    },
    {
      title: "Material Request",
      href: "/material-requests",
      icon: ClipboardList,
    },
    {
      title: "RFQ / RFP",
      href: "/rfx",
      icon: FileQuestion,
    },
    {
      title: "Quotations",
      href: "/quotations",
      icon: FileText,
    },
    {
      title: "Purchase Order",
      href: "/purchase-orders",
      icon: ShoppingCart,
    },
    {
      title: "Purchase Receipt",
      href: "/receipts",
      icon: PackageCheck,
    },
    {
      title: "Purchase Invoice",
      href: "/invoices",
      icon: Receipt,
    },
    {
      title: "Approvals",
      href: "/approvals",
      icon: ShieldCheck,
    },
    {
      title: "Items",
      href: "/items",
      icon: Package,
    },
    {
      title: "Suppliers",
      href: "/suppliers",
      icon: Building2,
    },
    {
      title: "Alerts",
      href: "/alerts",
      icon: AlertTriangle,
      badge: activeAlertsCount && activeAlertsCount > 0 ? activeAlertsCount : undefined,
      badgeVariant: "critical",
    },
    {
      title: "Graph",
      href: "/graph",
      icon: Network,
    },
  ];

  return (
    <aside
      className={cn(
        "flex flex-col h-full shrink-0 border-r border-neutral-200/80 bg-white transition-all duration-300 z-30 select-none shadow-[1px_0_4px_rgba(0,0,0,0.02)]",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-100 px-3.5">
        {!isCollapsed ? (
          <>
            <Link href="/dashboard" prefetch={false} className="flex items-center gap-2 pl-1 group">
              <ProvenanceLogo size="sm" inverted={false} withTagline={false} />
              <span className="text-xs font-extrabold tracking-wider text-neutral-900 font-mono">
                PROVENANCE
              </span>
            </Link>
            <div className="flex items-center gap-1">
              {/* Notification Bell */}
              <Link
                href="/alerts"
                prefetch={false}
                className="relative p-1.5 text-neutral-500 hover:text-neutral-900 rounded-lg hover:bg-neutral-100 transition-colors"
                title="Active Alerts"
              >
                <Bell className="w-4 h-4" />
                {activeAlertsCount && activeAlertsCount > 0 ? (
                  <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#FA651E] ring-2 ring-white" />
                ) : null}
              </Link>
              {/* Collapse Button */}
              <button
                onClick={toggleSidebar}
                className="p-1.5 text-neutral-400 hover:text-neutral-800 rounded-lg hover:bg-neutral-100 transition-colors"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>
          </>
        ) : (
          <button
            onClick={toggleSidebar}
            className="w-full flex items-center justify-center p-1.5 text-neutral-500 hover:text-neutral-900 rounded-lg hover:bg-neutral-100 transition-colors"
            aria-label="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav List */}
      <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || (item.href !== "/trace" && pathname.startsWith(`${item.href}/`)) || (item.href === "/trace" && pathname.startsWith("/trace"));
          const Icon = item.icon;

          return (
            <React.Fragment key={item.href}>
              <Link
                href={item.href}
                prefetch={false}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-2 text-xs transition-all duration-150",
                  isActive
                    ? "bg-neutral-100 text-neutral-950 font-semibold shadow-2xs border border-neutral-200/60"
                    : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-950 font-medium"
                )}
                title={isCollapsed ? (item.title === "Trace" ? "Agent Trace" : item.title) : undefined}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform group-hover:scale-105",
                    isActive ? "text-[#FA651E]" : "text-neutral-500"
                  )}
                />
                {!isCollapsed && (
                  <span className="flex-1 truncate tracking-tight">{item.title}</span>
                )}
                {!isCollapsed && item.badge && (
                  item.badgeVariant === "ai" ? (
                    <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-[#FA651E]/10 text-[#FA651E] border border-[#FA651E]/20 font-mono">
                      {item.badge}
                    </span>
                  ) : (
                    <Badge
                      variant={item.badgeVariant ?? "secondary"}
                      className="ml-auto text-[10px] py-0 px-1.5 font-mono"
                    >
                      {item.badge}
                    </Badge>
                  )
                )}
              </Link>

              {/* Conversation History below Trace tab */}
              {item.title === "Trace" && !isCollapsed && (
                <div className="mt-1 mb-2 ml-3 pl-2.5 border-l-2 border-neutral-100 space-y-1">
                  <div className="flex items-center justify-between px-1 py-1 text-[10px] font-mono font-bold tracking-wider text-neutral-400">
                    <span>CHATS {conversations.length > 0 ? `(${conversations.length})` : ""}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        createConversation();
                        if (pathname !== "/trace") {
                          router.push("/trace");
                        }
                      }}
                      className="p-1 rounded-md text-neutral-400 hover:text-[#FA651E] hover:bg-orange-50 transition-colors"
                      title="Start a new chat"
                      aria-label="Start a new chat"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>

                  {conversations.length === 0 ? (
                    <div className="px-2 py-1 text-[11px] text-neutral-400 italic">
                      No past chats yet
                    </div>
                  ) : (
                    <div className="space-y-0.5 max-h-52 overflow-y-auto pr-1">
                      {conversations.slice(0, 10).map((conv) => {
                        const isCurrentActive = pathname === "/trace" && activeConversationId === conv.id;
                        return (
                          <div
                            key={conv.id}
                            onClick={() => {
                              selectConversation(conv.id);
                              if (pathname !== "/trace") {
                                router.push("/trace");
                              }
                            }}
                            className={cn(
                              "group flex items-center justify-between rounded-lg px-2 py-1.5 text-[11px] cursor-pointer transition-all duration-150 select-none",
                              isCurrentActive
                                ? "bg-orange-50/90 text-[#FA651E] font-semibold border border-[#FA651E]/20 shadow-2xs"
                                : "text-neutral-600 hover:bg-neutral-100/70 hover:text-neutral-950 font-normal"
                            )}
                            title={conv.title}
                          >
                            <div className="flex items-center gap-1.5 min-w-0 flex-1 pr-1">
                              <MessageSquare
                                className={cn(
                                  "w-3 h-3 shrink-0",
                                  isCurrentActive ? "text-[#FA651E]" : "text-neutral-400 group-hover:text-neutral-600"
                                )}
                              />
                              <span className="truncate">{conv.title}</span>
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              <span className="text-[9px] text-neutral-400 font-mono group-hover:hidden">
                                {formatRelativeTime(conv.updatedAt)}
                              </span>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  deleteConversation(conv.id);
                                }}
                                className="hidden group-hover:flex items-center justify-center p-0.5 rounded text-neutral-400 hover:text-destructive hover:bg-neutral-200/60 transition-colors"
                                title="Delete chat"
                                aria-label="Delete chat"
                              >
                                <Trash2 className="w-2.5 h-2.5" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}


        {/* Platform Admin */}
        {isPlatformAdmin && (
          <Link
            href="/admin"
            className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-150",
              pathname.startsWith("/admin")
                ? "bg-neutral-100 text-neutral-950 font-semibold border border-neutral-200/60"
                : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-950"
            )}
            title={isCollapsed ? "Platform Admin" : undefined}
          >
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            {!isCollapsed && <span className="flex-1 truncate">Platform Admin</span>}
          </Link>
        )}
      </div>

      {/* Bottom User Profile Section */}
      <div className="shrink-0 border-t border-neutral-100 p-2 bg-neutral-50/40">
        <UserMenu isCollapsed={isCollapsed} />
      </div>
    </aside>
  );
}
