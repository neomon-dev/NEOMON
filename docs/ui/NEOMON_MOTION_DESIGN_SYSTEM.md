# NEOMON — Motion Design System & Animation Architecture
## Comprehensive Motion Tokens, Reusable Primitives & Route Interaction Guidelines

**Project**: NEOMON — Neural Evidence Orchestration & Multi-Agent Observation Network  
**Target Repository**: `C:\Users\mohid\OneDrive\Desktop\NEOMON`  
**Frontend Engine**: `motion/react` + Next.js 16 + React 19  
**Specification Date**: November 19, 2026  
**Status**: ACTIVE PRODUCTION SPECIFICATION  

---

## 1. System Philosophy: Purposeful Scientific Motion

In NEOMON, motion is never merely ornamental. It serves three non-negotiable operational functions:

1. **Cognitive Orienting**: Guiding the researcher's focus directly to high-entropy information—such as newly discovered research gaps, emergent contradictions between clinical trials, and multi-agent consensus shifts.
2. **State & Causality Communication**: Visualizing the state transition of computational pipelines (e.g., query expansion → literature ingestion → passage extraction → dialectical synthesis) so the researcher clearly understands where evidence originates.
3. **Cyberpunk Scientific Immersion**: Creating a cohesive, unforgettable command center aesthetic characterized by precision technical grids, telemetry beacons, cursor-tracked spotlights, and traveling border beams.

---

## 2. Shared Motion Tokens & CSS Architecture

Added directly into `app/globals.css`:

```css
:root {
  /* Motion Duration Tokens */
  --motion-instant: 100ms;
  --motion-fast: 180ms;
  --motion-normal: 260ms;
  --motion-slow: 420ms;
  --motion-atmospheric: 4000ms;

  /* Motion Easing Curves */
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-smooth: cubic-bezier(0.25, 1, 0.5, 1);
  --ease-sharp: cubic-bezier(0.4, 0, 0.2, 1);

  /* Elevation Shadows & Scientific Glows */
  --glow-cyan-subtle: 0 0 16px -2px rgba(37, 217, 242, 0.25);
  --glow-cyan-strong: 0 0 28px rgba(37, 217, 242, 0.5);
  --glow-blue-subtle: 0 0 16px -2px rgba(39, 135, 255, 0.25);
  --glow-violet-subtle: 0 0 16px -2px rgba(133, 100, 255, 0.25);
  --glow-mint-subtle: 0 0 16px -2px rgba(53, 224, 177, 0.25);
  --glow-amber-subtle: 0 0 16px -2px rgba(255, 181, 71, 0.25);
  --glow-red-subtle: 0 0 16px -2px rgba(255, 82, 119, 0.25);
}
```

---

## 3. Reusable Motion Primitives (`components/motion/`)

The motion architecture standardizes 10 reusable scientific UI primitives:

### 3.1. `SpotlightCard`
- **Purpose**: High-tech surface that computes mouse coordinates relative to its bounding rect, rendering a smooth radial specular highlight over an elevated obsidian card with a crisp border accent.
- **Props**: `children`, `className`, `spotlightColor` (defaults to `rgba(37, 217, 242, 0.12)`), `onClick`.

### 3.2. `BorderBeam`
- **Purpose**: Pure SVG stroke-dashoffset traveling beam along a card's border radius, inspired by Magic UI. Communicates active agent execution, high-priority hypotheses, or live ingestion.
- **Props**: `size` (px), `duration` (s), `colorFrom`, `colorTo`, `borderWidth`.

### 3.3. `AnimatedCounter`
- **Purpose**: Hardware-accelerated numerical counter using spring physics. Animates from `0` to the target value when mounted or when application state changes.
- **Props**: `value` (number), `formatter` (optional function for decimals or units), `duration`.

### 3.4. `TerminalText` / `DecryptedText`
- **Purpose**: Cyberpunk character cipher decoding effect. Cycles through pseudorandom characters (`01`, `§#⌘%*⚡`) before snapping to the definitive text string.
- **Props**: `text`, `speed`, `maxIterations`, `revealDirection`.

### 3.5. `MagneticButton`
- **Purpose**: Interactive primary action button that dynamically displaces toward the user's cursor within a 40px bounding radius using spring dampening, giving critical triggers (e.g. `+ Launch Investigation`) an irresistible physical responsiveness.
- **Props**: `children`, `className`, `strength`, `onClick`.

