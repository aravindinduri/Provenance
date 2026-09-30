import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Database } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function DataPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Data Sources & Ingestion Pipelines</h1>
          <p className="text-sm text-muted-foreground">Connector health, ingestion lag, and feed telemetry.</p>
        </div>
      </div>
      <Card className="glass-panel p-8 text-center border-dashed">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500">
            <Database className="h-6 w-6" />
          </div>
          <CardTitle className="text-lg">Connector Health Dashboard (Phase 10)</CardTitle>
          <CardDescription className="max-w-md mx-auto text-xs">
            Deep-dive pipeline metrics, token-bucket throttling status, and raw payload audit records.
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
