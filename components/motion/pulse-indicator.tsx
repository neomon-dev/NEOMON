"use client";

import React from "react";

interface PulseIndicatorProps {
  status?: "active" | "warning" | "error" | "mint" | "cyan" | "violet";
  label?: string;
  size?: number;
  className?: string;
}

const COLOR_MAP = {
  active: "#25D9F2",
  cyan: "#25D9F2",
  mint: "#35E0B1",
  warning: "#FFB547",
  error: "#FF5277",
  violet: "#8564FF",
};

export function PulseIndicator({
  status = "active",
  label,
  size = 8,
  className = "",
}: PulseIndicatorProps) {
  const color = COLOR_MAP[status] || COLOR_MAP.active;

  return (
    <span
      className={`inline-flex items-center gap-2 ${className}`}
      style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
    >
      <span
        style={{
          position: "relative",
          display: "inline-flex",
          width: `${size}px`,
          height: `${size}px`,
        }}
      >
        <span
          style={{
            position: "absolute",
            inset: "-2px",
            borderRadius: "50%",
            backgroundColor: color,
            opacity: 0.75,
            animation: "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
          }}
        />
        <span
          style={{
            position: "relative",
            display: "inline-flex",
            borderRadius: "50%",
            width: `${size}px`,
            height: `${size}px`,
            backgroundColor: color,
            boxShadow: `0 0 8px ${color}`,
          }}
        />
      </span>
      {label && (
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            fontFamily: "monospace",
            color: "#ECF5FF",
          }}
        >
          {label}
        </span>
      )}
    </span>
  );
}
