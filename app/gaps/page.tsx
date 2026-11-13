"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { requestJson } from "@/lib/api";
import { ResearchGapWorkspace } from "@/components/research-gap-workspace";

type InvestigationOption = {
  id: string;
  question: string;
  status: string;
  created_at?: string;
};

function GapsContent() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get("investigation_id") || "";

  const [investigations, setInvestigations] = useState<InvestigationOption[]>([]);
  const [selectedId, setSelectedId] = useState<string>(initialId);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    requestJson<InvestigationOption[]>("/research/investigations")
      .then((rows) => {
        setInvestigations(rows);
        if (!selectedId && rows.length > 0) {
          setSelectedId(rows[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const currentInv = investigations.find((i) => i.id === selectedId);

  return (
    <div className="content">
      <div className="investigation-select-bar panel" style={{ marginBottom: "16px", padding: "12px 18px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", width: "100%" }}>
          <label htmlFor="inv-selector" style={{ fontWeight: 600, fontSize: "13px", whiteSpace: "nowrap" }}>
            Select Investigation:
          </label>
          <select
            id="inv-selector"
            className="select-input"
            style={{ maxWidth: "600px", flex: 1 }}
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            {investigations.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.question} ({inv.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedId ? (
        <ResearchGapWorkspace
          investigationId={selectedId}
          investigationQuestion={currentInv?.question}
        />
      ) : loading ? (
        <div className="panel empty-state">
          <p className="muted">Loading investigations...</p>
        </div>
      ) : (
        <div className="panel empty-state">
          <p className="muted">No investigations found. Create an investigation first to analyze research gaps.</p>
        </div>
      )}
    </div>
  );
}

export default function GapsPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Research Gap Workspace...</p>
          </div>
        </div>
      }
    >
      <GapsContent />
    </Suspense>
  );
}
