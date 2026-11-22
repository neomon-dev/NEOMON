"use client";

import React, { useEffect, useRef, useState } from "react";

export interface DotLensProps {
  /** Background color between dots (default: #06111F) */
  background?: string;
  /** Idle/distant dot color (default: #0A223B) */
  baseColor?: string;
  /** Intermediate glow color (default: #647BFF) */
  midColor?: string;
  /** Focused/peak dot color (default: #36C5DE) */
  accentColor?: string;
  /** Number of dot cells across frame height (default: 34, range: 8-80) */
  density?: number;
  /** Peak dot radius as % of cell half-spacing (default: 80, range: 10-100) */
  dotSize?: number;
  /** Distance in % frame height where dot size drops to 50% (default: 20, range: 5-100) */
  reach?: number;
  /** Minimum dot radius as % of peak size (default: 10, range: 0-50) */
  minSize?: number;
  /** Cursor influence strength (0 = drift only, 100 = full lock, default: 100) */
  hover?: number;
  /** Idle Lissajous wander speed (0 = static center, default: 32) */
  speed?: number;
  /** Optional custom CSS classes */
  className?: string;
  /** Optional custom inline styles */
  style?: React.CSSProperties;
}

const VERTEX_SHADER_SRC = `
attribute vec2 aPos;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER_SRC = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform vec2  uRes;
uniform float uTime;
uniform vec3  uBg;
uniform vec3  uBase;
uniform vec3  uMid;
uniform vec3  uAccent;
uniform vec2  uFocus;
uniform float uSpacing;
uniform float uPeak;
uniform float uMin;
uniform float uReach;

// Deterministic 2D hash for high-frequency dither (anti-banding)
float h21(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  float aspect = uRes.x / uRes.y;
  vec2 p = vec2(uv.x * aspect, uv.y);
  float px = 1.0 / uRes.y;
  float aa = 1.4 * px;

  vec2 id = floor(p / uSpacing);
  float best = 1e9;
  float bestG = 0.0;

  // 3x3 neighbor cell centers to prevent edge cutoff
  for (int dj = -1; dj <= 1; dj++) {
    for (int di = -1; di <= 1; di++) {
      vec2 c = (id + vec2(float(di), float(dj)) + 0.5) * uSpacing;
      // Inverse-square law sampled strictly at cell center to keep dots circular
      float t = distance(c, uFocus) / max(uReach, 1e-4);
      float g = 1.0 / (1.0 + t * t);
      float rad = uPeak * mix(uMin, 1.0, g);
      float d = distance(p, c) - rad;
      if (d < best) {
        best = d;
        bestG = g;
      }
    }
  }

  // Anti-aliased coverage
  float cov = 1.0 - smoothstep(-aa, aa, best);

  // Three-stop gradient: Base Navy -> Violet Accent -> Intelligence Cyan
  vec3 midCol = mix(uBase, uMid, smoothstep(0.12, 0.55, bestG));
  vec3 dotCol = mix(midCol, uAccent, smoothstep(0.55, 0.95, bestG));
  vec3 col = mix(uBg, dotCol, cov);

  // Anti-banding dither noise
  col += (h21(gl_FragCoord.xy) - 0.5) * (1.5 / 255.0);

  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
`;

function parseColorToVec3(color: string | undefined, fallback: [number, number, number]): [number, number, number] {
  if (!color) return fallback;
  const str = color.trim();
  if (str.startsWith("#")) {
    let hex = str.slice(1);
    if (hex.length === 3 || hex.length === 4) {
      hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    }
    if (hex.length >= 6) {
      const r = parseInt(hex.slice(0, 2), 16) / 255;
      const g = parseInt(hex.slice(2, 4), 16) / 255;
      const b = parseInt(hex.slice(4, 6), 16) / 255;
      if (!isNaN(r) && !isNaN(g) && !isNaN(b)) return [r, g, b];
    }
  }
  const match = str.match(/[\d.]+/g);
  if (match && match.length >= 3) {
    return [
      Math.min(255, parseFloat(match[0])) / 255,
      Math.min(255, parseFloat(match[1])) / 255,
      Math.min(255, parseFloat(match[2])) / 255,
    ];
  }
  return fallback;
}

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

