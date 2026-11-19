"use client";

import React, { useEffect, useState } from "react";

interface DecryptedTextProps {
  text: string;
  speed?: number;
  maxIterations?: number;
  className?: string;
  characters?: string;
  animateOnMount?: boolean;
}

const DEFAULT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_#⌘⚡❖◈";

export function DecryptedText({
  text,
  speed = 30,
  maxIterations = 10,
  className = "",
  characters = DEFAULT_CHARS,
  animateOnMount = true,
}: DecryptedTextProps) {
  const [displayText, setDisplayText] = useState<string>(animateOnMount ? "" : text);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    let iteration = 0;
    const target = text;
    let prefersReducedMotion = false;

    if (typeof window !== "undefined" && window.matchMedia) {
      prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    if (prefersReducedMotion) {
      setDisplayText(target);
      return;
    }

    const interval = setInterval(() => {
      setDisplayText(() =>
        target
          .split("")
          .map((char, index) => {
            if (char === " " || index < iteration / 2) {
              return target[index];
            }
            return characters[Math.floor(Math.random() * characters.length)];
          })
          .join("")
      );

      iteration += 1;
      if (iteration >= target.length * 2 + maxIterations) {
        clearInterval(interval);
        setDisplayText(target);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, maxIterations, characters, isHovered]);

  return (
    <span
      className={className}
      onMouseEnter={() => setIsHovered((prev) => !prev)}
      style={{ fontFamily: "monospace", letterSpacing: "0.06em" }}
    >
      {displayText || text}
    </span>
  );
}
