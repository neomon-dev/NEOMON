"use client";

import { useEffect, useMemo, useState } from "react";
import { requestJson } from "@/lib/api";

export type ContradictionResolutionLogView = {
  id: string;
  contradiction_id: string;
  previous_status: string;
  new_status: string;
  resolution_rationale: string;
  resolving_evidence_ids: string[];
  created_at?: string | null;
};

export type ResearchContradictionView = {
  id: string;
  primary_investigation_id: string;
  primary_investigation_question?: string | null;
  secondary_investigation_id?: string | null;
  secondary_investigation_question?: string | null;
  title: string;
  description: string;
  category: string;
  severity: string;
  confidence: string;
  detection_method: string;
  status: string;
  claim_ids: string[];
  evidence_ids: string[];
  source_ids: string[];
  supporting_passages: { evidence_id?: string; text?: string; claim?: string; source_id?: string }[];
  conflicting_passages: { evidence_id?: string; text?: string; claim?: string; source_id?: string }[];
  scope_differences: string;
  methodological_differences: string;
  resolution_explanation: string;
  recommended_research_action: string;
  resolution_logs: ContradictionResolutionLogView[];
  created_at?: string | null;
  updated_at?: string | null;
};

type InvestigationOption = {
  id: string;
  question: string;
  status: string;
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  critical: { bg: "rgba(239, 68, 68, 0.2)", text: "#ef4444" },
  high: { bg: "rgba(245, 158, 11, 0.2)", text: "#f59e0b" },
  moderate: { bg: "rgba(59, 130, 246, 0.2)", text: "#3b82f6" },
  low: { bg: "rgba(148, 163, 184, 0.2)", text: "#94a3b8" },
};

const STATUS_LABELS: Record<string, string> = {
  newly_detected: "Newly Detected",
  under_investigation: "Under Investigation",
  scope_difference_identified: "Scope Difference Identified",
  methodological_difference_identified: "Methodological Difference",
  partially_resolved: "Partially Resolved",
  resolved_with_evidence: "Resolved with Evidence",
  unresolved: "Genuine Persistent Disagreement",
  requires_human_review: "Requires Human Review",
};

