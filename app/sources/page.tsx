import { Suspense } from "react";
import { SourceIntelligence } from "@/components/source-intelligence";

export default function SourcesPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Source Intelligence...</p>
          </div>
        </div>
      }
    >
      <SourceIntelligence />
    </Suspense>
  );
}
