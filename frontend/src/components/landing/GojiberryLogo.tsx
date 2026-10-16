import React from "react";
import Link from "next/link";

interface GojiberryLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  withLink?: boolean;
}

export function GojiberryLogo({
  className = "",
  size = "md",
  withLink = true,
}: GojiberryLogoProps): React.ReactElement {
  const iconSizes = {
    sm: "w-6 h-6",
    md: "w-7 h-7",
    lg: "w-9 h-9",
  };

  const textSizes = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl",
  };

  const content = (
    <div className={`inline-flex items-center gap-2.5 font-bold tracking-tight text-neutral-950 select-none group ${className}`}>
      {/* Gojiberry Origami Faceted Berry Vector Icon */}
      <svg
        className={`${iconSizes[size]} transition-transform duration-300 group-hover:scale-105`}
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="goji-top" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FD8A6B" />
            <stop offset="100%" stopColor="#FA651E" />
          </linearGradient>
          <linearGradient id="goji-left" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FA651E" />
            <stop offset="100%" stopColor="#E04803" />
          </linearGradient>
          <linearGradient id="goji-right" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFB39E" />
            <stop offset="100%" stopColor="#FD8A6B" />
          </linearGradient>
        </defs>

        {/* Back / Top Fold */}
        <polygon
          points="18,3 31,10.5 18,18 5,10.5"
          fill="url(#goji-top)"
          opacity="0.95"
        />
        {/* Left Fold */}
        <polygon
          points="5,10.5 18,18 18,33 5,25.5"
          fill="url(#goji-left)"
        />
        {/* Right Fold */}
        <polygon
          points="18,18 31,10.5 31,25.5 18,33"
          fill="url(#goji-right)"
        />
        {/* Subtle Inner Fold Notch */}
        <polygon
          points="18,18 24,14.5 24,22 18,25.5"
          fill="#FA651E"
          opacity="0.4"
        />
      </svg>

      <span className={`${textSizes[size]} font-extrabold tracking-[-0.04em] text-[#0A0A0A]`}>
        gojiberry
      </span>
    </div>
  );

  if (withLink) {
    return (
      <Link href="/" className="inline-flex focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FA651E] rounded-md">
        {content}
      </Link>
    );
  }

  return content;
}
