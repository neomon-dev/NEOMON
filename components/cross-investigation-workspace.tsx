"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { requestJson } from "@/lib/api";
import {
  SpotlightCard,
  AnimatedCounter,
  PulseIndicator,
  BorderBeam,
  RevealSection,
} from "@/components/motion";

export type CrossRelationshipView = {
  id: string;
  source_investigation_id: string;
  source_investigation_question?: string | null;
  target_investigation_id: string;
  target_investigation_question?: string | null;
  relationship_type: string;
  explanation: string;
  confidence: string;
  detection_method: string;
  claim_ids: string[];
  evidence_ids: string[];
  shared_evidence_count: number;
  created_at?: string | null;
};

export type InvestigationSynthesisReportView = {
  id: string;
  title: string;
  summary: string;
  investigation_ids: string[];
  shared_themes: { theme: string; investigation_1?: string; investigation_2?: string }[];
  common_findings: { concept: string; investigation_1_claim: string; investigation_2_claim: string; synthesis_summary: string }[];
  complementary_findings: { concept: string; investigation_1_claim: string; investigation_2_claim: string; synthesis_summary: string }[];
  conflicting_findings: { concept: string; investigation_1_claim: string; investigation_2_claim: string; tension_summary: string }[];
  shared_evidence: { identifier: string; title: string; investigations: { id: string; question: string }[] }[];
  independent_corroboration: { concept: string; finding: string; confidence: string }[];
  methodological_differences: { investigation_1: string; investigation_2: string; summary: string }[];
  unresolved_questions: string[];
  cross_investigation_gaps: string[];
  recommended_future_investigations: string[];
  created_at?: string | null;
};

export type GlobalClaimSearchResult = {
  claim_id: string;
  investigation_id: string;
  investigation_question: string;
  claim_text: string;
  status: string;
  priority: number;
  evidence_count: number;
};

export type SharedEvidenceResult = {
  evidence_id: string;
  exact_text: string;
  source_id: string;
  source_title: string;
  investigation_ids: string[];
  investigation_questions: string[];
  is_syndicated: boolean;
};

type InvestigationOption = {
  id: string;
  question: string;
  status: string;
};

const REL_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  supports: { bg: "rgba(16, 185, 129, 0.12)", text: "#10b981", border: "#10b981" },
  challenges: { bg: "rgba(239, 68, 68, 0.12)", text: "#ef4444", border: "#ef4444" },
  extends: { bg: "rgba(59, 130, 246, 0.12)", text: "#3b82f6", border: "#3b82f6" },
  shares_evidence_with: { bg: "rgba(168, 85, 247, 0.12)", text: "#a855f7", border: "#a855f7" },
  diverges_methodologically: { bg: "rgba(245, 158, 11, 0.12)", text: "#f59e0b", border: "#f59e0b" },
};

