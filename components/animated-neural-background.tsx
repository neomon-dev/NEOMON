"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseAlpha: number;
  alpha: number;
  color: string;
  pulseSpeed: number;
  pulsePhase: number;
}

interface NeuralParticleCanvasProps {
  density?: "high" | "medium" | "low";
  interactive?: boolean;
  className?: string;
}

const PARTICLE_COLORS = [
  "#38bdf8", // Electric blue
  "#06b6d4", // Intelligence cyan
  "#818cf8", // Indigo
  "#c084fc", // Violet
  "#67e8f9", // Light cyan
];

export function NeuralParticleCanvas({
  density = "medium",
  interactive = true,
  className = "",
}: NeuralParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const animFrameId = useRef<number | null>(null);
  const mouseRef = useRef<{ x: number | null; y: number | null }>({ x: null, y: null });
  const isTabVisible = useRef(true);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Check reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  // Listen to visibilitychange to pause RAF when tab is hidden
  useEffect(() => {
    const handleVisibilityChange = () => {
      isTabVisible.current = document.visibilityState === "visible";
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!interactive || prefersReducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }, [interactive, prefersReducedMotion]);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = { x: null, y: null };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let particles: Particle[] = [];

    const calculateParticleCount = (w: number, h: number) => {
      const area = w * h;
      const divisor = density === "high" ? 9000 : density === "medium" ? 14000 : 22000;
      const count = Math.floor(area / divisor);
      const min = density === "high" ? 40 : density === "medium" ? 25 : 15;
      const max = density === "high" ? 110 : density === "medium" ? 75 : 45;
      return Math.min(max, Math.max(min, count));
    };

    const initParticles = (w: number, h: number) => {
      const count = calculateParticleCount(w, h);
      const arr: Particle[] = [];
      for (let i = 0; i < count; i++) {
        const radius = Math.random() * 1.8 + 0.8;
        const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
        const speed = Math.random() * 0.35 + 0.12;
        const angle = Math.random() * Math.PI * 2;
        arr.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          radius,
          baseAlpha: Math.random() * 0.45 + 0.25,
          alpha: 0.3,
          color,
          pulseSpeed: Math.random() * 0.02 + 0.008,
          pulsePhase: Math.random() * Math.PI * 2,
        });
      }
      return arr;
    };

    const resize = () => {
      const rect = container.getBoundingClientRect();
      width = rect.width;
      height = rect.height;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.scale(dpr, dpr);
      particles = initParticles(width, height);
    };

    const resizeObserver = new ResizeObserver(() => {
      resize();
    });
    resizeObserver.observe(container);
    resize();

    const maxDist = density === "high" ? 135 : 115;
    const mouseRadius = 150;

    let lastTime = performance.now();

    const render = (time: number) => {
      if (!isTabVisible.current) {
        animFrameId.current = requestAnimationFrame(render);
        return;
      }

      const dt = Math.min((time - lastTime) / 16.67, 2.0);
      lastTime = time;

      ctx.clearRect(0, 0, width, height);

      const mouse = mouseRef.current;

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        if (!prefersReducedMotion) {
          p.x += p.vx * dt;
          p.y += p.vy * dt;

          // Wrap edges smoothly
          if (p.x < -10) p.x = width + 10;
          else if (p.x > width + 10) p.x = -10;
          if (p.y < -10) p.y = height + 10;
          else if (p.y > height + 10) p.y = -10;

          // Mouse gentle repulsion / interaction
          if (mouse.x !== null && mouse.y !== null) {
            const dx = p.x - mouse.x;
            const dy = p.y - mouse.y;
            const dist = Math.hypot(dx, dy);
            if (dist < mouseRadius && dist > 0) {
              const force = (1 - dist / mouseRadius) * 0.45;
              p.x += (dx / dist) * force * dt;
              p.y += (dy / dist) * force * dt;
            }
          }

          // Shimmer / pulse
          p.pulsePhase += p.pulseSpeed * dt;
          p.alpha = p.baseAlpha + Math.sin(p.pulsePhase) * 0.15;
        }

        // Draw particle node
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = Math.max(0.1, Math.min(0.9, p.alpha));
        ctx.fill();

        // Node glow
        if (p.radius > 1.5) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius * 2.2, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.alpha * 0.18;
          ctx.fill();
        }
      }

      // Draw interconnecting synaptic lines
      ctx.lineWidth = 0.85;
      for (let i = 0; i < particles.length; i++) {
        const p1 = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.hypot(dx, dy);

          if (dist < maxDist) {
            const lineAlpha = (1 - dist / maxDist) * 0.28;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = p1.color;
            ctx.globalAlpha = lineAlpha;
            ctx.stroke();
          }
        }

        // Connect to mouse cursor
        if (mouse.x !== null && mouse.y !== null) {
          const dx = p1.x - mouse.x;
          const dy = p1.y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < mouseRadius) {
            const lineAlpha = (1 - dist / mouseRadius) * 0.4;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.strokeStyle = "#38bdf8";
            ctx.globalAlpha = lineAlpha;
            ctx.stroke();
          }
        }
      }

      ctx.globalAlpha = 1.0;

      if (!prefersReducedMotion) {
        animFrameId.current = requestAnimationFrame(render);
      }
    };

    if (prefersReducedMotion) {
      render(performance.now());
    } else {
      animFrameId.current = requestAnimationFrame(render);
    }

    return () => {
      if (animFrameId.current !== null) {
        cancelAnimationFrame(animFrameId.current);
      }
      resizeObserver.disconnect();
    };
  }, [density, prefersReducedMotion]);

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`neural-canvas-container ${className}`}
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: interactive ? "auto" : "none",
        zIndex: 0,
      }}
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      />
    </div>
  );
}

export function AtmosphericAurora({
  className = "",
  showGrid = true,
  showScanlines = true,
}: {
  className?: string;
  showGrid?: boolean;
  showScanlines?: boolean;
}) {
  return (
    <div
      className={`atmospheric-aurora ${className}`}
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
      }}
      aria-hidden="true"
    >
      {/* Aurora Ambient Light Orbs */}
      <div className="aurora-orb aurora-orb-1" />
      <div className="aurora-orb aurora-orb-2" />
      <div className="aurora-orb aurora-orb-3" />

      {/* Cybernetic Scientific Grid */}
      {showGrid && <div className="cyber-grid-overlay" />}

      {/* High-tech Micro Scanlines */}
      {showScanlines && <div className="cyber-scanline-overlay" />}
    </div>
  );
}

export function ImmersiveBackground({
  variant = "hero",
  interactive = true,
  className = "",
}: {
  variant?: "hero" | "workspace" | "subtle";
  interactive?: boolean;
  className?: string;
}) {
  const density = variant === "hero" ? "high" : variant === "workspace" ? "medium" : "low";

  return (
    <div
      className={`immersive-bg-layer ${className}`}
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
      }}
      aria-hidden="true"
    >
      <AtmosphericAurora
        showGrid={variant !== "subtle"}
        showScanlines={variant === "hero"}
      />
      <NeuralParticleCanvas
        density={density}
        interactive={interactive}
      />
    </div>
  );
}
