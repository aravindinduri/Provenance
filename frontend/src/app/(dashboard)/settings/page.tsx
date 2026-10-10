"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  Users,
  Sliders,
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  Mail,
  Save,
  RotateCcw,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useUserStore } from "@/lib/store/user-store";
import { cn } from "@/lib/utils";

interface OrgMember {
  id: string;
  user_id: string;
  role: string;
  persona: string | null;
  assigned_categories: string[];
  joined_at: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const orgId = useUserStore((s) => s.orgId);
  const orgName = useUserStore((s) => s.orgName);
  const companyId = useUserStore((s) => s.companyId);
  const isOnboarded = useUserStore((s) => s.isOnboarded);
  const onboardingCompletedAt = useUserStore((s) => s.onboardingCompletedAt);

  // Profile Form State
  const [profileForm, setProfileForm] = useState({
    name: orgName || "",
    industry: "Manufacturing & Industrial",
    country: "US",
  });
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState<string | null>(null);

  // Members State
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [newMemberUserId, setNewMemberUserId] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("analyst");
  const [newMemberPersona, setNewMemberPersona] = useState("risk_manager");
  const [isInviting, setIsInviting] = useState(false);

  // Preferences State
  const [alertThreshold, setAlertThreshold] = useState(4);
  const [digestFrequency, setDigestFrequency] = useState("daily");

