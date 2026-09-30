import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Building2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function SuppliersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Supplier Directory & Registry</h1>
          <p className="text-sm text-muted-foreground">Tier-1 vendors, sub-tier graph nodes, and risk profile scores.</p>
        </div>
      </div>
      <Card className="glass-panel p-8 text-center border-dashed">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-500">
            <Building2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-lg">Supplier Directory (Phase 7)</CardTitle>
          <CardDescription className="max-w-md mx-auto text-xs">
            Detailed supplier dossier, bill-of-materials traceability, and sanctions lookup table are scheduled for Phase 7.
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
