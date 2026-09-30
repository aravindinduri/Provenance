import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { GitFork } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function GraphPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Supply Chain Graph Visualizer</h1>
          <p className="text-sm text-muted-foreground">Multi-tier dependency topology, single points of failure, and bottleneck analysis.</p>
        </div>
      </div>
      <Card className="glass-panel p-8 text-center border-dashed">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500">
            <GitFork className="h-6 w-6" />
          </div>
          <CardTitle className="text-lg">Interactive Topology Graph (Phase 8)</CardTitle>
          <CardDescription className="max-w-md mx-auto text-xs">
            Interactive Cytoscape / WebGL directed dependency visualizer with blast radius highlights is slated for Phase 8.
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
