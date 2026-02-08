"use client";

import { type ReactNode } from "react";

interface MarqueeProps {
  children: ReactNode;
  /** Direction: "left" (default) or "right" */
  direction?: "left" | "right";
  /** Duration for one full cycle in seconds */
  duration?: number;
  /** CSS class for the outer container */
  className?: string;
}

export function Marquee({
  children,
  direction = "left",
  duration = 30,
  className = "",
}: MarqueeProps) {
  const trackClass =
    direction === "right"
      ? "marquee-track marquee-track-reverse"
      : "marquee-track";

  return (
    <div className={`marquee-container ${className}`}>
      <div
        className={trackClass}
        style={{ "--marquee-duration": `${duration}s` } as React.CSSProperties}
      >
        {/* Original content */}
        {children}
        {/* Duplicate for seamless loop */}
        {children}
      </div>
    </div>
  );
}
