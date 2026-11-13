"use client";

import { useEffect, useMemo, useState } from "react";
import { requestJson } from "@/lib/api";

export type HypothesisEvaluationView = {
  id: string;
  hypothesis_id: string;
  reviewer_role: string;
  status: string;
  evidence_grounding_score: number;
  novelty_score: number;
  logical_consistency_score: number;
  falsifiability_score: number;
  testability_score: number;
  methodological_feasibility_score: number;
  review_comments: string;
  created_at?: string | null;
};

export type HypothesisView = {
  id: string;
  investigation_id: string;
  title: string;
  statement: string;
  rationale: string;
  category: string;
  status: string;
  claim_ids: string[];
  evidence_ids: string[];
  gap_ids: string[];
  supporting_evidence_ids: string[];
  challenging_evidence_ids: string[];
  proposed_mechanism: string;
  independent_variables: string[];
  dependent_variables: string[];
  expected_outcome: string;
  boundary_conditions: string;
  assumptions: string[];
  confounding_variables: string[];
  suggested_methodology: string;
  falsification_criteria: string;
  generation_method: string;
  confidence_level: string;
  testability_score: number;
  novelty_score: number;
  evidence_grounding_score: number;
  falsifiability_score: number;
  evaluation_notes: string;
  version_number: number;
  evaluations: HypothesisEvaluationView[];
  created_at?: string | null;
  updated_at?: string | null;
};

type Props = {
  investigationId: string;
  investigationQuestion?: string;
};

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  causal: { bg: "rgba(59, 130, 246, 0.12)", text: "#3b82f6", border: "#3b82f6" },
  mechanistic: { bg: "rgba(168, 85, 247, 0.12)", text: "#a855f7", border: "#a855f7" },
  correlational: { bg: "rgba(16, 185, 129, 0.12)", text: "#10b981", border: "#10b981" },
  comparative: { bg: "rgba(245, 158, 11, 0.12)", text: "#f59e0b", border: "#f59e0b" },
  exploratory: { bg: "rgba(99, 102, 241, 0.12)", text: "#6366f1", border: "#6366f1" },
};

const STATUS_BADGES: Record<string, { bg: string; text: string; label: string }> = {
  proposed: { bg: "rgba(148, 163, 184, 0.15)", text: "#94a3b8", label: "Proposed" },
  under_review: { bg: "rgba(245, 158, 11, 0.15)", text: "#f59e0b", label: "Under Review" },
  supported_by_subsequent_evidence: { bg: "rgba(16, 185, 129, 0.15)", text: "#10b981", label: "Corroborated" },
  challenged_by_subsequent_evidence: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444", label: "Challenged" },
  rejected: { bg: "rgba(244, 63, 94, 0.2)", text: "#f43f5e", label: "Falsified / Rejected" },
  refined: { bg: "rgba(6, 182, 212, 0.15)", text: "#06b6d4", label: "Refined" },
};