  // Load Members
  const loadMembers = useCallback(async () => {
    if (!orgId) return;
    setIsLoadingMembers(true);
    try {
      const res = await fetch(`/api/v1/organizations/${orgId}/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data.data || []);
      } else {
        setMembers([]);
      }
    } catch {
      setMembers([]);
    } finally {
      setIsLoadingMembers(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadMembers();
    if (orgName) {
      setProfileForm((prev) => ({ ...prev, name: orgName }));
    }
  }, [loadMembers, orgName]);

  // Save Profile
  const handleSaveProfile = async () => {
    if (!orgId) return;
    setIsSavingProfile(true);
    setProfileSuccessMsg(null);
    try {
      const res = await fetch(`/api/v1/organizations/${orgId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileForm),
      });

      if (res.ok) {
        setProfileSuccessMsg("Organization profile updated successfully.");
        setTimeout(() => setProfileSuccessMsg(null), 3500);
      }
    } catch {
      // Handle error
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Invite Member
  const handleInviteMember = async () => {
    if (!orgId || !newMemberUserId.trim()) return;
    setIsInviting(true);
    try {
      const res = await fetch(`/api/v1/organizations/${orgId}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: newMemberUserId.trim(),
          role: newMemberRole,
          persona: newMemberPersona,
        }),
      });

      if (res.ok) {
        setIsInviteModalOpen(false);
        setNewMemberUserId("");
        await loadMembers();
      }
    } catch {
      // Handle error
    } finally {
      setIsInviting(false);
    }
  };

  // Remove Member
  const handleRemoveMember = async (userId: string) => {
    if (!orgId || !confirm(`Remove user ${userId} from organization?`)) return;
    try {
      const res = await fetch(`/api/v1/organizations/${orgId}/members/${userId}`, {
        method: "DELETE",
      });
      if (res.ok || res.status === 204) {
        await loadMembers();
      }
    } catch {
      // Handle error
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Organization Settings</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Tenant identity, team member roles, and risk assessment preferences.
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-card/70 border border-border/70 p-1">
          <TabsTrigger value="profile" className="gap-2 text-xs">
            <Building2 className="h-3.5 w-3.5" /> Organization Profile
          </TabsTrigger>
          <TabsTrigger value="members" className="gap-2 text-xs">
            <Users className="h-3.5 w-3.5" /> Team & Members
          </TabsTrigger>
          <TabsTrigger value="preferences" className="gap-2 text-xs">
            <Sliders className="h-3.5 w-3.5" /> Risk Preferences
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: Profile */}
        <TabsContent value="profile" className="space-y-4">
          <Card className="glass-panel border-border/80 shadow-antigravity">
            <CardHeader>
              <CardTitle className="text-base font-semibold">Tenant Identity</CardTitle>
              <CardDescription className="text-xs">
                Organization details and canonical company entity connection.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 text-xs">
              {profileSuccessMsg && (
                <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{profileSuccessMsg}</span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-muted-foreground font-medium">Organization Name</label>
                  <Input
                    className="bg-card/90 text-xs"
                    value={profileForm.name}
                    onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-muted-foreground font-medium">Industry Sector</label>
                  <Input
                    className="bg-card/90 text-xs"
                    value={profileForm.industry}
                    onChange={(e) => setProfileForm({ ...profileForm, industry: e.target.value })}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-muted-foreground font-medium">Headquarters Country (ISO)</label>
                  <Input
                    className="bg-card/90 text-xs"
                    maxLength={2}
                    value={profileForm.country}
                    onChange={(e) =>
                      setProfileForm({ ...profileForm, country: e.target.value.toUpperCase() })
                    }
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-muted-foreground font-medium">Claimed Canonical Entity</label>
                  <div className="flex items-center gap-2">
                    <Input
                      disabled
                      className="bg-muted/40 font-mono text-xs"
                      value={companyId || "No canonical entity claimed yet"}
                    />
                    <Button variant="outline" size="sm" asChild className="shrink-0 text-xs">
                      <Link href="/onboarding">Claim Entity</Link>
                    </Button>
                  </div>
                </div>
              </div>

              {/* Onboarding Status Box */}
              <div className="rounded-xl border border-border/70 bg-card/60 p-4 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-foreground block text-xs">
                    Supply Base Onboarding Status
                  </span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {isOnboarded
                      ? `Completed on ${new Date(onboardingCompletedAt || "").toLocaleDateString()}`
                      : "Setup incomplete: seed suppliers and calibrate risk scoring."}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={isOnboarded ? "default" : "destructive"}>
                    {isOnboarded ? "Active & Seeded" : "Setup Required"}
                  </Badge>
                  <Button variant="outline" size="sm" asChild className="gap-1.5 text-xs">
                    <Link href="/onboarding">
                      <RotateCcw className="h-3.5 w-3.5" /> Re-run Setup
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>

            <CardFooter className="border-t border-border/60 pt-4 flex justify-end">
              <Button
                size="sm"
                disabled={isSavingProfile}
                onClick={handleSaveProfile}
                className="gap-2 text-xs"
              >
                {isSavingProfile ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save Changes
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* TAB 2: Members */}
        <TabsContent value="members" className="space-y-4">
          <Card className="glass-panel border-border/80 shadow-antigravity">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold">Team Members & Role Access</CardTitle>
                <CardDescription className="text-xs">
                  Manage organization access, assign personas (Risk Manager / Category Manager), and scope permissions.
                </CardDescription>
              </div>
              <Button size="sm" onClick={() => setIsInviteModalOpen(true)} className="gap-1.5 text-xs">
                <Plus className="h-3.5 w-3.5" /> Invite Member
              </Button>
            </CardHeader>

            <CardContent>
              <div className="rounded-lg border border-border/70 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] border-b border-border/60">
                    <tr>
                      <th className="py-2.5 px-3.5">User Identity</th>
                      <th className="py-2.5 px-3.5">Role</th>
                      <th className="py-2.5 px-3.5">Persona</th>
                      <th className="py-2.5 px-3.5">Assigned Categories</th>
                      <th className="py-2.5 px-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {isLoadingMembers ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin mx-auto text-primary" />
                        </td>
                      </tr>
                    ) : members.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">
                          No members configured.
                        </td>
                      </tr>
                    ) : (
                      members.map((mem) => (
                        <tr key={mem.id} className="hover:bg-accent/20">
                          <td className="py-2.5 px-3.5 font-medium text-foreground">
                            {mem.user_id}
                          </td>
                          <td className="py-2.5 px-3.5">
                            <Badge
                              variant={mem.role === "org_admin" ? "default" : "outline"}
                              className="capitalize text-[10px]"
                            >
                              {mem.role.replace("_", " ")}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-3.5 text-muted-foreground capitalize">
                            {(mem.persona || "risk_manager").replace("_", " ")}
                          </td>
                          <td className="py-2.5 px-3.5 text-muted-foreground">
                            {mem.assigned_categories?.length > 0
                              ? mem.assigned_categories.join(", ")
                              : "All Categories"}
                          </td>
                          <td className="py-2.5 px-3.5 text-right">
                            {mem.role !== "org_admin" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRemoveMember(mem.user_id)}
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: Preferences */}
        <TabsContent value="preferences" className="space-y-4">
          <Card className="glass-panel border-border/80 shadow-antigravity">
            <CardHeader>
              <CardTitle className="text-base font-semibold">Triage & Alert Thresholds</CardTitle>
              <CardDescription className="text-xs">
                Configure immediate alert triggers vs. daily digest bundling (§Part O).
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 text-xs">
              <div className="space-y-2">
                <label className="text-foreground font-medium block">
                  Immediate Notification Severity Trigger
                </label>
                <p className="text-[11px] text-muted-foreground">
                  Events triggering risk assessments at or above this threshold dispatch instant alerts. Lower severity events are collected into the digest.
                </p>
                <div className="flex gap-2 pt-1">
                  {[
                    { val: 5, label: "Level 5 Only (Severe / Outage)" },
                    { val: 4, label: "Level 4 & 5 (High & Critical)" },
                    { val: 3, label: "Level 3+ (Moderate & Above)" },
                  ].map((opt) => (
                    <button
                      key={opt.val}
                      type="button"
                      onClick={() => setAlertThreshold(opt.val)}
                      className={cn(
                        "rounded-lg border p-2.5 text-xs text-left transition-colors",
                        alertThreshold === opt.val
                          ? "border-primary bg-primary/10 text-primary font-medium shadow-sm"
                          : "border-border/70 bg-card/60 text-muted-foreground hover:bg-accent/40"
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-border/60 space-y-2">
                <label className="text-foreground font-medium block">Digest Schedule</label>
                <select
                  value={digestFrequency}
                  onChange={(e) => setDigestFrequency(e.target.value)}
                  className="h-9 rounded-md border border-input bg-card/80 px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="realtime">Real-time alerts only</option>
                  <option value="daily">Daily Morning Digest (08:00 Local)</option>
                  <option value="weekly">Weekly Strategic Summary (Monday 08:00)</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Invite Member Modal */}
      <Dialog open={isInviteModalOpen} onOpenChange={setIsInviteModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Invite Organization Member</DialogTitle>
            <DialogDescription className="text-xs">
              Add a team member and grant appropriate role-based permissions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label className="text-muted-foreground font-medium">Clerk User ID / Email *</label>
              <Input
                placeholder="user_2Xy..."
                value={newMemberUserId}
                onChange={(e) => setNewMemberUserId(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-muted-foreground font-medium">Role Permission Tier</label>
              <select
                value={newMemberRole}
                onChange={(e) => setNewMemberRole(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-card/80 px-3 text-xs text-foreground"
              >
                <option value="analyst">Analyst (Suppliers & Investigation)</option>
                <option value="org_user">Org User (Read-only + Alerts triage)</option>
                <option value="read_only">Read Only (Observer)</option>
                <option value="org_admin">Org Admin (Full Tenant Control)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-muted-foreground font-medium">Default Persona View</label>
              <select
                value={newMemberPersona}
                onChange={(e) => setNewMemberPersona(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-card/80 px-3 text-xs text-foreground"
              >
                <option value="risk_manager">Risk Manager (Geopolitical & Regulatory)</option>
                <option value="category_manager">Category Manager (Spend & Sourcing)</option>
              </select>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" size="sm" onClick={() => setIsInviteModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={isInviting || !newMemberUserId.trim()}
              onClick={handleInviteMember}
              className="gap-2"
            >
              {isInviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
