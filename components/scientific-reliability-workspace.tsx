"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { requestJson } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface ClaimSynthesis {
  id: string;
  claim_id: string;
  claim_text: string;
  synthesis_outcome: string;
  unique_underlying_studies_count: number;
  direct_supporting_count: number;
  partial_supporting_count: number;
  contradicting_count: number;
  contextual_count: number;
  evidence_strength_score: number;
  synthesis_rationale?: string;
  methodological_limitations?: string[];
  replication_status?: string;
}

interface EvidenceVerification {
  id: string;
  claim_id: string;
  evidence_id: string;
  source_id: string;
  exact_passage_text: string;
  relationship_classification: string;
  verification_status: string;
  confidence: number;
  meaning_representation?: string;
  explanation?: string;
  is_challenged: boolean;
  challenge_reason?: string;
}

interface StudyCluster {
  id: string;
  cluster_label: string;
  member_source_ids: string[];
  relationship_category: string;
  confidence: number;
  primary_doi?: string;
  shared_authors: string[];
  evidence_rationale: string;
}

interface MethodologyFinding {
  id: string;
  audit_dimension: string;
  issue_severity: string;
  finding_title: string;
  description: string;
  missing_data_condition?: string;
  suggested_action?: string;
}

interface ExecutionManifest {
  id: string;
  investigation_id: string;
  manifest_hash: string;
  research_question: string;
  timestamp: string;
  search_queries_count: number;
  sources_count: number;
  evidence_count: number;
  calibrated_quality_tier: string;
  calibrated_quality_score: number;
  search_manifest: Array<{ query: string; provider?: string; executed_at?: string; results_count?: number }>;
  execution_timeline: Array<{ agent_role: string; status: string; model_identifier?: string; started_at?: string; completed_at?: string }>;
  configuration_snapshot: Record<string, unknown>;
}

