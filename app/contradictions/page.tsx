"use client";

import { Suspense } from "react";
import { ContradictionWorkspace } from "@/components/contradiction-workspace";

export default function ContradictionsPage() {
  return (
    <Suspense
      fallback={
        <div className="content compact">
          <div className="panel empty-state">
            <p className="muted">Loading Contradiction Intelligence Workspace...</p>
          </div>
        </div>
      }
    >
      <div className="content compact">
        <ContradictionWorkspace />
      </div>
    </Suspense>
  );
}
