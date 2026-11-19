"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiBaseUrl, requestJson } from "@/lib/api";
import {
  SpotlightCard,
  AnimatedCounter,
  PulseIndicator,
  BorderBeam,
  RevealSection,
} from "@/components/motion";

export type RecommendedAction = {
  action_type: string;
  description: string;
  suggested_queries: string[];
  target_source_types: string[];
  expected_contribution: string;
};

export type ResearchGapView = {
  id: string;
  analysis_id: string;
  investigation_id: string;
  category: string;
  gap_type: string;
  title: string;
  description: string;
  claim_ids: string[];
  evidence_ids: string[];
  source_ids: string[];
  supporting_explanation: string;
  missing_information: string;
  severity: string;
  research_priority: number;
  confidence: string;
  is_observed: boolean;
  recommended_action: RecommendedAction;
  created_at?: string | null;
};

export type ResearchCoverageSummary = {
  coverage_score: number;
  total_claims: number;
  claims_with_direct_support: number;
  claims_with_conflicts: number;
  claims_unsupported: number;
  claims_single_source: number;
  total_sources: number;
  independent_clusters: number;
  full_text_count: number;
  unresolved_provenance_count: number;
  critical_gaps: number;
  high_gaps: number;
  moderate_gaps: number;
  low_gaps: number;
  narrative: string;
};

export type ResearchGapAnalysisResponse = {
  id: string;
  investigation_id: string;
  version_number: number;
  summary: string;
  coverage: ResearchCoverageSummary;
  gaps: ResearchGapView[];
  created_at?: string | null;
};

export type ResearchGapVersionView = {
  id: string;
  investigation_id: string;
  version_number: number;
  summary: string;
  coverage_score: number;
  critical_count: number;
  high_count: number;
  moderate_count: number;
  low_count: number;
  created_at?: string | null;
};

type Props = {
  investigationId: string;
  investigationQuestion?: string;
};

