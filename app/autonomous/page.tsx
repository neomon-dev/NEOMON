"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AutonomousResearchWorkspace } from "@/components/autonomous-research-workspace";

function AutonomousContent() {
  const searchParams = useSearchParams();
  const investigationId = searchParams.get("investigation_id") || undefined;

  return (
    <div className="content">
      <AutonomousResearchWorkspace initialInvestigationId={investigationId} />
    </div>
  );
}

export default function AutonomousPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Autonomous Research Engine...</p>
          </div>
        </div>
      }
    >
      <AutonomousContent />
    </Suspense>
  );
}
