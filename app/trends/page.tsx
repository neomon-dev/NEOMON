"use client";

import { Suspense } from "react";
import { ResearchTrendsWorkspace } from "@/components/research-trends-workspace";

export default function TrendsPage() {
  return (
    <Suspense
      fallback={
        <div className="content compact">
          <div className="panel empty-state">
            <p className="muted">Loading Research Trend Intelligence Workspace...</p>
          </div>
        </div>
      }
    >
      <div className="content compact">
        <ResearchTrendsWorkspace />
      </div>
    </Suspense>
  );
}
