"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { QualityAuditWorkspace } from "@/components/quality-audit-workspace";

function QualityAuditContent() {
  const searchParams = useSearchParams();
  const investigationId = searchParams.get("investigation_id") || undefined;

  return (
    <div className="content">
      <QualityAuditWorkspace initialInvestigationId={investigationId} />
    </div>
  );
}

export default function QualityAuditPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Scientific Quality Audit...</p>
          </div>
        </div>
      }
    >
      <QualityAuditContent />
    </Suspense>
  );
}
