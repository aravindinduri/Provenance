import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Settings as SettingsIcon } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Organization Settings</h1>
          <p className="text-sm text-muted-foreground">Manage tenant configuration, API tokens, and webhook endpoints.</p>
        </div>
      </div>
      <Card className="glass-panel p-8 text-center border-dashed">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-500/10 text-slate-400">
            <SettingsIcon className="h-6 w-6" />
          </div>
          <CardTitle className="text-lg">Tenant Preferences</CardTitle>
          <CardDescription className="max-w-md mx-auto text-xs">
            Manage your organization membership, Clerk role bindings, and notification preferences.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard">Return to Dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
