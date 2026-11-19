"use client";

import React, { useEffect, useRef, useState } from "react";

interface AnimatedCounterProps {
  value: number | string;
  duration?: number;
  className?: string;
  formatter?: (val: number) => string;
}

export function AnimatedCounter({
  value,
  duration = 1200,
  className = "",
  formatter,
}: AnimatedCounterProps) {
  const numericValue = typeof value === "number" ? value : parseFloat(String(value)) || 0;
  const isNaNValue = typeof value === "string" && isNaN(parseFloat(value));
  const [displayValue, setDisplayValue] = useState<number>(0);
  const startTimestampRef = useRef<number | null>(null);
  const currentValueRef = useRef<number>(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (isNaNValue) return;

    let prefersReducedMotion = false;
    if (typeof window !== "undefined" && window.matchMedia) {
      prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    if (prefersReducedMotion) {
      currentValueRef.current = numericValue;
      setDisplayValue(numericValue);
      return;
    }

    const startVal = currentValueRef.current;
    startTimestampRef.current = null;

    const step = (timestamp: number) => {
      if (!startTimestampRef.current) startTimestampRef.current = timestamp;
      const progress = Math.min((timestamp - startTimestampRef.current) / duration, 1);
      // Ease out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startVal + (numericValue - startVal) * easeProgress);

      currentValueRef.current = current;
      setDisplayValue(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };

    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [numericValue, duration, isNaNValue]);

  if (isNaNValue) {
    return <span className={className}>{value}</span>;
  }

  const formatted = formatter ? formatter(displayValue) : displayValue.toLocaleString();

  return (
    <span className={`tabular-nums ${className}`} style={{ fontVariantNumeric: "tabular-nums" }}>
      {formatted}
    </span>
  );
}
