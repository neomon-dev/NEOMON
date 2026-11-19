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
        setSelectedId((prev) => prev || (rows.length > 0 ? rows[0].id : ""));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const currentInv = investigations.find((i) => i.id === selectedId);

  return (
    <div className="content compact">
      {/* Sleek inline investigation selector bar */}
      <div
        className="inv-selector-bar"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "8px 16px",
          marginBottom: "12px",
          background: "var(--surface)",
          borderRadius: "8px",
          border: "1px solid var(--border)",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Target Investigation:
        </span>
        <select
          id="inv-selector"
          className="select-input"
          style={{ maxWidth: "520px", flex: 1, fontSize: "12px", padding: "5px 10px" }}
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {investigations.map((inv) => (
            <option key={inv.id} value={inv.id}>
              {inv.question} [{inv.status}]
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "monospace" }}>
          CORPUS::{investigations.length} MISSIONS
        </span>
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
        <div className="content compact">
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
