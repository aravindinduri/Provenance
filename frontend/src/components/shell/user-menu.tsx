"use client";

import React from "react";
import { useAppClerk } from "@/lib/auth/clerk-adapter";
import { User, LogOut, ShieldCheck, Building } from "lucide-react";
import { useUserStore } from "@/lib/store/user-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function UserMenu() {
  const { signOut } = useAppClerk();
  const email = useUserStore((s) => s.email);
  const role = useUserStore((s) => s.role);
  const orgName = useUserStore((s) => s.orgName);
  const subscriptionTier = useUserStore((s) => s.subscriptionTier);
  const isPlatformAdmin = useUserStore((s) => s.isPlatformAdmin);

  const displayRole = role ? role.replace("_", " ") : "Member";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="flex items-center gap-2 border-border/80 bg-background/60 backdrop-blur hover:bg-accent"
        >
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-primary">
            <User className="h-3.5 w-3.5" />
          </div>
          <div className="hidden text-left md:block">
            <span className="block text-xs font-semibold leading-none">
              {email ? email.split("@")[0] : "User"}
            </span>
            <span className="block text-[10px] text-muted-foreground capitalize">
              {orgName || "Provenance"}
            </span>
          </div>
          <Badge
            variant={isPlatformAdmin ? "critical" : "secondary"}
            className="hidden text-[10px] py-0 px-1.5 font-mono capitalize lg:inline-flex"
          >
            {displayRole}
          </Badge>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-xs font-medium leading-none text-foreground">
              {email || "Signed in"}
            </p>
            <div className="flex items-center gap-1.5 pt-1">
              <Building className="h-3 w-3 text-muted-foreground" />
              <p className="text-[11px] leading-none text-muted-foreground truncate">
                {orgName || "Default Organization"}
              </p>
            </div>
            {subscriptionTier && (
              <Badge variant="outline" className="w-fit text-[10px] mt-1 capitalize">
                Tier: {subscriptionTier}
              </Badge>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isPlatformAdmin && (
          <>
            <DropdownMenuItem asChild>
              <a href="/admin" className="flex items-center text-xs text-amber-500 font-medium">
                <ShieldCheck className="mr-2 h-3.5 w-3.5" />
                Platform Admin Portal
              </a>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem
          className="text-xs text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer"
          onClick={() => signOut({ redirectUrl: "/sign-in" })}
        >
          <LogOut className="mr-2 h-3.5 w-3.5" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
