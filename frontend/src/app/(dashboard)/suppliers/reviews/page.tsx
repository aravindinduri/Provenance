"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Building2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EntityReviewQueue } from "@/components/entity-reviews/review-queue";

export default function EntityReviewsPage(): React.JSX.Element {
  return (
    <div className="space-y-6">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground">
              <Link href="/suppliers">
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to Suppliers
              </Link>
            </Button>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            Entity Resolution Review Queue
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-normal bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Gemini AI Assisted
            </span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Human-in-the-loop review for ambiguous supplier mentions (Stage 7). Deterministic cascade (Stages 1-5) resolves ≥80% before Stage 6 adjudication.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild className="text-xs">
            <Link href="/suppliers">
              <Building2 className="h-3.5 w-3.5 mr-1.5" />
              Supplier Directory
            </Link>
          </Button>
        </div>
      </div>

      {/* Review Queue Component */}
      <EntityReviewQueue />
    </div>
  );
}
