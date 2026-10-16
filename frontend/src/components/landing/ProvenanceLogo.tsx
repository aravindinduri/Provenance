import React from "react";
import Image from "next/image";

interface ProvenanceLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  inverted?: boolean;
  withTagline?: boolean;
}

/**
 * Provenance Official Brand Logo Component
 * Uses /logo.png from the public assets directory.
 */
export function ProvenanceLogo({
  className = "",
  size = "md",
  inverted = false,
  withTagline = false,
}: ProvenanceLogoProps): React.ReactElement {
  const sizeMap = {
    sm: { width: 110, height: 32 },
    md: { width: 140, height: 42 },
    lg: { width: 180, height: 54 },
  };

  const { width, height } = sizeMap[size];

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      <div className="relative flex items-center justify-center overflow-hidden">
        <Image
          src="/logo.png"
          alt="Provenance — Agentic Procurement & Risk Platform"
          width={width}
          height={height}
          priority
          className={`h-auto w-auto object-contain transition-opacity duration-200 ${inverted ? "brightness-0 invert" : ""
            }`}
          style={{ maxHeight: `${height}px` }}
        />
      </div>
    </div>
  );
}
