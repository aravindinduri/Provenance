import Link from "next/link";
import { Compass, MoveLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-[600px] w-full flex-col items-center justify-center p-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4 shadow-glow-primary">
        <Compass className="h-8 w-8 animate-pulse" />
      </div>
      <span className="text-sm font-semibold tracking-wider uppercase text-primary">
        404 — Not Found
      </span>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">Node Unmapped</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        The requested resource, entity, or intelligence feed does not exist or has
        been relocated within the Provenance network graph.
      </p>
      <div className="mt-6 flex gap-3">
        <Button asChild variant="default">
          <Link href="/dashboard">
            <MoveLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
}