### 3.6. `RevealSection`
- **Purpose**: Viewport-aware staggered entrance animation with opacity fade and upward translation (`y: 16 -> 0`).
- **Props**: `delay`, `children`, `className`.

### 3.7. `PulseIndicator`
- **Purpose**: Multi-ring telemetry beacon indicating real-time system states (`ACTIVE`, `SYNTHESIZING`, `VERIFIED`, `CONTRADICTION`).
- **Props**: `status` ("active" | "warning" | "error" | "mint"), `label`.

### 3.8. `RadarScanning`
- **Purpose**: Circular or linear radar sweeping grid for the New Investigation mission launchpad and Autonomous Research suite.
- **Props**: `size`, `color`, `speed`.

### 3.9. `DataStream`
- **Purpose**: Subtle vertical or horizontal telemetry stream of hexadecimal and scientific coordinates drifting across the background without distracting from foreground content.

### 3.10. `EvidenceFlow`
- **Purpose**: Visual pathway connecting research claims to supporting citations and opposing dialectical extracts.

---

## 4. Route-Specific Visual Identities

Each major route in NEOMON receives a distinct visual identity tailored to its domain:

| Route | Visual Identity Concept | Key Signature Motion Elements |
| :--- | :--- | :--- |
| **`/` (Dashboard)** | AI Research Command Center | Neural Particle Canvas, Staggered Animated Metrics, Live Agent Telemetry, Spotlight Cards, Decrypted Beacons |
| **`/investigations/new`** | Mission Launch Terminal | Technical Coordinate Grid, Mode Selection Cards with Traveling Border Beams, Magnetic Launch Trigger |
| **`/autonomous`** | Autonomous Agent Orchestration | Multi-Stage Connected Pipeline, Active Pulse Indicator, Real Query Expansion Tracker, Stream Activity Feed |
| **`/graph`** | Interactive Knowledge Network | React Flow Animated Edges, Glowing Node Rings, Directional Evidence Flow, Minimized Minimap Pulse |
| **`/evidence`** | Dialectical Evidence Explorer | Support/Contradiction/Context badges with chromatic tags, Expandable Passage Drawer with Spring Transition |
| **`/sources`** | Source Ingestion Pipeline | Ingestion Status Tracker (Queued → Ingested → Extracted), Credibility Calibration Bars |
| **`/gaps`** | Evidence Horizon & Gap Discovery | Radial Evidence Coverage Gauge, Animated Gap Severity Bars, Claim Coverage Matrix |
| **`/hypotheses`** | Scientific Hypothesis Laboratory | Scientific Grid, Hypothesis Lifecycle Pipeline, Testability Rating Bars |
| **`/synthesis`** | Dialectical Synthesis Workspace | Split Convergence/Divergence comparison cards, Inter-study Synthesis Links |
| **`/contradictions`** | Dialectical Contradiction Inspector | Opposing Evidence Scales, High-Contrast Red/Cyan Conflict Visualizer, Severity Meters |
| **`/trends`** | Scientific Trend Intelligence | Animated SVG Time-Series Horizon, Topic Drift Coordinates, Interactive Tooltips |
| **`/quality-audit`** | Methodology & Quality Inspection | Quality Tier Gauge, Dimensional Calibration Radar, Reproducibility Scorecards |
| **`/agents`** | Multi-Agent Laboratory | 17 Distinct Agent Identity Cards, Activity Rings, Execution Duration Gauges |
| **`/benchmarks`** | Scientific Benchmark Suite | Benchmark Execution Stages, Pass/Fail Threshold Indicators, Comparative Delta Bars |
| **`/workspaces`** | Multi-Tenant Collaboration Hub | Role Badges with Metallic Sheens, Activity Stream Entrance, Threaded Review Indicators |

---

## 5. Performance and Resource Bounds

1. **Frame Budget**: All continuous animations (Canvas particle simulations, SVG border beams) run at a steady 60fps on modern hardware and consume <3% CPU utilization when idle.
2. **Offscreen Optimization**: All canvas loops and CSS animations use `IntersectionObserver` or CSS `contain: paint` to suspend execution when scrolled out of view.
3. **Tab Inactivity**: `document.addEventListener("visibilitychange")` halts animation ticks immediately when the user switches tabs.
4. **Bundle Footprint**: The entire motion runtime (`motion/react`) adds <35KB minified/gzipped to the bundle and is tree-shaken across routes.
