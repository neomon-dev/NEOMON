"use client";

import React from "react";

interface RadarScanningProps {
  size?: number;
  color?: string;
  className?: string;
}

export function RadarScanning({
  size = 180,
  color = "#25D9F2",
  className = "",
}: RadarScanningProps) {
  return (
    <div
      className={`radar-scanning-container ${className}`}
      style={{
        position: "relative",
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "50%",
        border: `1px solid rgba(37, 217, 242, 0.25)`,
        boxShadow: `0 0 20px rgba(37, 217, 242, 0.1)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* Concentric Coordinate Rings */}
      <div
        style={{
          position: "absolute",
          width: "66%",
          height: "66%",
          borderRadius: "50%",
          border: "1px dashed rgba(37, 217, 242, 0.2)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: "33%",
          height: "33%",
          borderRadius: "50%",
          border: "1px solid rgba(37, 217, 242, 0.3)",
        }}
      />
      {/* Crosshairs */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "1px",
          background: "rgba(37, 217, 242, 0.15)",
        }}
      />
      <div
        style={{
          position: "absolute",
          height: "100%",
          width: "1px",
          background: "rgba(37, 217, 242, 0.15)",
        }}
      />
      {/* Rotating Sweep Beam */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: `conic-gradient(from 0deg, transparent 0deg, transparent 270deg, ${color}22 330deg, ${color}88 360deg)`,
          animation: "radarSweep 3.5s linear infinite",
        }}
      />
      {/* Center blip */}
      <div
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          backgroundColor: color,
          boxShadow: `0 0 10px ${color}`,
        }}
      />
    </div>
  );
}
