"use client";

import React from "react";
import { Package } from "lucide-react";
import { ItemCatalog } from "@/components/procurement/item-catalog";

export default function ItemsPage(): React.ReactElement {
  return (
    <div className="flex-1 space-y-6 p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 flex items-center gap-2">
            <Package className="h-6 w-6 text-[#FA651E]" />
            Item Catalog &amp; Material Master
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Standard parts, raw materials, units of measure, and default pricing for requisitions and purchase orders.
          </p>
        </div>
      </div>

      {/* Main Component */}
      <ItemCatalog />
    </div>
  );
}
