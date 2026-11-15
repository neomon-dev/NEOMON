"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { requestJson } from "@/lib/api";

export type InvestigationQualityAuditItem = {
  investigation_id: string;
  question: string;
  quality_status: string;
  calibrated_tier: string;
  calibrated_score: number;
  raw_score: number;
  coverage_score: number;
  failure_penalty: number;
  operational_completeness?: number;
  research_coverage?: number;
  evidence_strength?: number;
  source_count: number;
  evidence_count: number;
  updated_at?: string | null;
};

export type QualityCalibrationAuditView = {
  investigation_id: string;
  investigation_question: string;
  calibrated_tier: string;
  raw_score: number;
  calibrated_score: number;
  coverage_score: number;
  failure_penalty: number;
  operational_completeness?: number;
  research_coverage?: number;
  evidence_strength?: number;
  dimension_breakdown: Record<string, any>;
  calibration_reasons: string[];
  verified_peer_reviewed_count: number;
  primary_source_count: number;
  total_sources: number;
  total_claims: number;
  total_evidence: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type SourceLineageCluster = {
  cluster_id: string;
  cluster_name: string;
  primary_source_id?: string | null;
  member_source_ids: string[];
  relationship_type: string;
  explanation: string;
  effective_independence_weight: number;
};

export type SourceLineageRelationship = {
  id: string;
  source_id: string;
  related_source_id: string;
  relationship_type: string;
  confidence: number;
  shared_identifiers: string[];
  explanation: string;
  created_at?: string | null;
};

export type SourceLineageOverviewResponse = {
  investigation_id: string;
  total_sources: number;
  effective_independent_count: number;
  independence_ratio: number;
  lineage_summary: string;
  clusters: SourceLineageCluster[];
  relationships: SourceLineageRelationship[];
};

export type EvidenceClaimValidation = {
  id: string;
  investigation_id: string;
  claim_id: string;
  claim_text: string;
  evidence_id: string;
  evidence_text: string;
  entailment_classification: string;
  entailment_strength: number;
  explanation: string;
  missing_inferential_steps: string[];
  correlation_vs_causation_flag: boolean;
  validation_method: string;
  validator_model?: string | null;
  status: string;
  created_at?: string | null;
};

export type ProviderFailureImpact = {
  id: string;
  investigation_id: string;
  provider: string;
  operation: string;
  query: string;
  failure_type: string;
  retry_attempts: number;
  impact_severity: string;
  missing_category?: string | null;
  explanation: string;
  created_at?: string | null;
};

export function QualityAuditWorkspace({ initialInvestigationId }: { initialInvestigationId?: string }) {
  const [investigations, setInvestigations] = useState<InvestigationQualityAuditItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>(initialInvestigationId || "");
  const [audit, setAudit] = useState<QualityCalibrationAuditView | null>(null);
  const [lineage, setLineage] = useState<SourceLineageOverviewResponse | null>(null);
  const [validations, setValidations] = useState<EvidenceClaimValidation[]>([]);
  const [failures, setFailures] = useState<ProviderFailureImpact[]>([]);
  const [activeTab, setActiveTab] = useState<"dimensions" | "lineage" | "entailment" | "failures">("dimensions");
  const [loading, setLoading] = useState<boolean>(true);
  const [calibrating, setCalibrating] = useState<boolean>(false);
  const [entailmentFilter, setEntailmentFilter] = useState<string>("all");

  // Load all investigation audit items
  useEffect(() => {
    let active = true;
    async function loadAudits() {
      try {
        const data = await requestJson<InvestigationQualityAuditItem[]>(
          `/research/quality/audits`
        );
        if (!active) return;
        setInvestigations(data || []);
        if (data && data.length > 0) {
          setSelectedId((prev) => prev || initialInvestigationId || data[0].investigation_id);
        }
      } catch (err) {
        if (active) console.error("Failed to load quality audits:", err);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadAudits();
    return () => {
      active = false;
    };
  }, [initialInvestigationId]);

  // Load details for selected investigation
  useEffect(() => {
    if (!selectedId) return;
    let active = true;

    async function loadDetails() {
      setLoading(true);
      try {
        const [auditRes, lineageRes, valRes, failRes] = await Promise.all([
          requestJson<QualityCalibrationAuditView>(
            `/research/investigations/${selectedId}/quality/audit`
          ),
          requestJson<SourceLineageOverviewResponse>(
            `/research/investigations/${selectedId}/quality/lineage`
          ),
          requestJson<EvidenceClaimValidation[]>(
            `/research/investigations/${selectedId}/quality/validations`
          ),
          requestJson<ProviderFailureImpact[]>(
            `/research/investigations/${selectedId}/quality/failures`
          ),
        ]);
        if (!active) return;
        setAudit(auditRes);
        setLineage(lineageRes);
        setValidations(valRes || []);
        setFailures(failRes || []);
      } catch (err) {
        if (active) console.error("Failed to load audit details:", err);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadDetails();
    return () => {
      active = false;
    };
  }, [selectedId]);

  async function handleTriggerCalibration() {
    if (!selectedId) return;
    setCalibrating(true);
    try {
      const res = await requestJson<QualityCalibrationAuditView>(
        `/research/investigations/${selectedId}/quality/calibrate`,
        { method: "POST" }
      );
      setAudit(res);
      // Reload validations and failures
      const [valRes, failRes, lineageRes] = await Promise.all([
        requestJson<EvidenceClaimValidation[]>(
          `/research/investigations/${selectedId}/quality/validations`
        ),
        requestJson<ProviderFailureImpact[]>(
          `/research/investigations/${selectedId}/quality/failures`
        ),
        requestJson<SourceLineageOverviewResponse>(
          `/research/investigations/${selectedId}/quality/lineage`
        ),
      ]);
      setValidations(valRes || []);
      setFailures(failRes || []);
      setLineage(lineageRes);
    } catch (err) {
      console.error("Calibration error:", err);
    } finally {
      setCalibrating(false);
    }
  }

  const filteredValidations = useMemo(() => {
    if (entailmentFilter === "all") return validations;
    return validations.filter((v) => v.entailment_classification === entailmentFilter);
  }, [validations, entailmentFilter]);

  const tierColor = (tier: string) => {
    switch ((tier || "").toLowerCase()) {
      case "very strong":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "strong":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
      case "moderate":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "weak":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      default:
        return "bg-slate-700/40 text-slate-300 border-slate-600/40";
    }
  };

  const severityBadge = (sev: string) => {
    switch (sev) {
      case "critical_loss":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      case "significant_coverage":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "partial_coverage":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500/40";
      default:
        return "bg-slate-700/30 text-slate-400 border-slate-600/30";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-xl">🔬</span> Scientific Quality Audit & Calibration
            </h1>
            <span className="rounded-full bg-cyan-500/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-400 border border-cyan-500/20">
              Milestone 8G
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Audited evidence-strength ratings, verified peer-review separation, publication lineage clustering, and logical entailment matrix.
          </p>
        </div>

        {/* Investigation Selector & Calibrate Trigger */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="rounded-lg bg-surface border border-border px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500 max-w-xs"
          >
            {investigations.map((inv) => (
              <option key={inv.investigation_id} value={inv.investigation_id}>
                {inv.question.length > 45 ? `${inv.question.slice(0, 45)}...` : inv.question} ({inv.calibrated_tier})
              </option>
            ))}
          </select>

          <button
            onClick={handleTriggerCalibration}
            disabled={calibrating || !selectedId}
            className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {calibrating ? "Calibrating..." : "⚡ Recalibrate"}
          </button>

          {selectedId && (
            <Link
              href={`/investigations/${selectedId}`}
              className="rounded-lg bg-surface border border-border px-3 py-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              Open Investigation →
            </Link>
          )}
        </div>
      </div>

      {/* Decoupled Scientific Dimensions Banner (Milestone 9.2) */}
      {audit && (
        <div className="rounded-xl border border-border/80 bg-surface/60 p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span>⚖️</span> Three Decoupled Quality Dimensions
            </h2>
            <span className="text-xs text-slate-400">
              Operational completion and question coverage are strictly separated from evidence strength
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
            {/* Dimension A: Operational Completeness */}
            <div className="rounded-lg bg-surface-muted/60 border border-border/60 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Dimension A: Operational Completeness</span>
                <span className="text-xs text-slate-400">Execution</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {(audit.operational_completeness ?? Math.max(0, 100 - audit.failure_penalty * 2.5)).toFixed(1)}%
                </span>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                Execution of planned search, retrieval, and analysis actions (penalized for provider dropouts).
              </p>
            </div>

            {/* Dimension B: Research Coverage */}
            <div className="rounded-lg bg-surface-muted/60 border border-border/60 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-300">Dimension B: Research Coverage</span>
                <span className="text-xs text-slate-400">Breadth</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-cyan-400">
                  {(audit.research_coverage ?? audit.coverage_score).toFixed(1)}%
                </span>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                Coverage of atomic research claims and full-text document acquisition rate.
              </p>
            </div>

            {/* Dimension C: Evidence Strength */}
            <div className="rounded-lg bg-surface-muted/60 border border-border/60 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-indigo-300">Dimension C: Evidence Strength</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold border ${tierColor(audit.calibrated_tier)}`}>
                  {audit.calibrated_tier}
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {(audit.evidence_strength ?? audit.calibrated_score).toFixed(1)}
                </span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                Direct empirical proof, verified peer review, and true publication independence.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      {audit && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Calibrated Tier */}
          <div className="rounded-xl bg-surface border border-border p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-400">Calibrated Quality Tier</div>
            <div className="mt-2 flex items-center gap-2">
              <span className={`inline-block px-3 py-1 rounded-md text-sm font-bold border ${tierColor(audit.calibrated_tier)}`}>
                {audit.calibrated_tier}
              </span>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Evaluated against scientific benchmarks
            </div>
          </div>

          {/* Calibrated vs Raw Score */}
          <div className="rounded-xl bg-surface border border-border p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-400">Calibrated Score</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-white">{audit.calibrated_score.toFixed(1)}</span>
              <span className="text-sm text-slate-400">/ 100</span>
              {audit.failure_penalty > 0 && (
                <span className="text-xs font-semibold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                  -{audit.failure_penalty.toFixed(1)}
                </span>
              )}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Raw 5D Score: {audit.raw_score.toFixed(1)}/100
            </div>
          </div>

          {/* Research Coverage */}
          <div className="rounded-xl bg-surface border border-border p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-400">Research Coverage</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-cyan-400">{audit.coverage_score.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2">
              <div
                className="bg-cyan-500 h-1.5 rounded-full"
                style={{ width: `${Math.min(100, audit.coverage_score)}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {audit.coverage_score < 70 ? "Coverage caps tier to Moderate" : "Adequate coverage threshold"}
            </div>
          </div>

          {/* Verified Peer-Reviewed */}
          <div className="rounded-xl bg-surface border border-border p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-400">Verified Peer-Reviewed</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-indigo-400">{audit.verified_peer_reviewed_count}</span>
              <span className="text-sm text-slate-400">/ {audit.total_sources} sources</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {audit.verified_peer_reviewed_count === 0 ? "⚠️ Preprints/trade press only" : "Indexed journal verified"}
            </div>
          </div>

          {/* True Independence Ratio */}
          <div className="rounded-xl bg-surface border border-border p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-400">Effective Lineage Clusters</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-emerald-400">
                {lineage ? lineage.effective_independent_count : audit.total_sources}
              </span>
              <span className="text-sm text-slate-400">
                ({lineage ? `${(lineage.independence_ratio * 100).toFixed(0)}%` : "100%"})
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Collapsed from syndication & copies
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-border/60 flex gap-2">
        <button
          onClick={() => setActiveTab("dimensions")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "dimensions"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          📊 5-Dimension Calibration ({audit ? audit.calibrated_score.toFixed(0) : 0}/100)
        </button>
        <button
          onClick={() => setActiveTab("lineage")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "lineage"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          🌐 Source Lineage & Syndication ({lineage ? lineage.clusters.length : 0})
        </button>
        <button
          onClick={() => setActiveTab("entailment")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "entailment"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          ⚖️ Evidence Entailment Matrix ({validations.length})
        </button>
        <button
          onClick={() => setActiveTab("failures")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "failures"
              ? "border-cyan-500 text-cyan-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          ⚠️ Retrieval Failure Impact ({failures.length})
        </button>
      </div>

      {/* Tab 1: Dimensions Breakdown */}
      {activeTab === "dimensions" && audit && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Dimensions Chart / Bars */}
            <div className="rounded-xl bg-surface border border-border p-5 space-y-4">
              <h3 className="text-base font-semibold text-white">Calibrated 5D Evidence Evaluation</h3>
              <p className="text-xs text-slate-400">
                Each dimension is evaluated with empirical thresholds and penalized for syndication, correlational conflation, and retrieval dropouts.
              </p>

              <div className="space-y-3.5 pt-2">
                {[
                  { label: "Empirical Depth", key: "empirical_depth", max: 25, color: "bg-blue-500" },
                  { label: "Source Credibility", key: "source_credibility", max: 25, color: "bg-indigo-500" },
                  { label: "Source Independence", key: "source_independence", max: 20, color: "bg-emerald-500" },
                  { label: "Methodological Rigor", key: "methodological_rigor", max: 15, color: "bg-cyan-500" },
                  { label: "Consensus Stability", key: "consensus_stability", max: 15, color: "bg-purple-500" },
                ].map((dim) => {
                  const val = audit.dimension_breakdown[dim.key] || 0;
                  const pct = Math.min(100, (val / dim.max) * 100);
                  return (
                    <div key={dim.key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-slate-300">{dim.label}</span>
                        <span className="text-slate-400">
                          {val.toFixed(1)} / {dim.max} pts ({pct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2">
                        <div className={`${dim.color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Empirical Proof Breakdown (Milestone 9.2) */}
              {audit.dimension_breakdown && (
                <div className="mt-4 pt-3 border-t border-border/40 space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Empirical Entailment Distribution
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    <div className="p-2 rounded bg-surface-muted/40 border border-border/40">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">Direct Proof</div>
                      <div className="text-base font-bold text-emerald-400 mt-0.5">
                        {audit.dimension_breakdown.direct_support_count ?? 0}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-surface-muted/40 border border-border/40">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">Partial Mechanism</div>
                      <div className="text-base font-bold text-cyan-400 mt-0.5">
                        {audit.dimension_breakdown.partial_support_count ?? 0}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-surface-muted/40 border border-border/40">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">Contextual</div>
                      <div className="text-base font-bold text-amber-400 mt-0.5">
                        {audit.dimension_breakdown.contextual_count ?? 0}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-surface-muted/40 border border-border/40">
                      <div className="text-[10px] text-slate-400 uppercase font-medium">Contradictions</div>
                      <div className="text-base font-bold text-rose-400 mt-0.5">
                        {audit.dimension_breakdown.contradiction_count ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {audit.failure_penalty > 0 && (
                <div className="mt-4 pt-3 border-t border-border/40 flex justify-between items-center text-xs">
                  <span className="text-rose-400 font-medium">Provider Failure Penalty:</span>
                  <span className="text-rose-400 font-bold">-{audit.failure_penalty.toFixed(1)} pts</span>
                </div>
              )}
            </div>

            {/* Calibration Reasons & Adjustments */}
            <div className="rounded-xl bg-surface border border-border p-5 space-y-4">
              <h3 className="text-base font-semibold text-white">Calibration Explanations & Rationale</h3>
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {audit.calibration_reasons.map((reason, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-surface-muted/50 border border-border/50 text-xs text-slate-300 flex items-start gap-2.5"
                  >
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <span>{reason}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Lineage Explorer */}
      {activeTab === "lineage" && lineage && (
        <div className="space-y-6">
          <div className="rounded-xl bg-surface border border-border p-5">
            <h3 className="text-base font-semibold text-white mb-2">Lineage Summary</h3>
            <p className="text-sm text-slate-300 mb-4">{lineage.lineage_summary}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3 rounded-lg bg-surface-muted border border-border/40">
                <div className="text-xs text-slate-400">Total Sources Analyzed</div>
                <div className="text-xl font-bold text-white mt-1">{lineage.total_sources}</div>
              </div>
              <div className="p-3 rounded-lg bg-surface-muted border border-border/40">
                <div className="text-xs text-slate-400">Effective Independent Clusters</div>
                <div className="text-xl font-bold text-emerald-400 mt-1">{lineage.effective_independent_count}</div>
              </div>
              <div className="p-3 rounded-lg bg-surface-muted border border-border/40">
                <div className="text-xs text-slate-400">True Independence Ratio</div>
                <div className="text-xl font-bold text-cyan-400 mt-1">{(lineage.independence_ratio * 100).toFixed(1)}%</div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-base font-semibold text-white">Lineage Clusters ({lineage.clusters.length})</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {lineage.clusters.map((cluster) => (
                <div key={cluster.cluster_id} className="rounded-xl bg-surface border border-border p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-white">{cluster.cluster_name}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {cluster.member_source_ids.length} source(s)
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{cluster.explanation}</p>
                  <div className="text-xs text-slate-500 pt-1">
                    Relationship: <span className="text-slate-300">{cluster.relationship_type.replace(/_/g, " ")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Entailment Matrix */}
      {activeTab === "entailment" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Filter Classification:</span>
              <select
                value={entailmentFilter}
                onChange={(e) => setEntailmentFilter(e.target.value)}
                className="rounded-lg bg-surface border border-border px-2.5 py-1 text-xs text-white"
              >
                <option value="all">All Classifications ({validations.length})</option>
                <option value="direct_support">Direct Support</option>
                <option value="contextual_support">Contextual Support</option>
                <option value="direct_contradiction">Direct Contradiction</option>
                <option value="mitigating">Mitigating</option>
                <option value="methodological_limitation">Methodological Limitation</option>
                <option value="insufficient_evidence">Insufficient Evidence</option>
              </select>
            </div>
            <span className="text-xs text-slate-400">Showing {filteredValidations.length} validation(s)</span>
          </div>

          <div className="space-y-3">
            {filteredValidations.map((val) => (
              <div
                key={val.id}
                className={`rounded-xl bg-surface border p-4 space-y-3 ${
                  val.correlation_vs_causation_flag
                    ? "border-amber-500/40 bg-amber-500/5"
                    : val.entailment_classification === "direct_support"
                    ? "border-emerald-500/30"
                    : "border-border"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                        val.entailment_classification === "direct_support"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                          : val.entailment_classification === "direct_contradiction"
                          ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                          : val.entailment_classification === "mitigating"
                          ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                          : "bg-slate-700/30 text-slate-300 border-slate-600/30"
                      }`}
                    >
                      {val.entailment_classification.replace(/_/g, " ").toUpperCase()}
                    </span>
                    {val.correlation_vs_causation_flag && (
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                        ⚠️ Correlation ≠ Causation
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-400">
                    Entailment Strength: {(val.entailment_strength * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Claim */}
                <div className="text-xs">
                  <span className="font-semibold text-slate-400">Claim:</span>{" "}
                  <span className="text-slate-200">{val.claim_text}</span>
                </div>

                {/* Evidence Passage */}
                <div className="p-2.5 rounded-lg bg-surface-muted/60 border border-border/40 text-xs text-slate-300 italic">
                  "{val.evidence_text}"
                </div>

                {/* Explanation */}
                <div className="text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Explanation:</span> {val.explanation}
                </div>

                {/* Missing inferential steps */}
                {val.missing_inferential_steps.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-amber-400">Missing Inferential Steps:</div>
                    <ul className="list-disc list-inside text-xs text-slate-400 space-y-0.5 pl-1">
                      {val.missing_inferential_steps.map((step, sIdx) => (
                        <li key={sIdx}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Provider Failures */}
      {activeTab === "failures" && (
        <div className="space-y-4">
          <div className="rounded-xl bg-surface border border-border p-4">
            <h3 className="text-base font-semibold text-white mb-1">Provider Retrieval Impact Log</h3>
            <p className="text-xs text-slate-400">
              Provider timeouts, rate limits, and errors are assessed for evidentiary impact. Critical failures penalize the calibrated score and cap maximum achievable tiers.
            </p>
          </div>

          {failures.length === 0 ? (
            <div className="rounded-xl bg-surface border border-border p-8 text-center text-slate-400 text-sm">
              ✅ No provider failures recorded for this investigation. All retrieval operations succeeded cleanly.
            </div>
          ) : (
            <div className="space-y-3">
              {failures.map((f) => (
                <div key={f.id} className="rounded-xl bg-surface border border-border p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{f.provider}</span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${severityBadge(f.impact_severity)}`}>
                        {f.impact_severity.replace(/_/g, " ").toUpperCase()}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400">{f.failure_type}</span>
                  </div>
                  <div className="text-xs text-slate-300">
                    <span className="font-semibold text-slate-400">Query:</span> {f.query}
                  </div>
                  <div className="text-xs text-slate-400">{f.explanation}</div>
                  {f.missing_category && (
                    <div className="text-xs text-rose-400">
                      Missing Category: <span className="font-semibold">{f.missing_category}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