export function CrossInvestigationWorkspace() {
  const [tab, setTab] = useState<"synthesis" | "relationships" | "claims" | "shared_evidence">("synthesis");
  const [investigations, setInvestigations] = useState<InvestigationOption[]>([]);
  const [selectedInvIds, setSelectedInvIds] = useState<string[]>([]);
  const [reports, setReports] = useState<InvestigationSynthesisReportView[]>([]);
  const [activeReport, setActiveReport] = useState<InvestigationSynthesisReportView | null>(null);
  const [relationships, setRelationships] = useState<CrossRelationshipView[]>([]);
  const [globalClaims, setGlobalClaims] = useState<GlobalClaimSearchResult[]>([]);
  const [sharedEvidence, setSharedEvidence] = useState<SharedEvidenceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [synthesizing, setSynthesizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Claim Search Filter
  const [claimSearchQuery, setClaimSearchQuery] = useState("");
  const [relTypeFilter, setRelTypeFilter] = useState("all");

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      const [invs, reps, rels, shared] = await Promise.all([
        requestJson<InvestigationOption[]>("/research/investigations"),
        requestJson<InvestigationSynthesisReportView[]>("/research/synthesis/reports"),
        requestJson<CrossRelationshipView[]>("/research/synthesis/relationships"),
        requestJson<SharedEvidenceResult[]>("/research/synthesis/shared-evidence"),
      ]);
      setInvestigations(invs || []);
      setReports(reps || []);
      if (reps && reps.length > 0) {
        setActiveReport(reps[0]);
      }
      setRelationships(rels || []);
      setSharedEvidence(shared || []);

      if (invs && invs.length >= 2) {
        setSelectedInvIds((prev) => (prev.length === 0 ? [invs[0].id, invs[1].id] : prev));
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load synthesis workspace data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleSynthesize = async () => {
    if (selectedInvIds.length < 2) {
      setError("Please select at least 2 investigations to synthesize.");
      return;
    }
    setSynthesizing(true);
    setError(null);
    try {
      const resp = await requestJson<{
        report: InvestigationSynthesisReportView;
        relationships: CrossRelationshipView[];
      }>("/research/synthesis/generate", {
        method: "POST",
        body: JSON.stringify({ investigation_ids: selectedInvIds }),
      });
      setActiveReport(resp.report);
      setReports((prev) => [resp.report, ...prev]);
      setRelationships((prev) => [...resp.relationships, ...prev]);
      setTab("synthesis");
    } catch (err: any) {
      setError(err?.message || "Failed to generate cross-investigation synthesis.");
    } finally {
      setSynthesizing(false);
    }
  };

  const handleSearchClaims = async () => {
    try {
      const results = await requestJson<GlobalClaimSearchResult[]>(
        `/research/synthesis/claims/search?query=${encodeURIComponent(claimSearchQuery)}`
      );
      setGlobalClaims(results || []);
    } catch (err: any) {
      setError(err?.message || "Failed to search global claims.");
    }
  };

  const filteredRelationships = useMemo(() => {
    if (relTypeFilter === "all") return relationships;
    return relationships.filter((r) => r.relationship_type.toLowerCase() === relTypeFilter.toLowerCase());
  }, [relationships, relTypeFilter]);

  const toggleSelectInv = (id: string) => {
    setSelectedInvIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="cross-investigation-workspace" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Compact Unified Header & Action Bar */}
      <div className="panel compact" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "14px", marginBottom: "14px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, color: "#f8fafc" }}>Cross-Investigation Synthesis</h1>
              <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", borderRadius: "10px", background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "1px solid rgba(56, 189, 248, 0.3)" }}>
                CROSS-STUDY CONVERGENCE
              </span>
            </div>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: "13px" }}>
              Synthesize evidence, detect convergent and contradictory claims, and discover shared citations across studies.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "12px", color: selectedInvIds.length >= 2 ? "#38bdf8" : "var(--muted)", fontWeight: 600 }}>
              {selectedInvIds.length} of {investigations.length} selected
            </span>
            <button
              className="cyber-primary-btn"
              disabled={synthesizing || selectedInvIds.length < 2}
              onClick={handleSynthesize}
              style={{ padding: "8px 18px", fontSize: "12px" }}
            >
              {synthesizing ? "Synthesizing Knowledge..." : `Synthesize Selected (${selectedInvIds.length})`}
            </button>
          </div>
        </div>

        {/* Investigation Multi-Selector Card Row */}
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)" }}>
              Select Studies to Compare (Minimum 2 required)
            </span>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setSelectedInvIds(investigations.map((i) => i.id))}
                style={{ background: "none", border: "none", color: "#38bdf8", fontSize: "11px", fontWeight: 600, cursor: "pointer", padding: "2px 6px" }}
              >
                Select All
              </button>
              <span style={{ color: "var(--border)", fontSize: "11px" }}>|</span>
              <button
                type="button"
                onClick={() => setSelectedInvIds([])}
                style={{ background: "none", border: "none", color: "var(--muted)", fontSize: "11px", fontWeight: 600, cursor: "pointer", padding: "2px 6px" }}
              >
                Clear
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "8px", maxHeight: "180px", overflowY: "auto", paddingRight: "4px" }}>
            {investigations.map((inv) => {
              const isSelected = selectedInvIds.includes(inv.id);
              return (
                <div
                  key={inv.id}
                  onClick={() => toggleSelectInv(inv.id)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: isSelected ? "1px solid #25D9F2" : "1px solid rgba(255, 255, 255, 0.08)",
                    background: isSelected ? "rgba(37, 217, 242, 0.1)" : "rgba(12, 25, 43, 0.5)",
                    boxShadow: isSelected ? "0 0 16px -2px rgba(37, 217, 242, 0.35)" : "none",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    position: "relative",
                    overflow: "hidden",
                    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                  }}
                >
                  {isSelected && <BorderBeam size={100} duration={6} colorFrom="#25D9F2" colorTo="#2787FF" />}
                  <div
                    style={{
                      width: "16px",
                      height: "16px",
                      borderRadius: "4px",
                      border: isSelected ? "1px solid #38bdf8" : "1px solid var(--muted)",
                      background: isSelected ? "#38bdf8" : "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#000",
                      fontSize: "10px",
                      fontWeight: 800,
                      flexShrink: 0,
                    }}
                  >
                    {isSelected ? "✓" : ""}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "12px", fontWeight: 600, color: isSelected ? "#f8fafc" : "#cbd5e1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {inv.question}
                    </div>
                    <div className="muted" style={{ fontSize: "10px", marginTop: "1px" }}>Status: {inv.status}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {error && (
        <div className="panel error-banner" style={{ padding: "10px 16px", color: "#f43f5e", fontSize: "13px" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="tab-nav" style={{ padding: "0 4px" }}>
        <button
          className={`tab-btn ${tab === "synthesis" ? "active" : ""}`}
          onClick={() => setTab("synthesis")}
        >
          Synthesis Reports ({reports.length})
        </button>
        <button
          className={`tab-btn ${tab === "relationships" ? "active" : ""}`}
          onClick={() => setTab("relationships")}
        >
          Cross-Study Relationships ({relationships.length})
        </button>
        <button
          className={`tab-btn ${tab === "claims" ? "active" : ""}`}
          onClick={() => {
            setTab("claims");
            if (globalClaims.length === 0) handleSearchClaims();
          }}
        >
          Global Claim Search
        </button>
        <button
          className={`tab-btn ${tab === "shared_evidence" ? "active" : ""}`}
          onClick={() => setTab("shared_evidence")}
        >
          Shared Evidence & Citations ({sharedEvidence.length})
        </button>
      </div>

      {/* Tab 1: Synthesis Reports */}
      {tab === "synthesis" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {reports.length > 1 && (
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "var(--muted)" }}>Select Synthesis Run:</span>
              <select
                className="select-input"
                value={activeReport?.id || ""}
                onChange={(e) => setActiveReport(reports.find((r) => r.id === e.target.value) || null)}
                style={{ fontSize: "13px" }}
              >
                {reports.map((r, i) => (
                  <option key={r.id} value={r.id}>
                    {r.title} ({new Date(r.created_at || "").toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>
          )}

          {activeReport ? (
            <div className="panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
              <div>
                <h3 style={{ fontSize: "1.3rem", fontWeight: 700, margin: "0 0 8px" }}>{activeReport.title}</h3>
                <div style={{ fontSize: "13.5px", lineHeight: 1.6, color: "#e2e8f0" }}>{activeReport.summary}</div>
              </div>

              {/* 1. Common Convergent Findings */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#10b981", textTransform: "uppercase", margin: 0 }}>
                  1. Common Convergent Findings ({activeReport.common_findings.length})
                </h4>
                {activeReport.common_findings.length === 0 ? (
                  <p className="muted" style={{ fontSize: "13px" }}>No direct convergent findings identified between these cohorts.</p>
                ) : (
                  activeReport.common_findings.map((cf, idx) => (
                    <div key={idx} style={{ padding: "12px 16px", background: "rgba(16, 185, 129, 0.05)", borderLeft: "3px solid #10b981", borderRadius: "4px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#6ee7b7" }}>Concept: {cf.concept}</div>
                      <div style={{ fontSize: "12.5px", marginTop: "4px" }}>{cf.synthesis_summary}</div>
                    </div>
                  ))
                )}
              </div>

              {/* 2. Divergent & Conflicting Claims */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", margin: 0 }}>
                  2. Divergent / Conflicting Claims ({activeReport.conflicting_findings.length})
                </h4>
                {activeReport.conflicting_findings.length === 0 ? (
                  <p className="muted" style={{ fontSize: "13px" }}>No contradictory directional tensions detected.</p>
                ) : (
                  activeReport.conflicting_findings.map((df, idx) => (
                    <div key={idx} style={{ padding: "12px 16px", background: "rgba(239, 68, 68, 0.05)", borderLeft: "3px solid #ef4444", borderRadius: "4px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#fca5a5" }}>Tension on Concept: {df.concept}</div>
                      <div style={{ fontSize: "12.5px", marginTop: "4px" }}>{df.tension_summary}</div>
                      <div style={{ fontSize: "12px", marginTop: "6px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                        <div style={{ background: "rgba(0,0,0,0.2)", padding: "6px 10px", borderRadius: "4px" }}>
                          <strong>Study 1 Claim:</strong> {df.investigation_1_claim}
                        </div>
                        <div style={{ background: "rgba(0,0,0,0.2)", padding: "6px 10px", borderRadius: "4px" }}>
                          <strong>Study 2 Claim:</strong> {df.investigation_2_claim}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* 3. Shared Evidence & Citations */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#a855f7", textTransform: "uppercase", margin: 0 }}>
                  3. Shared Literature & Citations ({activeReport.shared_evidence.length})
                </h4>
                {activeReport.shared_evidence.length === 0 ? (
                  <p className="muted" style={{ fontSize: "13px" }}>No shared primary literature references or DOIs found across investigations.</p>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "10px" }}>
                    {activeReport.shared_evidence.map((se, idx) => (
                      <div key={idx} style={{ padding: "10px 14px", background: "rgba(168, 85, 247, 0.05)", border: "1px solid rgba(168, 85, 247, 0.2)", borderRadius: "6px" }}>
                        <div style={{ fontSize: "11px", color: "#c084fc", fontWeight: 700 }}>{se.identifier}</div>
                        <div style={{ fontSize: "13px", fontWeight: 600, marginTop: "2px" }}>{se.title}</div>
                        <div className="muted" style={{ fontSize: "11px", marginTop: "4px" }}>
                          Referenced in {se.investigations?.length || 2} studies
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 4. Methodological Differences */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase", margin: 0 }}>
                  4. Methodological Divergences & Scope Variations
                </h4>
                {activeReport.methodological_differences.map((md, idx) => (
                  <div key={idx} style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "6px", fontSize: "12.5px" }}>
                    {md.summary}
                  </div>
                ))}
              </div>

              {/* 5. Recommendations for Future Research */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#06b6d4", textTransform: "uppercase", margin: 0 }}>
                  5. Actionable Next Steps & Unified Inquiry Recommendations
                </h4>
                <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", lineHeight: 1.6 }}>
                  {activeReport.recommended_future_investigations.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: "6px" }}>{rec}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="panel empty-state">
              <p className="muted">No synthesis report available. Select 2 investigations and click Synthesize.</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Relationships */}
      {tab === "relationships" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="panel" style={{ padding: "12px 18px", display: "flex", alignItems: "center", gap: "12px" }}>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Filter by Relationship Type:</label>
            <select
              className="select-input"
              value={relTypeFilter}
              onChange={(e) => setRelTypeFilter(e.target.value)}
              style={{ fontSize: "13px" }}
            >
              <option value="all">All Types</option>
              <option value="supports">Supports</option>
              <option value="challenges">Challenges</option>
              <option value="extends">Extends</option>
              <option value="shares_evidence_with">Shares Evidence With</option>
              <option value="diverges_methodologically">Diverges Methodologically</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {filteredRelationships.map((r) => {
              const style = REL_COLORS[r.relationship_type.toLowerCase()] || { bg: "rgba(255,255,255,0.05)", text: "#cbd5e1", border: "#475569" };
              return (
                <div
                  key={r.id}
                  className="panel"
                  style={{
                    padding: "16px 20px",
                    borderLeft: `4px solid ${style.border}`,
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        backgroundColor: style.bg,
                        color: style.text,
                      }}
                    >
                      {r.relationship_type}
                    </span>
                    <span className="muted" style={{ fontSize: "11px" }}>
                      Confidence: <strong>{r.confidence}</strong> | Method: {r.detection_method}
                    </span>
                  </div>

                  <div style={{ fontSize: "13px", lineHeight: 1.5 }}>{r.explanation}</div>

                  {(r.source_investigation_question || r.target_investigation_question) && (
                    <div style={{ fontSize: "12px", display: "flex", gap: "16px", marginTop: "4px", color: "var(--muted)" }}>
                      <div><strong>Source:</strong> {r.source_investigation_question || r.source_investigation_id}</div>
                      <div><strong>Target:</strong> {r.target_investigation_question || r.target_investigation_id}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 3: Global Claims Search */}
      {tab === "claims" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="panel" style={{ padding: "14px 20px", display: "flex", gap: "10px" }}>
            <input
              type="text"
              className="text-input"
              placeholder="Search claims across all investigations (e.g. 'productivity', 'hallucinations', 'latency')..."
              value={claimSearchQuery}
              onChange={(e) => setClaimSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearchClaims()}
              style={{ flex: 1, padding: "8px 12px", fontSize: "13px" }}
            />
            <button className="button primary" onClick={handleSearchClaims}>
              Search Claims
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {globalClaims.map((claim) => (
              <div key={claim.claim_id} className="panel" style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px" }}>
                    Investigation: <strong>{claim.investigation_question}</strong>
                  </span>
                  <span style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "4px", background: "rgba(255,255,255,0.05)" }}>
                    Priority: {claim.priority} | Evidence Items: {claim.evidence_count}
                  </span>
                </div>
                <div style={{ fontSize: "13.5px", fontWeight: 600 }}>{claim.claim_text}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Shared Evidence */}
      {tab === "shared_evidence" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="panel" style={{ padding: "14px 20px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 6px" }}>
              Cross-Study Syndicated Evidence & Sources
            </h3>
            <p className="muted" style={{ margin: 0, fontSize: "13px" }}>
              Literature, DOIs, and evidence passages independently retrieved across multiple distinct investigations.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {sharedEvidence.length === 0 ? (
              <div className="panel empty-state">
                <p className="muted">No syndicated evidence found across 2+ investigations yet.</p>
              </div>
            ) : (
              sharedEvidence.map((se) => (
                <div key={se.evidence_id} className="panel" style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#a855f7" }}>
                      Source: {se.source_title}
                    </span>
                    <span style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "10px", background: "rgba(168,85,247,0.15)", color: "#c084fc" }}>
                      Syndicated Across {se.investigation_ids.length} Studies
                    </span>
                  </div>
                  <div style={{ fontSize: "13px", fontStyle: "italic", padding: "8px 12px", background: "rgba(0,0,0,0.2)", borderRadius: "4px" }}>
                    "{se.exact_text}"
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--muted)" }}>
                    <strong>Referenced In:</strong> {se.investigation_questions.join(" • ")}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
