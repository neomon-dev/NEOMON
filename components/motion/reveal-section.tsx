"use client";

import React, { type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";

interface RevealSectionProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  delay?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
  className?: string;
}

export function RevealSection({
  children,
  delay = 0,
  direction = "up",
  className = "",
  ...props
}: RevealSectionProps) {
  const getOffset = () => {
    switch (direction) {
      case "up":
        return { y: 16, x: 0 };
      case "down":
        return { y: -16, x: 0 };
      case "left":
        return { x: 20, y: 0 };
      case "right":
        return { x: -20, y: 0 };
      default:
        return { x: 0, y: 0 };
    }
  };

  const offset = getOffset();

  return (
    <motion.div
      initial={{ opacity: 0, ...offset }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration: 0.45,
        delay,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}