export function ContradictionWorkspace() {
  const [contradictions, setContradictions] = useState<ResearchContradictionView[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationOption[]>([]);
  const [selectedInvId, setSelectedInvId] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [detecting, setDetecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Resolution modal state
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState<string>("scope_difference_identified");
  const [resolutionRationale, setResolutionRationale] = useState<string>("");
  const [submittingResolve, setSubmittingResolve] = useState<boolean>(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [invs, contras] = await Promise.all([
        requestJson<InvestigationOption[]>("/research/investigations"),
        requestJson<ResearchContradictionView[]>("/research/contradictions"),
      ]);
      setInvestigations(invs || []);
      setContradictions(contras || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load contradiction intelligence data.");
    } finally {
      setLoading(false);
    }
  };

  const handleDetect = async () => {
    setDetecting(true);
    setError(null);
    try {
      const detected = await requestJson<ResearchContradictionView[]>(
        "/research/contradictions/detect",
        {
          method: "POST",
          body: JSON.stringify({
            investigation_id: selectedInvId !== "all" ? selectedInvId : null,
            cross_investigation: true,
          }),
        }
      );
      setContradictions(detected || []);
    } catch (err: any) {
      setError(err?.message || "Contradiction detection failed.");
    } finally {
      setDetecting(false);
    }
  };

  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingId) return;
    setSubmittingResolve(true);
    try {
      const updated = await requestJson<ResearchContradictionView>(
        `/research/contradictions/${resolvingId}/resolve`,
        {
          method: "PATCH",
          body: JSON.stringify({
            new_status: newStatus,
            resolution_rationale: resolutionRationale,
            resolving_evidence_ids: [],
          }),
        }
      );
      setContradictions((prev) => prev.map((c) => (c.id === resolvingId ? updated : c)));
      setResolvingId(null);
      setResolutionRationale("");
    } catch (err: any) {
      setError(err?.message || "Failed to submit resolution.");
    } finally {
      setSubmittingResolve(false);
    }
  };

  const filteredContradictions = useMemo(() => {
    return contradictions.filter((c) => {
      if (selectedInvId !== "all") {
        if (c.primary_investigation_id !== selectedInvId && c.secondary_investigation_id !== selectedInvId) {
          return false;
        }
      }
      if (statusFilter !== "all" && c.status.toLowerCase() !== statusFilter.toLowerCase()) return false;
      if (categoryFilter !== "all" && c.category.toLowerCase() !== categoryFilter.toLowerCase()) return false;
      if (severityFilter !== "all" && c.severity.toLowerCase() !== severityFilter.toLowerCase()) return false;
      return true;
    });
  }, [contradictions, selectedInvId, statusFilter, categoryFilter, severityFilter]);

  return (
    <div className="contradiction-workspace" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Banner */}
      <div className="panel" style={{ padding: "18px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>Scientific Contradiction Intelligence</h2>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "12px", background: "rgba(239, 68, 68, 0.15)", color: "#ef4444" }}>
              Milestone 8D
            </span>
          </div>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: "13px" }}>
            Identify, classify, and track empirical discrepancies across claims and studies without forcing artificial consensus.
          </p>
        </div>

        <button
          className="button primary"
          disabled={detecting}
          onClick={handleDetect}
        >
          {detecting ? "Scanning for Contradictions..." : "Detect Scientific Contradictions"}
        </button>
      </div>

      {/* Scientific Principle Notice */}
      <div
        style={{
          padding: "12px 18px",
          borderRadius: "8px",
          background: "rgba(239, 68, 68, 0.08)",
          border: "1px solid rgba(239, 68, 68, 0.25)",
          fontSize: "12px",
          color: "#fca5a5",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <span style={{ fontSize: "16px" }}>⚖️</span>
        <span>
          <strong>Scientific Principle:</strong> Authentic empirical divergence is a discovery opportunity. Never force artificial consensus. Genuine contradictions must be investigated through boundary conditions, population differences, or temporal shifts.
        </span>
      </div>

      {error && (
        <div className="panel error-banner" style={{ padding: "12px 18px", color: "#ef4444" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Filters Bar */}
      <div className="panel" style={{ padding: "14px 20px", display: "flex", gap: "14px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Investigation:</label>
          <select
            className="select-input"
            value={selectedInvId}
            onChange={(e) => setSelectedInvId(e.target.value)}
            style={{ fontSize: "13px", maxWidth: "260px" }}
          >
            <option value="all">All Investigations</option>
            {investigations.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.question}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Category:</label>
          <select
            className="select-input"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ fontSize: "13px" }}
          >
            <option value="all">All Categories</option>
            <option value="direct_factual">Direct Factual</option>
            <option value="quantitative">Quantitative</option>
            <option value="causal">Causal</option>
            <option value="methodological">Methodological</option>
            <option value="scope_dependent">Scope Dependent</option>
            <option value="population_specific">Population Specific</option>
            <option value="temporal">Temporal</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Severity:</label>
          <select
            className="select-input"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{ fontSize: "13px" }}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="moderate">Moderate</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted)" }}>Status:</label>
          <select
            className="select-input"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ fontSize: "13px" }}
          >
            <option value="all">All Statuses</option>
            <option value="newly_detected">Newly Detected</option>
            <option value="under_investigation">Under Investigation</option>
            <option value="scope_difference_identified">Scope Difference</option>
            <option value="methodological_difference_identified">Methodological</option>
            <option value="partially_resolved">Partially Resolved</option>
            <option value="resolved_with_evidence">Resolved with Evidence</option>
            <option value="unresolved">Unresolved (Persistent)</option>
          </select>
        </div>
      </div>

      {/* Main Contradictions List */}
      {loading ? (
        <div className="panel empty-state">
          <p className="muted">Analyzing empirical discrepancies...</p>
        </div>
      ) : filteredContradictions.length === 0 ? (
        <div className="panel empty-state" style={{ padding: "40px", textAlign: "center" }}>
          <p className="muted" style={{ fontSize: "14px", marginBottom: "12px" }}>
            No scientific contradictions matching active filter parameters.
          </p>
          <button className="button primary" onClick={handleDetect}>
            Scan for Contradictions
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {filteredContradictions.map((c) => {
            const sev = SEVERITY_COLORS[c.severity.toLowerCase()] || { bg: "rgba(255,255,255,0.08)", text: "#cbd5e1" };
            const statusLabel = STATUS_LABELS[c.status] || c.status;

            return (
              <div
                key={c.id}
                className="panel"
                style={{
                  borderLeft: `4px solid ${sev.text}`,
                  padding: "20px 24px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "14px",
                }}
              >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "6px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: sev.bg,
                          color: sev.text,
                        }}
                      >
                        {c.severity} Severity
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: "rgba(255,255,255,0.08)",
                          color: "#93c5fd",
                        }}
                      >
                        Category: {c.category}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: "rgba(255,255,255,0.05)",
                          color: "#cbd5e1",
                        }}
                      >
                        Status: {statusLabel}
                      </span>
                    </div>

                    <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "4px 0" }}>{c.title}</h3>
                  </div>

                  <button
                    className="button secondary"
                    style={{ fontSize: "12px", padding: "4px 10px" }}
                    onClick={() => {
                      setResolvingId(c.id);
                      setNewStatus(c.status);
                    }}
                  >
                    Update Resolution
                  </button>
                </div>

                {/* Description */}
                <div style={{ fontSize: "13.5px", lineHeight: 1.5, color: "#e2e8f0" }}>{c.description}</div>

                {/* Comparative Passages */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                  <div style={{ padding: "12px 14px", background: "rgba(16, 185, 129, 0.05)", borderLeft: "3px solid #10b981", borderRadius: "4px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "#6ee7b7", textTransform: "uppercase", marginBottom: "6px" }}>
                      Supporting Empirical Evidence ({c.supporting_passages.length})
                    </div>
                    {c.supporting_passages.map((p, idx) => (
                      <div key={idx} style={{ fontSize: "12.5px", fontStyle: "italic", marginBottom: "4px" }}>
                        "{p.text || p.claim}"
                      </div>
                    ))}
                  </div>

                  <div style={{ padding: "12px 14px", background: "rgba(239, 68, 68, 0.05)", borderLeft: "3px solid #ef4444", borderRadius: "4px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "#fca5a5", textTransform: "uppercase", marginBottom: "6px" }}>
                      Conflicting / Counter-Evidence ({c.conflicting_passages.length})
                    </div>
                    {c.conflicting_passages.map((p, idx) => (
                      <div key={idx} style={{ fontSize: "12.5px", fontStyle: "italic", marginBottom: "4px" }}>
                        "{p.text || p.claim}"
                      </div>
                    ))}
                  </div>
                </div>

                {/* Distinguishing Factors */}
                {(c.scope_differences || c.methodological_differences) && (
                  <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.2)", borderRadius: "6px", fontSize: "12.5px", display: "flex", flexDirection: "column", gap: "4px" }}>
                    {c.scope_differences && (
                      <div>
                        <strong style={{ color: "#93c5fd" }}>Scope Difference: </strong>
                        {c.scope_differences}
                      </div>
                    )}
                    {c.methodological_differences && (
                      <div>
                        <strong style={{ color: "#f59e0b" }}>Methodological Difference: </strong>
                        {c.methodological_differences}
                      </div>
                    )}
                  </div>
                )}

                {/* Recommended Action */}
                {c.recommended_research_action && (
                  <div style={{ fontSize: "12.5px", padding: "8px 12px", background: "rgba(59, 130, 246, 0.05)", borderLeft: "3px solid #3b82f6", borderRadius: "4px" }}>
                    <strong style={{ color: "#93c5fd" }}>Recommended Action: </strong>
                    {c.recommended_research_action}
                  </div>
                )}

                {/* Resolution Logs */}
                {c.resolution_logs && c.resolution_logs.length > 0 && (
                  <div style={{ borderTop: "1px solid var(--border)", paddingTop: "10px", marginTop: "4px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", marginBottom: "6px" }}>
                      Resolution Audit Log ({c.resolution_logs.length})
                    </div>
                    {c.resolution_logs.map((log) => (
                      <div key={log.id} style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600, color: "#cbd5e1" }}>
                          {STATUS_LABELS[log.new_status] || log.new_status}:
                        </span>{" "}
                        {log.resolution_rationale}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Resolution Modal */}
      {resolvingId && (
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
          <div className="panel" style={{ maxWidth: "560px", width: "100%", padding: "24px" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: "0 0 16px" }}>
              Update Contradiction Resolution
            </h3>

            <form onSubmit={handleResolveSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600 }}>Target Resolution Lifecycle Status</label>
                <select
                  className="select-input"
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  style={{ width: "100%", marginTop: "4px" }}
                >
                  <option value="under_investigation">Under Investigation</option>
                  <option value="scope_difference_identified">Scope Difference Identified</option>
                  <option value="methodological_difference_identified">Methodological Difference Identified</option>
                  <option value="partially_resolved">Partially Resolved</option>
                  <option value="resolved_with_evidence">Resolved with Evidence</option>
                  <option value="unresolved">Unresolved (Genuine Scientific Controversy)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", fontWeight: 600 }}>Scientific Resolution Rationale</label>
                <textarea
                  className="text-input"
                  rows={4}
                  value={resolutionRationale}
                  onChange={(e) => setResolutionRationale(e.target.value)}
                  placeholder="Explain why the discrepancy occurs (e.g. boundary conditions, differing populations, measurement techniques)..."
                  style={{ width: "100%", marginTop: "4px" }}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setResolvingId(null)}
                  disabled={submittingResolve}
                >
                  Cancel
                </button>
                <button type="submit" className="button primary" disabled={submittingResolve}>
                  {submittingResolve ? "Saving..." : "Save Resolution"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
