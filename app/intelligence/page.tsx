"use client";

import { Suspense } from "react";
import { UnifiedIntelligenceWorkspace } from "@/components/unified-intelligence-workspace";

export default function IntelligencePage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Unified Research Intelligence Hub...</p>
          </div>
        </div>
      }
    >
      <div className="content">
        <UnifiedIntelligenceWorkspace />
      </div>
    </Suspense>
  );
}
