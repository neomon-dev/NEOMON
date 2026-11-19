"use client";

import { Suspense } from "react";
import { CrossInvestigationWorkspace } from "@/components/cross-investigation-workspace";

export default function SynthesisPage() {
  return (
    <Suspense
      fallback={
        <div className="content compact">
          <div className="panel empty-state">
            <p className="muted">Loading Cross-Investigation Synthesis Workspace...</p>
          </div>
        </div>
      }
    >
      <div className="content compact">
        <CrossInvestigationWorkspace />
      </div>
    </Suspense>
  );
}
