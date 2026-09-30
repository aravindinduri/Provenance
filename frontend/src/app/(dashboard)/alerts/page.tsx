import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AlertsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Alerts & Signal Stream</h1>
          <p className="text-sm text-muted-foreground">Real-time regulatory, sanctions, and supply disruption warnings.</p>
        </div>
      </div>
      <Card className="glass-panel p-8 text-center border-dashed">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <CardTitle className="text-lg">Alert Center (Phase 6)</CardTitle>
          <CardDescription className="max-w-md mx-auto text-xs">
            Full faceted filtering, severity triage, and alert resolution workflow are mapped for Phase 6.
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
