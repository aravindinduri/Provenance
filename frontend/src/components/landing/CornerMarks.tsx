import React from "react";

interface CornerMarksProps {
  className?: string;
  size?: number;
  color?: string;
  thickness?: number;
  offset?: number;
}

/**
 * Technical Corner Registration Marks: ┌ ┐ └ ┘
 * Faithfully recreates Gojiberry's signature engineering bracket styling.
 */
export function CornerMarks({
  className = "",
  size = 8,
  color = "#c7c7c7",
  thickness = 1,
  offset = -4,
}: CornerMarksProps): React.ReactElement {
  const style = (top?: boolean, left?: boolean): React.CSSProperties => ({
    position: "absolute",
    width: `${size}px`,
    height: `${size}px`,
    top: top ? `${offset}px` : undefined,
    bottom: !top ? `${offset}px` : undefined,
    left: left ? `${offset}px` : undefined,
    right: !left ? `${offset}px` : undefined,
    borderTop: top ? `${thickness}px solid ${color}` : undefined,
    borderBottom: !top ? `${thickness}px solid ${color}` : undefined,
    borderLeft: left ? `${thickness}px solid ${color}` : undefined,
    borderRight: !left ? `${thickness}px solid ${color}` : undefined,
    pointerEvents: "none",
    transition: "border-color 0.2s ease, transform 0.2s ease",
  });

  return (
    <div className={`pointer-events-none absolute inset-0 ${className}`} aria-hidden="true">
      <span style={style(true, true)} />
      <span style={style(true, false)} />
      <span style={style(false, true)} />
      <span style={style(false, false)} />
    </div>
  );
}
