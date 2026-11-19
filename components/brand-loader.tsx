"use client";

import React from "react";

interface BrandLoaderProps {
  label?: string;
  size?: number;
  className?: string;
}

export function BrandLoader({
  label = "Synthesizing intelligence...",
  size = 48,
  className = "",
}: BrandLoaderProps) {
  return (
    <div
      className={`brand-loader-container ${className}`}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "14px",
        padding: "32px 20px",
      }}
    >
      <div
        className="brand-loader-pulse"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Ambient glow ring */}
        <div
          style={{
            position: "absolute",
            inset: "-8px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(54, 197, 222, 0.25) 0%, transparent 70%)",
            animation: "loaderGlowPulse 2s ease-in-out infinite",
          }}
        />
        {/* Rotating border or pulse */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/brand/neomon-symbol.png"
          alt="Loading..."
          width={size}
          height={size}
          style={{
            objectFit: "contain",
            filter: "drop-shadow(0 0 12px rgba(54, 197, 222, 0.6))",
            animation: "loaderFloatPulse 2s ease-in-out infinite alternate",
          }}
        />
      </div>
      {label && (
        <span
          style={{
            fontSize: "12px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            color: "#94a3b8",
            textTransform: "uppercase",
            fontFamily: "monospace",
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
}