function createShader(gl: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, src);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error("DotLens shader compile error:", gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

export function DotLens({
  background = "#06111F",
  baseColor = "#0A223B",
  midColor = "#647BFF",
  accentColor = "#36C5DE",
  density = 34,
  dotSize = 78,
  reach = 20,
  minSize = 10,
  hover = 100,
  speed = 32,
  className = "",
  style,
}: Readonly<DotLensProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);

  const propsRef = useRef({ background, baseColor, midColor, accentColor, density, dotSize, reach, minSize, hover, speed });

  useEffect(() => {
    propsRef.current = { background, baseColor, midColor, accentColor, density, dotSize, reach, minSize, hover, speed };
  }, [background, baseColor, midColor, accentColor, density, dotSize, reach, minSize, hover, speed]);

  const pointerRef = useRef({
    rawX: 0.5,
    rawY: 0.5,
    on: 0,
    onTarget: 0,
  });

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const gl = canvas.getContext("webgl", {
      antialias: false,
      alpha: false,
      depth: false,
      preserveDrawingBuffer: false,
      powerPreference: "low-power",
    });

    if (!gl) {
      setWebglSupported(false);
      return;
    }

    const vs = createShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER_SRC);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER_SRC);
    if (!vs || !fs) {
      setWebglSupported(false);
      return;
    }

    const program = gl.createProgram();
    if (!program) {
      setWebglSupported(false);
      return;
    }
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("DotLens link error:", gl.getProgramInfoLog(program));
      setWebglSupported(false);
      return;
    }
    gl.useProgram(program);

    // Full screen triangle geometry
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);

    const aPos = gl.getAttribLocation(program, "aPos");
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    const uResLoc = gl.getUniformLocation(program, "uRes");
    const uTimeLoc = gl.getUniformLocation(program, "uTime");
    const uBgLoc = gl.getUniformLocation(program, "uBg");
    const uBaseLoc = gl.getUniformLocation(program, "uBase");
    const uMidLoc = gl.getUniformLocation(program, "uMid");
    const uAccentLoc = gl.getUniformLocation(program, "uAccent");
    const uFocusLoc = gl.getUniformLocation(program, "uFocus");
    const uSpacingLoc = gl.getUniformLocation(program, "uSpacing");
    const uPeakLoc = gl.getUniformLocation(program, "uPeak");
    const uMinLoc = gl.getUniformLocation(program, "uMin");
    const uReachLoc = gl.getUniformLocation(program, "uReach");

    let width = window.innerWidth || container.offsetWidth || 1;
    let height = window.innerHeight || container.offsetHeight || 1;

    const onResize = () => {
      width = window.innerWidth || container.offsetWidth || 1;
      height = window.innerHeight || container.offsetHeight || 1;
    };
    window.addEventListener("resize", onResize, { passive: true });

    const prefersReducedMotion =
      typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let animFrame = 0;
    let lastTime = performance.now();
    let accumulatedTime = 0;
    let isPaused = false;

    const render = (now: number) => {
      if (isPaused) return;
      animFrame = requestAnimationFrame(render);
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const p = propsRef.current;
      const effectiveSpeed = prefersReducedMotion ? 0 : clamp(p.speed, 0, 100) / 50;
      accumulatedTime = (accumulatedTime + dt * effectiveSpeed) % 3600;

      const pointer = pointerRef.current;
      const smoothFactor = 1 - Math.exp(-6.0 * dt);
      pointer.on += (pointer.onTarget - pointer.on) * smoothFactor;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const targetW = Math.max(1, Math.round(width * dpr));
      const targetH = Math.max(1, Math.round(height * dpr));

      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
        gl.viewport(0, 0, targetW, targetH);
      }

      const aspect = targetW / targetH;
      // Autonomous Lissajous drift
      const idleX = aspect * 0.5 + 0.3 * Math.sin(accumulatedTime * 0.31);
      const idleY = 0.5 + 0.24 * Math.sin(accumulatedTime * 0.47 + 1.3);

      const pointerX = pointer.rawX * aspect;
      const pointerY = 1.0 - pointer.rawY; // Invert Y for WebGL coordinates

      const k = (clamp(p.hover, 0, 100) / 100) * Math.min(1, pointer.on);
      const focusX = idleX + (pointerX - idleX) * k;
      const focusY = idleY + (pointerY - idleY) * k;

      const spacing = 1 / Math.round(clamp(p.density, 8, 80));

      gl.uniform2f(uResLoc, targetW, targetH);
      gl.uniform1f(uTimeLoc, accumulatedTime);

      const bg = parseColorToVec3(p.background, [0.0235, 0.0667, 0.1216]);
      const base = parseColorToVec3(p.baseColor, [0.039, 0.133, 0.231]);
      const mid = parseColorToVec3(p.midColor, [0.392, 0.482, 1.0]);
      const accent = parseColorToVec3(p.accentColor, [0.212, 0.773, 0.871]);

      gl.uniform3f(uBgLoc, bg[0], bg[1], bg[2]);
      gl.uniform3f(uBaseLoc, base[0], base[1], base[2]);
      gl.uniform3f(uMidLoc, mid[0], mid[1], mid[2]);
      gl.uniform3f(uAccentLoc, accent[0], accent[1], accent[2]);
      gl.uniform2f(uFocusLoc, focusX, focusY);
      gl.uniform1f(uSpacingLoc, spacing);
      gl.uniform1f(uPeakLoc, (clamp(p.dotSize, 10, 100) / 100) * spacing * 0.5);
      gl.uniform1f(uMinLoc, clamp(p.minSize, 0, 50) / 100);
      gl.uniform1f(uReachLoc, clamp(p.reach, 5, 100) / 100);

      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    // Global viewport pointer listener so the lens reacts smoothly across all cards and surfaces
    const onPointerMove = (e: PointerEvent) => {
      const vw = window.innerWidth || 1;
      const vh = window.innerHeight || 1;
      pointerRef.current.rawX = clamp(e.clientX / vw, 0, 1);
      pointerRef.current.rawY = clamp(e.clientY / vh, 0, 1);
      pointerRef.current.onTarget = 1;
    };

    const onPointerLeave = () => {
      pointerRef.current.onTarget = 0;
    };

    // Pause rendering when tab is hidden to preserve local GPU/CPU resources
    const onVisibilityChange = () => {
      if (document.hidden) {
        isPaused = true;
        if (animFrame) cancelAnimationFrame(animFrame);
        animFrame = 0;
      } else {
        isPaused = false;
        lastTime = performance.now();
        if (!animFrame) animFrame = requestAnimationFrame(render);
      }
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerleave", onPointerLeave, { passive: true });
    window.addEventListener("blur", onPointerLeave, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange, { passive: true });

    animFrame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("blur", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibilityChange);

      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    };
  }, []);

  if (!webglSupported) {
    // Graceful static CSS fallback if WebGL is unavailable
    return (
      <div
        className={className}
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
          backgroundColor: background,
          backgroundImage: "radial-gradient(rgba(54, 197, 222, 0.12) 1.5px, transparent 1.5px)",
          backgroundSize: "28px 28px",
          ...style,
        }}
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
        backgroundColor: background,
        ...style,
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          display: "block",
          pointerEvents: "none",
        }}
      />
    </div>
  );
}

export default DotLens;