export function ResearchGapWorkspace({ investigationId, investigationQuestion }: Props) {
  const [analysis, setAnalysis] = useState<ResearchGapAnalysisResponse | null>(null);
  const [versions, setVersions] = useState<ResearchGapVersionView[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<string>("latest");
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedGapId, setExpandedGapId] = useState<string | null>(null);
  const [copiedQuery, setCopiedQuery] = useState<string | null>(null);

  // Load versions
  const loadVersions = useCallback(async () => {
    try {
      const data = await requestJson<ResearchGapVersionView[]>(
        `/research/investigations/${investigationId}/gaps/versions`
      );
      setVersions(data);
    } catch {
      // Version list is non-critical metadata
    }
  }, [investigationId]);

  // Load analysis data
  const loadAnalysis = useCallback(async (versionOrId?: string) => {
    setLoading(true);
    setError(null);
    try {
      let data: ResearchGapAnalysisResponse;
      if (versionOrId && versionOrId !== "latest") {
        data = await requestJson<ResearchGapAnalysisResponse>(
          `/research/investigations/${investigationId}/gaps/versions/${versionOrId}`
        );
      } else {
        data = await requestJson<ResearchGapAnalysisResponse>(
          `/research/investigations/${investigationId}/gaps`
        );
      }
      setAnalysis(data);
      if (data.gaps.length > 0) {
        setExpandedGapId((prev) => prev || data.gaps[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load research gap analysis";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    if (investigationId) {
      loadAnalysis();
      loadVersions();
    }
  }, [investigationId, loadAnalysis, loadVersions]);

  // Trigger re-analysis
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const data = await requestJson<ResearchGapAnalysisResponse>(
        `/research/investigations/${investigationId}/gaps/analyze`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ force_regenerate: true }),
        }
      );
      setAnalysis(data);
      setSelectedVersion("latest");
      await loadVersions();
      if (data.gaps.length > 0) {
        setExpandedGapId(data.gaps[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run gap analysis";
      setError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCopyQuery = (query: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(query);
      setCopiedQuery(query);
      setTimeout(() => setCopiedQuery(null), 2000);
    }
  };

  // Filtered gaps
  const filteredGaps = useMemo(() => {
    if (!analysis) return [];
    return analysis.gaps.filter((g) => {
      if (severityFilter !== "all" && g.severity.toLowerCase() !== severityFilter.toLowerCase()) {
        return false;
      }
      if (categoryFilter !== "all" && g.category.toLowerCase() !== categoryFilter.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = g.title.toLowerCase().includes(q);
        const matchesDesc = g.description.toLowerCase().includes(q);
        const matchesMissing = g.missing_information.toLowerCase().includes(q);
        const matchesType = g.gap_type.toLowerCase().includes(q);
        if (!matchesTitle && !matchesDesc && !matchesMissing && !matchesType) {
          return false;
        }
      }
      return true;
    });
  }, [analysis, severityFilter, categoryFilter, searchQuery]);

  // Coverage score color
  const coverageScore = analysis?.coverage.coverage_score ?? 0;
  const coverageColor =
    coverageScore >= 75 ? "#10b981" : coverageScore >= 45 ? "#f59e0b" : "#ef4444";

  // Segment calculations for coverage distribution
  const totalClaimsCount = analysis?.coverage.total_claims || 1;
  const directSupportPct = Math.round(((analysis?.coverage.claims_with_direct_support || 0) / totalClaimsCount) * 100);
  const conflictPct = Math.round(((analysis?.coverage.claims_with_conflicts || 0) / totalClaimsCount) * 100);
  const unsupportedPct = Math.round(((analysis?.coverage.claims_unsupported || 0) / totalClaimsCount) * 100);

  return (
    <div className="research-gap-workspace" id="research-gap-workspace">
      {/* Header bar */}
      <div className="gap-workspace-header" style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", background: "var(--surface)", borderRadius: "10px", border: "1px solid var(--border)", marginBottom: "16px" }}>
        <div className="gap-header-titles">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", borderRadius: "10px", background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.3)" }}>
              EVIDENCE HORIZON & RESEARCH GAPS
            </span>
            <span className="milestone-hidden" data-milestone="8A" style={{ display: "none" }}>
              AUTONOMOUS GAP DISCOVERY · MILESTONE 8A
            </span>
          </div>
          <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>Research Gaps & Evidence Horizon</h2>
          <p className="muted" style={{ fontSize: "13px", marginTop: "2px", margin: "2px 0 0" }}>
            Uncovers inadequately supported claims, conflicting evidence, missing perspectives, and high-yield research subquestions.
          </p>
        </div>

        <div className="gap-header-actions" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {versions.length > 1 && (
            <div className="gap-version-selector" style={{ display: "flex", alignItems: "center" }}>
              <label htmlFor="gap-version-select" className="muted" style={{ fontSize: "12px", marginRight: "6px" }}>
                Version:
              </label>
              <select
                id="gap-version-select"
                className="select-input compact-select"
                value={selectedVersion}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedVersion(val);
                  loadAnalysis(val);
                }}
                style={{ fontSize: "12px", padding: "5px 8px" }}
              >
                <option value="latest">Latest (v{analysis?.version_number ?? 1})</option>
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} — {v.coverage_score}% ({v.critical_count} critical)
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            className="cyber-primary-btn"
            onClick={handleAnalyze}
            disabled={analyzing || loading}
            style={{ padding: "8px 16px", fontSize: "12px" }}
          >
            {analyzing ? "Analyzing Gaps..." : "⚡ Run Gap Discovery"}
          </button>
        </div>
      </div>

      {error && (
        <div className="gap-error-banner" role="alert" style={{ marginBottom: "16px" }}>
          <strong>Gap Analysis Error:</strong> {error}
        </div>
      )}

      {loading && !analysis ? (
        <div className="gap-loading-skeleton">
          <div className="skeleton-bar" style={{ width: "60%", height: "24px" }} />
          <div className="skeleton-bar" style={{ width: "100%", height: "80px", marginTop: "12px" }} />
          <div className="skeleton-bar" style={{ width: "90%", height: "140px", marginTop: "12px" }} />
        </div>
      ) : analysis ? (
        <>
          {/* Prominent Evidence Coverage Dashboard */}
          <section className="gap-coverage-card" style={{ padding: "20px", marginBottom: "16px", background: "var(--surface)", borderRadius: "10px", border: "1px solid var(--border)" }}>
            <div className="coverage-main-grid" style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "24px", alignItems: "center" }}>
              {/* Prominent Coverage Gauge Box */}
              <div className="coverage-meter-box" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "16px", background: "rgba(12, 25, 43, 0.6)", borderRadius: "10px", border: "1px solid rgba(37, 217, 242, 0.15)" }}>
                <div className="coverage-score-circle" style={{ width: "100px", height: "100px", borderRadius: "50%", border: `4px solid ${coverageColor}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: `0 0 20px -4px ${coverageColor}66` }}>
                  <span className="coverage-number" style={{ color: coverageColor, fontSize: "28px", fontWeight: 800, lineHeight: 1 }}>
                    <AnimatedCounter value={coverageScore} />%
                  </span>
                  <span className="coverage-label" style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase", marginTop: "4px" }}>
                    Coverage
                  </span>
                </div>
                <div className="coverage-tier-badge" style={{ marginTop: "12px", backgroundColor: `${coverageColor}22`, color: coverageColor, padding: "4px 12px", borderRadius: "12px", fontSize: "11px", fontWeight: 700, border: `1px solid ${coverageColor}44` }}>
                  {coverageScore >= 75 ? "Defensible Synthesis" : coverageScore >= 45 ? "Moderate Gaps Identified" : "High Uncertainty / Critical Gaps"}
                </div>
              </div>

              {/* Statistics & Horizontal Breakdown */}
              <div className="coverage-stats-box" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {/* Horizontal Multi-Segment Coverage Progress Bar */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px", fontSize: "11px", color: "var(--muted)", fontWeight: 600 }}>
                    <span>EVIDENCE SUPPORT DISTRIBUTION</span>
                    <span>{analysis.coverage.total_claims} Total Claims Examined</span>
                  </div>
                  <div style={{ width: "100%", height: "10px", borderRadius: "5px", background: "rgba(255, 255, 255, 0.08)", overflow: "hidden", display: "flex" }}>
                    <div style={{ width: `${directSupportPct}%`, background: "#10b981" }} title={`Direct Support: ${directSupportPct}%`} />
                    <div style={{ width: `${conflictPct}%`, background: "#f59e0b" }} title={`Contradictions: ${conflictPct}%`} />
                    <div style={{ width: `${unsupportedPct}%`, background: "#f43f5e" }} title={`Unsupported: ${unsupportedPct}%`} />
                  </div>
                  <div style={{ display: "flex", gap: "16px", marginTop: "6px", fontSize: "11px" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#10b981" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "#10b981" }} /> Direct Support ({directSupportPct}%)
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#f59e0b" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "#f59e0b" }} /> Contradictions ({conflictPct}%)
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#f43f5e" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "#f43f5e" }} /> Unsupported ({unsupportedPct}%)
                    </span>
                  </div>
                </div>

                {/* Micro Metric Grid */}
                <div className="stats-row" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "10px" }}>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val" style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", display: "block" }}>{analysis.coverage.total_claims}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Claims Tested</span>
                  </div>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val text-green" style={{ fontSize: "18px", fontWeight: 700, color: "#10b981", display: "block" }}>{analysis.coverage.claims_with_direct_support}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Direct Support</span>
                  </div>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val text-red" style={{ fontSize: "18px", fontWeight: 700, color: "#f43f5e", display: "block" }}>{analysis.coverage.claims_unsupported}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Unsupported</span>
                  </div>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val text-orange" style={{ fontSize: "18px", fontWeight: 700, color: "#f59e0b", display: "block" }}>{analysis.coverage.claims_with_conflicts}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Contradictions</span>
                  </div>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val" style={{ fontSize: "18px", fontWeight: 700, color: "#38bdf8", display: "block" }}>{analysis.coverage.independent_clusters}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Origin Clusters</span>
                  </div>
                  <div className="stat-item" style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span className="stat-val" style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", display: "block" }}>{analysis.coverage.full_text_count}/{analysis.coverage.total_sources}</span>
                    <span className="stat-desc" style={{ fontSize: "10px", color: "var(--muted)" }}>Full-Text Docs</span>
                  </div>
                </div>

                {/* Narrative Summary */}
                <div className="coverage-narrative-box" style={{ padding: "10px 14px", background: "rgba(56, 189, 248, 0.04)", borderRadius: "6px", borderLeft: "3px solid #38bdf8" }}>
                  <p style={{ margin: 0, fontSize: "12px", color: "#cbd5e1", lineHeight: 1.5 }}>{analysis.coverage.narrative}</p>
                </div>
              </div>
            </div>
          </section>

          {/* Severity & Category Filter Bar */}
          <div className="gap-filter-toolbar">
            {/* Severity Tabs */}
            <div className="filter-pill-group">
              <span className="filter-group-label">Severity:</span>
              {[
                { id: "all", label: "All", count: analysis.gaps.length },
                { id: "critical", label: "Critical", count: analysis.coverage.critical_gaps, cls: "pill-critical" },
                { id: "high", label: "High", count: analysis.coverage.high_gaps, cls: "pill-high" },
                { id: "moderate", label: "Moderate", count: analysis.coverage.moderate_gaps, cls: "pill-moderate" },
                { id: "low", label: "Low", count: analysis.coverage.low_gaps, cls: "pill-low" },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  className={`filter-pill ${severityFilter === btn.id ? "active" : ""} ${btn.cls || ""}`}
                  onClick={() => setSeverityFilter(btn.id)}
                >
                  {btn.label} <span className="pill-badge">{btn.count}</span>
                </button>
              ))}
            </div>

            {/* Category Tabs */}
            <div className="filter-pill-group">
              <span className="filter-group-label">Category:</span>
              {[
                { id: "all", label: "All Dimensions" },
                { id: "claim_coverage", label: "Claim Gaps" },
                { id: "evidence_coverage", label: "Evidence Gaps" },
                { id: "perspective", label: "Perspective" },
                { id: "research_question", label: "Subquestions" },
              ].map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  className={`filter-pill ${categoryFilter === cat.id ? "active" : ""}`}
                  onClick={() => setCategoryFilter(cat.id)}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="gap-search-input-wrap">
              <input
                type="text"
                className="gap-search-input"
                placeholder="Search gap keywords..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="gap-search-clear"
                  onClick={() => setSearchQuery("")}
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Gaps List & Inspection View */}
          <div className="gap-items-container">
            {filteredGaps.length === 0 ? (
              <div className="gap-empty-state">
                <p>No research gaps match the selected filters.</p>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => {
                    setSeverityFilter("all");
                    setCategoryFilter("all");
                    setSearchQuery("");
                  }}
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <div className="gap-cards-list">
                {filteredGaps.map((gap) => {
                  const isExpanded = expandedGapId === gap.id;
                  const severityClass = `severity-${gap.severity}`;
                  const priorityFormatted = gap.research_priority.toFixed(1);

                  return (
                    <div
                      key={gap.id}
                      className={`gap-card ${severityClass} ${isExpanded ? "expanded" : ""}`}
                    >
                      <div
                        className="gap-card-header"
                        onClick={() => setExpandedGapId(isExpanded ? null : gap.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            setExpandedGapId(isExpanded ? null : gap.id);
                          }
                        }}
                      >
                        <div className="gap-card-meta-row">
                          <span className={`gap-severity-badge ${severityClass}`}>
                            {gap.severity.toUpperCase()}
                          </span>
                          <span className="gap-priority-pill" title="Calculated Research Priority">
                            Priority: {priorityFormatted}/10
                          </span>
                          <span className="gap-category-tag">
                            {gap.category.replace("_", " ")}
                          </span>
                          <span className="gap-type-tag">
                            {gap.gap_type.replace(/_/g, " ")}
                          </span>
                          <span className="gap-confidence-tag">
                            Confidence: {gap.confidence}
                          </span>
                        </div>

                        <h4 className="gap-card-title">{gap.title}</h4>
                        <p className="gap-card-desc">{gap.description}</p>

                        <div className="gap-card-toggle-indicator">
                          {isExpanded ? "Hide Details ▲" : "Inspect Action & Queries ▼"}
                        </div>
                      </div>

                      {/* Expanded Details Body */}
                      {isExpanded && (
                        <div className="gap-card-body">
                          {/* Supporting Explanation */}
                          <div className="gap-detail-section">
                            <strong>Evidentiary Basis & Observation:</strong>
                            <p className="gap-explanation-text">{gap.supporting_explanation}</p>
                          </div>

                          {/* Missing Information Callout */}
                          <div className="gap-missing-info-box">
                            <strong>Missing Information / Required Data:</strong>
                            <p>{gap.missing_information}</p>
                          </div>

                          {/* Recommended Action Card */}
                          {gap.recommended_action && (
                            <div className="gap-action-box">
                              <div className="gap-action-header">
                                <span className="action-type-pill">
                                  Action: {gap.recommended_action.action_type.replace(/_/g, " ")}
                                </span>
                                {gap.recommended_action.target_source_types?.length > 0 && (
                                  <div className="target-types-group">
                                    <span className="muted" style={{ fontSize: "11px", marginRight: "4px" }}>
                                      Target Sources:
                                    </span>
                                    {gap.recommended_action.target_source_types.map((st) => (
                                      <span key={st} className="source-type-pill">
                                        {st}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>

                              <p className="gap-action-description">
                                {gap.recommended_action.description}
                              </p>

                              {gap.recommended_action.expected_contribution && (
                                <p className="gap-action-contribution">
                                  <strong>Expected Outcome: </strong>
                                  {gap.recommended_action.expected_contribution}
                                </p>
                              )}

                              {/* Suggested Provider Queries */}
                              {gap.recommended_action.suggested_queries?.length > 0 && (
                                <div className="gap-queries-section">
                                  <span className="queries-label">
                                    Suggested Provider Search Queries:
                                  </span>
                                  <div className="queries-list">
                                    {gap.recommended_action.suggested_queries.map((q, idx) => {
                                      const isCopied = copiedQuery === q;
                                      return (
                                        <div key={idx} className="query-row">
                                          <code className="query-code">{q}</code>
                                          <button
                                            type="button"
                                            className="copy-query-button"
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              handleCopyQuery(q);
                                            }}
                                            title="Copy query to clipboard"
                                          >
                                            {isCopied ? "✓ Copied" : "📋 Copy"}
                                          </button>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