export function HypothesisWorkspace({ investigationId, investigationQuestion }: Props) {
  const [hypotheses, setHypotheses] = useState<HypothesisView[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [minTestability, setMinTestability] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Status modal / form state
  const [evaluatingHypId, setEvaluatingHypId] = useState<string | null>(null);
  const [evalScoreTestability, setEvalScoreTestability] = useState<number>(8.0);
  const [evalScoreFalsifiability, setEvalScoreFalsifiability] = useState<number>(8.0);
  const [evalScoreGrounding, setEvalScoreGrounding] = useState<number>(7.5);
  const [evalScoreNovelty, setEvalScoreNovelty] = useState<number>(7.0);
  const [evalScoreConsistency, setEvalScoreConsistency] = useState<number>(8.5);
  const [evalScoreFeasibility, setEvalScoreFeasibility] = useState<number>(7.5);
  const [evalStatus, setEvalStatus] = useState<string>("under_review");
  const [evalRole, setEvalRole] = useState<string>("peer_reviewer");
  const [evalComments, setEvalComments] = useState<string>("");
  const [evalSubmitting, setEvalSubmitting] = useState<boolean>(false);

  const loadHypotheses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await requestJson<HypothesisView[]>(
        `/research/investigations/${investigationId}/hypotheses`
      );
      setHypotheses(data || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load hypotheses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (investigationId) {
      loadHypotheses();
    }
  }, [investigationId]);

  const handleGenerate = async (force: boolean = false) => {
    setGenerating(true);
    setError(null);
    try {
      const resp = await requestJson<{ hypotheses: HypothesisView[] }>(
        `/research/investigations/${investigationId}/hypotheses/generate`,
        {
          method: "POST",
          body: JSON.stringify({ force_regenerate: force }),
        }
      );
      setHypotheses(resp.hypotheses || []);
    } catch (err: any) {
      setError(err?.message || "Hypothesis generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const handleQuickStatusChange = async (hypId: string, newStatus: string) => {
    try {
      const updated = await requestJson<HypothesisView>(
        `/research/investigations/${investigationId}/hypotheses/${hypId}/status`,
        {
          method: "PATCH",
          body: JSON.stringify({ status: newStatus, review_comments: `Direct status transition to ${newStatus}` }),
        }
      );
      setHypotheses((prev) => prev.map((h) => (h.id === hypId ? updated : h)));
    } catch (err: any) {
      setError(err?.message || "Failed to update hypothesis status.");
    }
  };

  const handleSubmitEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evaluatingHypId) return;
    setEvalSubmitting(true);
    try {
      const updated = await requestJson<HypothesisView>(
        `/research/investigations/${investigationId}/hypotheses/${evaluatingHypId}/evaluate`,
        {
          method: "POST",
          body: JSON.stringify({
            reviewer_role: evalRole,
            status: evalStatus,
            evidence_grounding_score: evalScoreGrounding,
            novelty_score: evalScoreNovelty,
            logical_consistency_score: evalScoreConsistency,
            falsifiability_score: evalScoreFalsifiability,
            testability_score: evalScoreTestability,
            methodological_feasibility_score: evalScoreFeasibility,
            review_comments: evalComments,
          }),
        }
      );
      setHypotheses((prev) => prev.map((h) => (h.id === evaluatingHypId ? updated : h)));
      setEvaluatingHypId(null);
      setEvalComments("");
    } catch (err: any) {
      setError(err?.message || "Evaluation submission failed.");
    } finally {
      setEvalSubmitting(false);
    }
  };

  const filteredHypotheses = useMemo(() => {
    return hypotheses.filter((h) => {
      if (categoryFilter !== "all" && h.category.toLowerCase() !== categoryFilter.toLowerCase()) return false;
      if (statusFilter !== "all" && h.status.toLowerCase() !== statusFilter.toLowerCase()) return false;
      if (minTestability > 0 && h.testability_score < minTestability) return false;
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = h.title.toLowerCase().includes(query);
        const matchesStatement = h.statement.toLowerCase().includes(query);
        const matchesRationale = h.rationale.toLowerCase().includes(query);
        const matchesMechanism = h.proposed_mechanism.toLowerCase().includes(query);
        if (!matchesTitle && !matchesStatement && !matchesRationale && !matchesMechanism) return false;
      }
      return true;
    });
  }, [hypotheses, categoryFilter, statusFilter, minTestability, searchQuery]);

  return (
    <div className="hypothesis-workspace" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Banner / Actions */}
      <div className="panel" style={{ padding: "18px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>Hypothesis Generation & Review</h2>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "12px", background: "rgba(168, 85, 247, 0.15)", color: "#a855f7" }}>
              Milestone 8B
            </span>
          </div>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: "13px" }}>
            Testable, falsifiable scientific propositions formulated from observed evidence, contradictions, and research gaps.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            className="button primary"
            disabled={generating}
            onClick={() => handleGenerate(true)}
            style={{ display: "flex", alignItems: "center", gap: "8px" }}
          >
            {generating ? "Formulating Hypotheses..." : "Regenerate Hypotheses"}
          </button>
        </div>
      </div>

      {/* Scientific Principle Notice */}
      <div
        style={{
          padding: "12px 18px",
          borderRadius: "8px",
          background: "rgba(59, 130, 246, 0.08)",
          border: "1px solid rgba(59, 130, 246, 0.25)",
          fontSize: "12px",
          color: "#93c5fd",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <span style={{ fontSize: "16px" }}>🔬</span>
        <span>
          <strong>Scientific Validity Standard:</strong> A hypothesis is an empirical proposition to be tested, not verified knowledge or proof. Correlation is never conflated with causation. Every hypothesis requires falsification criteria and boundary conditions.
        </span>
      </div>

      {error && (
        <div className="panel error-banner" style={{ padding: "12px 18px", color: "#ef4444" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Filter Bar */}
      <div className="panel" style={{ padding: "14px 20px", display: "flex", gap: "14px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <input
            type="text"
            className="text-input"
            placeholder="Search statement, variables, or mechanism..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: "100%", padding: "7px 12px", fontSize: "13px" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Category:</label>
          <select
            className="select-input"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ padding: "6px 10px", fontSize: "13px" }}
          >
            <option value="all">All Categories</option>
            <option value="causal">Causal</option>
            <option value="mechanistic">Mechanistic</option>
            <option value="correlational">Correlational</option>
            <option value="comparative">Comparative</option>
            <option value="exploratory">Exploratory</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Status:</label>
          <select
            className="select-input"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: "6px 10px", fontSize: "13px" }}
          >
            <option value="all">All Review Statuses</option>
            <option value="proposed">Proposed</option>
            <option value="under_review">Under Review</option>
            <option value="supported_by_subsequent_evidence">Corroborated</option>
            <option value="challenged_by_subsequent_evidence">Challenged</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Min Testability:</label>
          <input
            type="range"
            min="0"
            max="10"
            step="1"
            value={minTestability}
            onChange={(e) => setMinTestability(parseFloat(e.target.value))}
            style={{ width: "80px" }}
          />
          <span style={{ fontSize: "12px", fontWeight: 600, minWidth: "24px" }}>{minTestability}</span>
        </div>
      </div>

      {/* Main Content List */}
      {loading ? (
        <div className="panel empty-state">
          <p className="muted">Evaluating evidence and generating hypotheses...</p>
        </div>
      ) : filteredHypotheses.length === 0 ? (
        <div className="panel empty-state" style={{ padding: "40px", textAlign: "center" }}>
          <p className="muted" style={{ fontSize: "14px", marginBottom: "12px" }}>
            No hypotheses matching the active filter criteria.
          </p>
          <button className="button primary" onClick={() => handleGenerate(true)}>
            Generate Initial Hypotheses
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {filteredHypotheses.map((hyp) => {
            const catStyle = CATEGORY_COLORS[hyp.category.toLowerCase()] || { bg: "rgba(255,255,255,0.08)", text: "#cbd5e1", border: "#475569" };
            const statusBadge = STATUS_BADGES[hyp.status.toLowerCase()] || { bg: "rgba(255,255,255,0.08)", text: "#cbd5e1", label: hyp.status };
            const isExpanded = expandedId === hyp.id;

            return (
              <div
                key={hyp.id}
                className="panel"
                style={{
                  borderLeft: `4px solid ${catStyle.border}`,
                  padding: "20px 24px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "14px",
                  transition: "box-shadow 0.2s ease",
                }}
              >
                {/* Header Row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", marginBottom: "6px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: catStyle.bg,
                          color: catStyle.text,
                        }}
                      >
                        {hyp.category}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: statusBadge.bg,
                          color: statusBadge.text,
                        }}
                      >
                        {statusBadge.label}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                        Method: <strong>{hyp.generation_method}</strong>
                      </span>
                    </div>

                    <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "4px 0" }}>
                      {hyp.title}
                    </h3>
                  </div>

                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      className="button secondary"
                      style={{ fontSize: "12px", padding: "4px 10px" }}
                      onClick={() => setEvaluatingHypId(hyp.id)}
                    >
                      Evaluate
                    </button>
                    <button
                      className="button secondary"
                      style={{ fontSize: "12px", padding: "4px 10px" }}
                      onClick={() => setExpandedId(isExpanded ? null : hyp.id)}
                    >
                      {isExpanded ? "Hide Details" : "View Details"}
                    </button>
                  </div>
                </div>

                {/* Core Statement */}
                <div
                  style={{
                    padding: "12px 16px",
                    background: "rgba(0, 0, 0, 0.2)",
                    borderRadius: "6px",
                    borderLeft: "3px solid #a855f7",
                    fontSize: "13.5px",
                    lineHeight: 1.5,
                  }}
                >
                  <strong style={{ color: "#c084fc" }}>Proposition: </strong>
                  {hyp.statement}
                </div>

                {/* Scientific Scores Bar */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                    gap: "10px",
                    padding: "10px 14px",
                    background: "rgba(255, 255, 255, 0.02)",
                    borderRadius: "6px",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div>
                    <div className="muted" style={{ fontSize: "11px" }}>Testability</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#10b981" }}>
                      {hyp.testability_score.toFixed(1)} / 10
                    </div>
                  </div>
                  <div>
                    <div className="muted" style={{ fontSize: "11px" }}>Falsifiability</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#a855f7" }}>
                      {hyp.falsifiability_score.toFixed(1)} / 10
                    </div>
                  </div>
                  <div>
                    <div className="muted" style={{ fontSize: "11px" }}>Grounding</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#3b82f6" }}>
                      {hyp.evidence_grounding_score.toFixed(1)} / 10
                    </div>
                  </div>
                  <div>
                    <div className="muted" style={{ fontSize: "11px" }}>Novelty</div>
                    <div style={{ fontSize: "14px", fontWeight: 700, color: "#f59e0b" }}>
                      {hyp.novelty_score.toFixed(1)} / 10
                    </div>
                  </div>
                </div>

                {/* Falsification Criteria (Always visible) */}
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: "rgba(239, 68, 68, 0.06)",
                    border: "1px dashed rgba(239, 68, 68, 0.4)",
                    fontSize: "12.5px",
                  }}
                >
                  <strong style={{ color: "#f87171" }}>Falsification Criteria: </strong>
                  <span style={{ color: "#fecaca" }}>{hyp.falsification_criteria}</span>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "6px", paddingTop: "12px", borderTop: "1px solid var(--border)" }}>
                    {/* Variables */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                      <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "6px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                          Independent Variables (Manipulated / Measured)
                        </div>
                        <div style={{ marginTop: "6px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {hyp.independent_variables.map((iv, idx) => (
                            <span key={idx} style={{ fontSize: "12px", padding: "2px 8px", background: "rgba(59, 130, 246, 0.15)", color: "#93c5fd", borderRadius: "4px" }}>
                              {iv}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.15)", borderRadius: "6px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                          Dependent Variables (Target Outcomes)
                        </div>
                        <div style={{ marginTop: "6px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {hyp.dependent_variables.map((dv, idx) => (
                            <span key={idx} style={{ fontSize: "12px", padding: "2px 8px", background: "rgba(16, 185, 129, 0.15)", color: "#6ee7b7", borderRadius: "4px" }}>
                              {dv}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Proposed Mechanism & Rationale */}
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted)" }}>PROPOSED MECHANISM</div>
                      <p style={{ margin: "4px 0 0", fontSize: "13px" }}>{hyp.proposed_mechanism || "None specified"}</p>
                    </div>

                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted)" }}>SCIENTIFIC RATIONALE</div>
                      <p style={{ margin: "4px 0 0", fontSize: "13px" }}>{hyp.rationale}</p>
                    </div>

                    {/* Boundary Conditions & Confounders */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)" }}>BOUNDARY CONDITIONS</div>
                        <p style={{ margin: "4px 0 0", fontSize: "12px" }}>{hyp.boundary_conditions || "Broad application under standard assumptions."}</p>
                      </div>
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)" }}>CONFOUNDING VARIABLES</div>
                        <p style={{ margin: "4px 0 0", fontSize: "12px" }}>
                          {hyp.confounding_variables.length > 0 ? hyp.confounding_variables.join(", ") : "None documented."}
                        </p>
                      </div>
                    </div>

                    {/* Suggested Methodology */}
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--muted)" }}>SUGGESTED VALIDATION METHODOLOGY</div>
                      <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#e2e8f0" }}>{hyp.suggested_methodology}</p>
                    </div>

                    {/* Evidence Grounding */}
                    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "12px" }}>
                      <div>
                        <strong>Supporting Evidence IDs: </strong>
                        {hyp.supporting_evidence_ids.length > 0 ? hyp.supporting_evidence_ids.join(", ") : "None registered"}
                      </div>
                      <div>
                        <strong>Challenging Evidence IDs: </strong>
                        {hyp.challenging_evidence_ids.length > 0 ? (
                          <span style={{ color: "#f87171" }}>{hyp.challenging_evidence_ids.join(", ")}</span>
                        ) : (
                          "None observed"
                        )}
                      </div>
                    </div>

                    {/* Evaluation History */}
                    {hyp.evaluations && hyp.evaluations.length > 0 && (
                      <div style={{ marginTop: "10px", padding: "10px 14px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                          Peer Evaluation Log ({hyp.evaluations.length})
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                          {hyp.evaluations.map((ev) => (
                            <div key={ev.id} style={{ fontSize: "12px", borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "6px" }}>
                              <span style={{ fontWeight: 600, color: "#93c5fd" }}>{ev.reviewer_role}</span>:{" "}
                              <span style={{ color: "#e2e8f0" }}>{ev.review_comments}</span>{" "}
                              <span className="muted" style={{ fontSize: "11px" }}>
                                (Testability: {ev.testability_score}, Grounding: {ev.evidence_grounding_score})
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Quick Status Action Controls */}
                    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "8px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Quick Status Transition:</span>
                      <button
                        className="button secondary"
                        style={{ fontSize: "11px", padding: "3px 8px" }}
                        onClick={() => handleQuickStatusChange(hyp.id, "under_review")}
                      >
                        Set Under Review
                      </button>
                      <button
                        className="button secondary"
                        style={{ fontSize: "11px", padding: "3px 8px", borderColor: "#10b981", color: "#6ee7b7" }}
                        onClick={() => handleQuickStatusChange(hyp.id, "supported_by_subsequent_evidence")}
                      >
                        Corroborate
                      </button>
                      <button
                        className="button secondary"
                        style={{ fontSize: "11px", padding: "3px 8px", borderColor: "#ef4444", color: "#fca5a5" }}
                        onClick={() => handleQuickStatusChange(hyp.id, "challenged_by_subsequent_evidence")}
                      >
                        Challenge
                      </button>
                      <button
                        className="button secondary"
                        style={{ fontSize: "11px", padding: "3px 8px", borderColor: "#f43f5e", color: "#fda4af" }}
                        onClick={() => handleQuickStatusChange(hyp.id, "rejected")}
                      >
                        Falsify / Reject
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Evaluation Modal / Popover */}
      {evaluatingHypId && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div className="panel" style={{ maxWidth: "600px", width: "100%", maxHeight: "90vh", overflowY: "auto", padding: "24px" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: "0 0 16px" }}>
              Submit Scientific Evaluation
            </h3>

            <form onSubmit={handleSubmitEvaluation} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600 }}>Reviewer Role</label>
                <input
                  type="text"
                  className="text-input"
                  value={evalRole}
                  onChange={(e) => setEvalRole(e.target.value)}
                  style={{ width: "100%", marginTop: "4px" }}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", fontWeight: 600 }}>Review Outcome / Status</label>
                <select
                  className="select-input"
                  value={evalStatus}
                  onChange={(e) => setEvalStatus(e.target.value)}
                  style={{ width: "100%", marginTop: "4px" }}
                >
                  <option value="under_review">Under Review</option>
                  <option value="supported_by_subsequent_evidence">Supported by Evidence</option>
                  <option value="challenged_by_subsequent_evidence">Challenged by Evidence</option>
                  <option value="rejected">Falsified / Rejected</option>
                  <option value="refined">Refined</option>
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px" }}>Testability (0-10): {evalScoreTestability}</label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={evalScoreTestability}
                    onChange={(e) => setEvalScoreTestability(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px" }}>Falsifiability (0-10): {evalScoreFalsifiability}</label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={evalScoreFalsifiability}
                    onChange={(e) => setEvalScoreFalsifiability(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px" }}>Evidence Grounding (0-10): {evalScoreGrounding}</label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={evalScoreGrounding}
                    onChange={(e) => setEvalScoreGrounding(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px" }}>Novelty (0-10): {evalScoreNovelty}</label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={evalScoreNovelty}
                    onChange={(e) => setEvalScoreNovelty(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: "12px", fontWeight: 600 }}>Methodological Evaluation Comments</label>
                <textarea
                  className="text-input"
                  rows={3}
                  value={evalComments}
                  onChange={(e) => setEvalComments(e.target.value)}
                  placeholder="Explain findings, boundary conditions observed, or experimental replication notes..."
                  style={{ width: "100%", marginTop: "4px" }}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setEvaluatingHypId(null)}
                  disabled={evalSubmitting}
                >
                  Cancel
                </button>
                <button type="submit" className="button primary" disabled={evalSubmitting}>
                  {evalSubmitting ? "Submitting..." : "Save Evaluation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
