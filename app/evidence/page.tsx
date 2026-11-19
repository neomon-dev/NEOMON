import { Suspense } from "react";
import { EvidenceExplorer } from "@/components/evidence-explorer";

export default function EvidencePage() {
  return (
    <Suspense
      fallback={
        <div className="content compact">
          <div className="panel empty-state">
            <p className="muted">Loading Evidence Explorer...</p>
          </div>
        </div>
      }
    >
      <div className="content compact">
        <EvidenceExplorer />
      </div>
    </Suspense>
  );
}