export function ScientificReliabilityWorkspace({ investigationId }: { investigationId: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"claims" | "independence" | "methodology" | "reproducibility">("claims");

  // State
  const [syntheses, setSyntheses] = useState<ClaimSynthesis[]>([]);
  const [verifications, setVerifications] = useState<EvidenceVerification[]>([]);
  const [clusters, setClusters] = useState<StudyCluster[]>([]);
  const [findings, setFindings] = useState<MethodologyFinding[]>([]);
  const [manifest, setManifest] = useState<ExecutionManifest | null>(null);
  const [tamperStatus, setTamperStatus] = useState<{ is_tamper_free?: boolean; status?: string } | null>(null);

  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Reviewer Correction Modal / Form State
  const [selectedRecord, setSelectedRecord] = useState<EvidenceVerification | null>(null);
  const [challengeClassification, setChallengeClassification] = useState<string>("contextual_background");
  const [challengeReason, setChallengeReason] = useState<string>("");

  const loadAllData = useCallback(async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      const [synthData, verifData, clustData, findData, manData] = await Promise.all([
        requestJson<ClaimSynthesis[]>(`/research/investigations/${investigationId}/claim-synthesis`).catch(() => []),
        requestJson<EvidenceVerification[]>(`/research/investigations/${investigationId}/verification`).catch(() => []),
        requestJson<StudyCluster[]>(`/research/investigations/${investigationId}/study-independence`).catch(() => []),
        requestJson<MethodologyFinding[]>(`/research/investigations/${investigationId}/methodology-audit`).catch(() => []),
        requestJson<ExecutionManifest>(`/research/investigations/${investigationId}/reproducibility/manifest`).catch(() => null),
      ]);

      setSyntheses(Array.isArray(synthData) ? synthData : []);
      setVerifications(Array.isArray(verifData) ? verifData : []);
      setClusters(Array.isArray(clustData) ? clustData : []);
      setFindings(Array.isArray(findData) ? findData : []);
      setManifest(manData && manData.manifest_hash ? manData : null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load reliability data");
    } finally {
      setLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Actions
  const runVerificationAndSynthesis = async () => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await requestJson(`/research/investigations/${investigationId}/verification/verify`, { method: "POST" });
      await requestJson(`/research/investigations/${investigationId}/study-independence/analyze`, { method: "POST" });
      await requestJson(`/research/investigations/${investigationId}/claim-synthesis/run`, { method: "POST" });
      await requestJson(`/research/investigations/${investigationId}/methodology-audit/run`, { method: "POST" });
      await requestJson(`/research/investigations/${investigationId}/reproducibility/manifest`, { method: "POST" });
      setSuccessMsg("Scientific verification, study clustering, and synthesis successfully executed.");
      await loadAllData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis run failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyManifest = async () => {
    setActionLoading(true);
    try {
      const res = await requestJson<{ is_tamper_free: boolean; status: string }>(
        `/research/investigations/${investigationId}/reproducibility/manifest/verify`
      );
      setTamperStatus(res);
      setSuccessMsg(res.is_tamper_free ? "Cryptographic manifest verified: 100% tamper-free." : "Tamper warning: hash mismatch!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification check failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReproduceRun = async () => {
    if (!confirm("Spawn an independent reproduction run of this investigation?")) return;
    setActionLoading(true);
    try {
      const res = await requestJson<{ message: string; reproduction_investigation_id: string }>(
        `/research/investigations/${investigationId}/reproducibility/reproduce`,
        { method: "POST" }
      );
      setSuccessMsg(`Reproduction spawned: ${res.reproduction_investigation_id}. Redirecting...`);
      router.push(`/investigations/${res.reproduction_investigation_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reproduction failed");
    } finally {
      setActionLoading(false);
    }
  };

  const submitReviewerChallenge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/investigations/${investigationId}/verification/${selectedRecord.id}/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          corrected_classification: challengeClassification,
          reason: challengeReason,
        }),
      });

      // Submit formal correction record
      await requestJson(`/research/investigations/${investigationId}/corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: selectedRecord.claim_id,
          evidence_id: selectedRecord.evidence_id,
          correction_type: challengeClassification === "contextual_background" ? "mark_contextual" : "overrule_entailment",
          corrected_value: challengeClassification,
          reason: challengeReason,
        }),
      });

      // Re-run versioned reassessment
      await requestJson(`/research/investigations/${investigationId}/corrections/reassess`, { method: "POST" });

      setSuccessMsg("Correction recorded & investigation reassessment completed!");
      setSelectedRecord(null);
      setChallengeReason("");
      await loadAllData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setActionLoading(false);
    }
  };

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case "strongly_supported":
        return <span style={{ background: "#064e3b", color: "#34d399", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #059669" }}>STRONGLY SUPPORTED</span>;
      case "moderately_supported":
        return <span style={{ background: "#0c4a6e", color: "#38bdf8", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #0284c7" }}>MODERATELY SUPPORTED</span>;
      case "weakly_supported":
        return <span style={{ background: "#78350f", color: "#fbbf24", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #d97706" }}>WEAKLY SUPPORTED</span>;
      case "mixed_evidence":
        return <span style={{ background: "#581c87", color: "#c084fc", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #9333ea" }}>MIXED EVIDENCE</span>;
      case "contradicted":
        return <span style={{ background: "#7f1d1d", color: "#f87171", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #dc2626" }}>CONTRADICTED</span>;
      default:
        return <span style={{ background: "#1e293b", color: "#94a3b8", padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, border: "1px solid #475569" }}>INSUFFICIENT EVIDENCE</span>;
    }
  };

  const getRelationshipBadge = (rel: string) => {
    switch (rel) {
      case "directly_supports":
        return <span style={{ background: "#064e3b", color: "#34d399", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>Direct Support</span>;
      case "partially_supports":
        return <span style={{ background: "#134e4a", color: "#2dd4bf", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>Partial Support</span>;
      case "contradicts":
        return <span style={{ background: "#7f1d1d", color: "#f87171", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>Contradicts</span>;
      case "contextual_background":
        return <span style={{ background: "#3b0764", color: "#c084fc", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>Contextual</span>;
      case "mentions_subject":
        return <span style={{ background: "#1e293b", color: "#94a3b8", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>Mentions Subject</span>;
      default:
        return <span style={{ background: "#1e293b", color: "#cbd5e1", padding: "2px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600 }}>{rel}</span>;
    }
  };

  return (
    <section
      id="scientific-reliability-workspace"
      style={{
        marginTop: "32px",
        background: "#080d1a",
        border: "1px solid #1e293b",
        borderRadius: "8px",
        padding: "24px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: "16px", marginBottom: "20px" }}>
        <div>
          <span style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700, letterSpacing: "0.08em" }}>
            MILESTONE 12 · SCIENTIFIC RELIABILITY & REPRODUCIBILITY
          </span>
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f8fafc", margin: "4px 0" }}>
            Research Intelligence Validation Engine
          </h2>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>
            Defensible evidence synthesis, study-level deduplication, 15-dimension methodology audit, and cryptographic provenance.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={runVerificationAndSynthesis}
            disabled={actionLoading}
            style={{
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: actionLoading ? "not-allowed" : "pointer",
            }}
          >
            {actionLoading ? "Processing..." : "Run Scientific Verification ⚡"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #b91c1c", color: "#fca5a5", padding: "10px 14px", borderRadius: "6px", fontSize: "13px", marginBottom: "16px" }}>
          {error}
        </div>
      )}
      {successMsg && (
        <div style={{ background: "#064e3b", border: "1px solid #059669", color: "#6ee7b7", padding: "10px 14px", borderRadius: "6px", fontSize: "13px", marginBottom: "16px" }}>
          {successMsg}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid #1e293b", paddingBottom: "8px", marginBottom: "20px" }}>
        <button
          onClick={() => setActiveTab("claims")}
          style={{
            background: "transparent",
            border: "none",
            color: activeTab === "claims" ? "#38bdf8" : "#94a3b8",
            borderBottom: activeTab === "claims" ? "2px solid #38bdf8" : "2px solid transparent",
            padding: "6px 12px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Claim Evidence & Synthesis ({syntheses.length})
        </button>
        <button
          onClick={() => setActiveTab("independence")}
          style={{
            background: "transparent",
            border: "none",
            color: activeTab === "independence" ? "#38bdf8" : "#94a3b8",
            borderBottom: activeTab === "independence" ? "2px solid #38bdf8" : "2px solid transparent",
            padding: "6px 12px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Study Independence Clusters ({clusters.length})
        </button>
        <button
          onClick={() => setActiveTab("methodology")}
          style={{
            background: "transparent",
            border: "none",
            color: activeTab === "methodology" ? "#38bdf8" : "#94a3b8",
            borderBottom: activeTab === "methodology" ? "2px solid #38bdf8" : "2px solid transparent",
            padding: "6px 12px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Methodology Audit ({findings.length})
        </button>
        <button
          onClick={() => setActiveTab("reproducibility")}
          style={{
            background: "transparent",
            border: "none",
            color: activeTab === "reproducibility" ? "#38bdf8" : "#94a3b8",
            borderBottom: activeTab === "reproducibility" ? "2px solid #38bdf8" : "2px solid transparent",
            padding: "6px 12px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Execution Manifest & Provenance {manifest ? "🛡️" : ""}
        </button>
      </div>

      {/* Tab 1: Claims & Synthesis */}
      {activeTab === "claims" && (
        <div>
          {syntheses.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
              <p>No claims synthesized yet. Click <strong>Run Scientific Verification</strong> to synthesize claims.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {syntheses.map((s) => {
                const claimVerifs = verifications.filter((v) => v.claim_id === s.claim_id);
                return (
                  <div
                    key={s.id}
                    style={{
                      background: "#0f172a",
                      border: "1px solid #1e293b",
                      borderRadius: "6px",
                      padding: "16px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          {getOutcomeBadge(s.synthesis_outcome)}
                          <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                            {s.unique_underlying_studies_count} unique study cluster{s.unique_underlying_studies_count !== 1 ? "s" : ""} · Score: {Math.round(s.evidence_strength_score * 100)}%
                          </span>
                        </div>
                        <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#f1f5f9", margin: "4px 0" }}>
                          {s.claim_text}
                        </h3>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "16px", background: "#0b1120", padding: "8px 12px", borderRadius: "4px", fontSize: "12px", color: "#94a3b8", marginBottom: "12px" }}>
                      <span>Direct: <strong style={{ color: "#34d399" }}>{s.direct_supporting_count}</strong></span>
                      <span>Partial: <strong style={{ color: "#2dd4bf" }}>{s.partial_supporting_count}</strong></span>
                      <span>Contradicting: <strong style={{ color: "#f87171" }}>{s.contradicting_count}</strong></span>
                      <span>Contextual: <strong style={{ color: "#c084fc" }}>{s.contextual_count}</strong></span>
                      <span>Replication: <strong style={{ color: "#38bdf8" }}>{s.replication_status ?? "Single Study"}</strong></span>
                    </div>

                    {s.synthesis_rationale && (
                      <p style={{ fontSize: "13px", color: "#cbd5e1", margin: "6px 0 12px 0", lineHeight: "1.5" }}>
                        <em>Synthesis Rationale:</em> {s.synthesis_rationale}
                      </p>
                    )}

                    {/* Passages with Provenance */}
                    <div style={{ marginTop: "12px", borderTop: "1px solid #1e293b", paddingTop: "12px" }}>
                      <h4 style={{ fontSize: "12px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 8px 0" }}>
                        Passage Provenance & Reviewer Verification ({claimVerifs.length})
                      </h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {claimVerifs.map((v) => (
                          <div
                            key={v.id}
                            style={{
                              background: "#080d1a",
                              border: "1px solid #1e293b",
                              borderRadius: "4px",
                              padding: "10px 12px",
                              fontSize: "12px",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                {getRelationshipBadge(v.relationship_classification)}
                                <span style={{ color: v.is_challenged ? "#fbbf24" : "#94a3b8" }}>
                                  Status: {v.verification_status} ({Math.round(v.confidence * 100)}% conf)
                                </span>
                              </div>
                              <button
                                onClick={() => {
                                  setSelectedRecord(v);
                                  setChallengeClassification("contextual_background");
                                  setChallengeReason("");
                                }}
                                style={{
                                  background: "transparent",
                                  border: "1px solid #334155",
                                  color: "#94a3b8",
                                  borderRadius: "4px",
                                  padding: "3px 8px",
                                  fontSize: "11px",
                                  cursor: "pointer",
                                }}
                              >
                                Reviewer Challenge ✎
                              </button>
                            </div>
                            <blockquote style={{ margin: "4px 0", color: "#e2e8f0", borderLeft: "2px solid #38bdf8", paddingLeft: "8px", fontStyle: "italic" }}>
                              &ldquo;{v.exact_passage_text}&rdquo;
                            </blockquote>
                            {v.is_challenged && v.challenge_reason && (
                              <p style={{ margin: "4px 0 0 0", color: "#fbbf24", fontSize: "11px" }}>
                                <strong>Human Reviewer Correction:</strong> {v.challenge_reason}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Study Independence */}
      {activeTab === "independence" && (
        <div>
          {clusters.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
              <p>No study clusters generated yet. Click <strong>Run Scientific Verification</strong> to cluster sources.</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "16px" }}>
              {clusters.map((c) => (
                <div
                  key={c.id}
                  style={{
                    background: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "6px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
                      {c.cluster_label}
                    </h3>
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "3px",
                        background: c.relationship_category === "confirmed_independent" ? "#064e3b" : c.relationship_category === "duplicate_publications" ? "#7f1d1d" : "#1e293b",
                        color: c.relationship_category === "confirmed_independent" ? "#34d399" : c.relationship_category === "duplicate_publications" ? "#f87171" : "#fbbf24",
                      }}
                    >
                      {c.relationship_category.replace(/_/g, " ").toUpperCase()}
                    </span>
                  </div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", margin: "6px 0" }}>
                    <strong>Evidence:</strong> {c.evidence_rationale}
                  </p>
                  <div style={{ fontSize: "11px", color: "#64748b", display: "flex", flexDirection: "column", gap: "4px", marginTop: "8px", borderTop: "1px solid #1e293b", paddingTop: "8px" }}>
                    {c.primary_doi && <span>DOI: {c.primary_doi}</span>}
                    {c.shared_authors && c.shared_authors.length > 0 && (
                      <span>Shared Authors: {c.shared_authors.slice(0, 3).join(", ")}</span>
                    )}
                    <span>Underlying Sources: {c.member_source_ids?.length ?? 1}</span>
                    <span>Independence Confidence: {Math.round(c.confidence * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Methodology Audit */}
      {activeTab === "methodology" && (
        <div>
          {findings.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
              <p>No methodology audit findings recorded yet. Click <strong>Run Scientific Verification</strong> to audit.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {findings.map((f) => {
                const isProblem = f.issue_severity === "confirmed_problem";
                const isConcern = f.issue_severity === "potential_concern";
                return (
                  <div
                    key={f.id}
                    style={{
                      background: "#0f172a",
                      borderLeft: `4px solid ${isProblem ? "#ef4444" : isConcern ? "#f59e0b" : "#64748b"}`,
                      borderTop: "1px solid #1e293b",
                      borderRight: "1px solid #1e293b",
                      borderBottom: "1px solid #1e293b",
                      borderRadius: "4px",
                      padding: "14px 16px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "3px",
                            background: isProblem ? "#7f1d1d" : isConcern ? "#78350f" : "#1e293b",
                            color: isProblem ? "#f87171" : isConcern ? "#fbbf24" : "#94a3b8",
                          }}
                        >
                          {f.issue_severity.replace(/_/g, " ").toUpperCase()}
                        </span>
                        <span style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 600 }}>
                          [{f.audit_dimension}]
                        </span>
                      </div>
                    </div>
                    <h4 style={{ fontSize: "14px", fontWeight: 600, color: "#f8fafc", margin: "4px 0" }}>
                      {f.finding_title}
                    </h4>
                    <p style={{ fontSize: "13px", color: "#cbd5e1", margin: "4px 0 8px 0" }}>
                      {f.description}
                    </p>
                    {f.missing_data_condition && (
                      <p style={{ fontSize: "12px", color: "#94a3b8", margin: "2px 0" }}>
                        <em>Missing Evidence Condition:</em> {f.missing_data_condition}
                      </p>
                    )}
                    {f.suggested_action && (
                      <p style={{ fontSize: "12px", color: "#34d399", margin: "4px 0 0 0" }}>
                        <strong>Corrective Action:</strong> {f.suggested_action}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Execution Manifest & Reproducibility */}
      {activeTab === "reproducibility" && (
        <div>
          {!manifest ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
              <p>No execution manifest generated yet. Click <strong>Run Scientific Verification</strong> to create manifest.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px", padding: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div>
                    <span style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700 }}>CANONICAL PROVENANCE RECORD</span>
                    <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#f8fafc", margin: "2px 0" }}>
                      Research Execution Manifest
                    </h3>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={handleVerifyManifest}
                      disabled={actionLoading}
                      style={{
                        background: tamperStatus?.is_tamper_free ? "#064e3b" : "#1e293b",
                        border: "1px solid #334155",
                        color: tamperStatus?.is_tamper_free ? "#34d399" : "#cbd5e1",
                        padding: "6px 12px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      {tamperStatus?.is_tamper_free ? "✓ Verified Tamper-Free" : "Verify Integrity Hash"}
                    </button>
                    <button
                      onClick={handleReproduceRun}
                      disabled={actionLoading}
                      style={{
                        background: "#4f46e5",
                        border: "none",
                        color: "#fff",
                        padding: "6px 14px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Reproduce Investigation ↻
                    </button>
                  </div>
                </div>

                <div style={{ background: "#080d1a", padding: "10px", borderRadius: "4px", fontFamily: "monospace", fontSize: "12px", color: "#38bdf8", wordBreak: "break-all", border: "1px solid #1e293b", marginBottom: "12px" }}>
                  SHA-256 Hash: {manifest.manifest_hash}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", fontSize: "12px", color: "#94a3b8" }}>
                  <div>Queries: <strong style={{ color: "#f1f5f9" }}>{manifest.search_queries_count}</strong></div>
                  <div>Sources: <strong style={{ color: "#f1f5f9" }}>{manifest.sources_count}</strong></div>
                  <div>Evidence: <strong style={{ color: "#f1f5f9" }}>{manifest.evidence_count}</strong></div>
                  <div>Calibrated Tier: <strong style={{ color: "#34d399" }}>{manifest.calibrated_quality_tier}</strong></div>
                </div>
              </div>

              {/* Search Query Timeline */}
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px", padding: "16px" }}>
                <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#f8fafc", margin: "0 0 12px 0" }}>
                  Search Query Sequence & Execution Provenance ({manifest.search_manifest?.length ?? 0})
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {manifest.search_manifest && manifest.search_manifest.length > 0 ? (
                    manifest.search_manifest.map((q, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#080d1a", padding: "8px 12px", borderRadius: "4px", fontSize: "12px" }}>
                        <span style={{ color: "#e2e8f0" }}>{q.query}</span>
                        <span style={{ color: "#64748b", fontSize: "11px" }}>
                          {q.provider ? `Provider: ${q.provider} · ` : ""}{q.results_count ?? 0} results
                        </span>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: "12px", color: "#64748b" }}>No queries logged.</p>
                  )}
                </div>
              </div>

              {/* Agent Timeline */}
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px", padding: "16px" }}>
                <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#f8fafc", margin: "0 0 12px 0" }}>
                  Multi-Agent Execution Timeline
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {manifest.execution_timeline && manifest.execution_timeline.length > 0 ? (
                    manifest.execution_timeline.map((a, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#080d1a", padding: "8px 12px", borderRadius: "4px", fontSize: "12px" }}>
                        <span style={{ color: "#38bdf8", fontWeight: 600 }}>{a.agent_role}</span>
                        <span style={{ color: "#94a3b8" }}>Model: {a.model_identifier ?? "default"}</span>
                        <span style={{ color: a.status === "completed" ? "#34d399" : "#fbbf24" }}>{a.status}</span>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: "12px", color: "#64748b" }}>No agent executions recorded.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reviewer Challenge Modal */}
      {selectedRecord && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            style={{
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "8px",
              padding: "24px",
              maxWidth: "540px",
              width: "100%",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc", margin: "0 0 8px 0" }}>
              Human Reviewer Challenge & Correction
            </h3>
            <p style={{ fontSize: "12px", color: "#94a3b8", margin: "0 0 16px 0" }}>
              Submit a formal scientific challenge to overrule false positives, downgrade aims to contextual background, or flag methodology constraints.
            </p>
            <blockquote style={{ background: "#080d1a", padding: "8px 12px", borderRadius: "4px", fontSize: "12px", color: "#e2e8f0", margin: "0 0 16px 0" }}>
              &ldquo;{selectedRecord.exact_passage_text}&rdquo;
            </blockquote>
            <form onSubmit={submitReviewerChallenge}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                  Corrected Classification:
                </label>
                <select
                  value={challengeClassification}
                  onChange={(e) => setChallengeClassification(e.target.value)}
                  style={{ width: "100%", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", padding: "8px", borderRadius: "4px", fontSize: "13px" }}
                >
                  <option value="directly_supports">Directly Supports</option>
                  <option value="partially_supports">Partially Supports</option>
                  <option value="contradicts">Contradicts</option>
                  <option value="contextual_background">Contextual Background (e.g. Study Aim)</option>
                  <option value="methodological_context">Methodological Context</option>
                  <option value="mentions_subject">Mentions Subject Only</option>
                </select>
              </div>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                  Scientific Justification:
                </label>
                <textarea
                  required
                  rows={3}
                  value={challengeReason}
                  onChange={(e) => setChallengeReason(e.target.value)}
                  placeholder="Explain why this classification is scientifically inaccurate (e.g., rodent trial, study aim without empirical finding, confounding variable)..."
                  style={{ width: "100%", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", padding: "8px", borderRadius: "4px", fontSize: "13px" }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setSelectedRecord(null)}
                  style={{ background: "transparent", border: "1px solid #334155", color: "#94a3b8", padding: "6px 14px", borderRadius: "4px", fontSize: "13px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  style={{ background: "#2563eb", border: "none", color: "#fff", padding: "6px 16px", borderRadius: "4px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
                >
                  {actionLoading ? "Submitting..." : "Apply & Reassess"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
