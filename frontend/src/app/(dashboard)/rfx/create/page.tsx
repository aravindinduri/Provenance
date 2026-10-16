"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RFxCreationWizard } from "@/components/procurement/rfx-creation-wizard";

export default function CreateRFxPage(): React.ReactElement {
  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/rfx">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-neutral-500 hover:text-neutral-900">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <FileQuestion className="h-5 w-5 text-[#FA651E]" />
            New Sourcing Event Wizard
          </h1>
          <p className="text-xs text-neutral-500 mt-0.5">
            Configure RFQ/RFP event specifications, weighted evaluation matrix, and invite vendors.
          </p>
        </div>
      </div>

      {/* Wizard */}
      <RFxCreationWizard />
    </div>
  );
}
