"use client";

import React, { useRef, useState, type MouseEvent, type ReactNode } from "react";

interface SpotlightCardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  spotlightColor?: string;
  borderColor?: string;
  onClick?: () => void;
}

export function SpotlightCard({
  children,
  className = "",
  style,
  spotlightColor = "rgba(37, 217, 242, 0.14)",
  borderColor = "rgba(37, 217, 242, 0.3)",
  onClick,
}: SpotlightCardProps) {
  const divRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return;
    const rect = divRef.current.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseEnter = () => {
    setOpacity(1);
  };

  const handleMouseLeave = () => {
    setOpacity(0);
  };

  const activeBorderColor = opacity > 0 ? borderColor : "var(--border, rgba(37, 217, 242, 0.12))";

  // Prevent React shorthand vs longhand style property conflicts (e.g. border vs borderBottom)
  const {
    border: propBorder,
    borderTop: propBorderTop,
    borderRight: propBorderRight,
    borderBottom: propBorderBottom,
    borderLeft: propBorderLeft,
    ...restStyle
  } = style || {};

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      className={`spotlight-card ${className}`}
      style={{
        position: "relative",
        background: "var(--panel, rgba(8, 25, 45, 0.40))",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderTop: propBorderTop || propBorder || `1px solid ${activeBorderColor}`,
        borderRight: propBorderRight || propBorder || `1px solid ${activeBorderColor}`,
        borderBottom: propBorderBottom || propBorder || `1px solid ${activeBorderColor}`,
        borderLeft: propBorderLeft || propBorder || `1px solid ${activeBorderColor}`,
        borderRadius: "var(--radius-md, 10px)",
        overflow: "hidden",
        transition: "border-color 0.25s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease",
        boxShadow: opacity > 0 ? "0 8px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(37, 217, 242, 0.1)" : "0 4px 16px rgba(0, 0, 0, 0.4)",
        ...restStyle,
      }}
    >
      {/* Specular Spotlight Overlay */}
      <div
        style={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          opacity,
          transition: "opacity 0.25s ease",
          background: `radial-gradient(400px circle at ${position.x}px ${position.y}px, ${spotlightColor}, transparent 65%)`,
          zIndex: 1,
        }}
      />
      {/* Foreground Content */}
      <div style={{ position: "relative", zIndex: 2 }}>{children}</div>
    </div>
  );
}
