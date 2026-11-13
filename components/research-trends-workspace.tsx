"use client";

import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";

export type ResearchTrendTopicView = {
  id: string;
  analysis_id: string;
  topic_name: string;
  classification: string;
  activity_score: number;
  quality_score: number;
  independence_score: number;
  growth_rate: number;
  contradiction_count: number;
  gap_count: number;
  temporal_observations_count: number;
  investigation_ids: string[];
  source_ids: string[];
  summary_narrative: string;
  created_at?: string | null;
};

export type ResearchTrendAnalysisResponse = {
  id: string;
  title: string;
  summary: string;
  total_investigations_analyzed: number;
  total_sources_analyzed: number;
  total_evidence_analyzed: number;
  temporal_span_start?: string | null;
  temporal_span_end?: string | null;
  topics: ResearchTrendTopicView[];
  emerging_themes: { topic: string; growth_rate: string; description: string }[];
  consensus_shifts: { topic: string; description: string; recent_growth?: string }[];
  persistent_gaps: { topic: string; description: string }[];
  active_contradictions_count: number;
  recommendations: { priority: string; action: string; target_topics: string[] }[];
  created_at?: string | null;
};

const CLASSIFICATION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  emerging_topic: { bg: "rgba(59, 130, 246, 0.15)", text: "#3b82f6", label: "Emerging Topic" },
  growing_activity: { bg: "rgba(16, 185, 129, 0.15)", text: "#10b981", label: "Growing Activity" },
  stable_topic: { bg: "rgba(148, 163, 184, 0.15)", text: "#94a3b8", label: "Stable Consensus" },
  changing_consensus: { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444", label: "Shifting Consensus" },
  persistent_gap: { bg: "rgba(245, 158, 11, 0.15)", text: "#f59e0b", label: "Persistent Gap" },
  insufficient_historical_data: { bg: "rgba(168, 85, 247, 0.15)", text: "#a855f7", label: "Early Stage Data" },
};

export function ResearchTrendsWorkspace() {
  const [trendAnalysis, setTrendAnalysis] = useState<ResearchTrendAnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadLatest = async () => {
    setLoading(true);
    try {
      const data = await requestJson<ResearchTrendAnalysisResponse>("/research/trends/latest");
      setTrendAnalysis(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load trend analysis.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLatest();
  }, []);

  const handleRunAnalysis = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const resp = await requestJson<ResearchTrendAnalysisResponse>("/research/trends/analyze", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setTrendAnalysis(resp);
    } catch (err: any) {
      setError(err?.message || "Trend analysis execution failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="trends-workspace" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Banner */}
      <div className="panel" style={{ padding: "18px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>Research Trend Intelligence</h2>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "12px", background: "rgba(234, 179, 8, 0.15)", color: "#eab308" }}>
              Milestone 8E
            </span>
          </div>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: "13px" }}>
            Longitudinal distribution analysis, topic velocity tracking, and emerging research paradigm shifts.
          </p>
        </div>

        <button className="button primary" disabled={analyzing} onClick={handleRunAnalysis}>
          {analyzing ? "Synthesizing Longitudinal Trends..." : "Run Trend Analysis"}
        </button>
      </div>

      {error && (
        <div className="panel error-banner" style={{ padding: "12px 18px", color: "#ef4444" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {loading ? (
        <div className="panel empty-state">
          <p className="muted">Analyzing temporal evidence corpus...</p>
        </div>
      ) : !trendAnalysis ? (
        <div className="panel empty-state" style={{ padding: "40px", textAlign: "center" }}>
          <p className="muted" style={{ fontSize: "14px", marginBottom: "12px" }}>
            No trend intelligence reports available. Click below to initiate longitudinal analysis.
          </p>
          <button className="button primary" onClick={handleRunAnalysis}>
            Execute Trend Analysis
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Overview Metrics Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
            <div className="panel" style={{ padding: "14px 18px" }}>
              <div className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>
                Studies Analyzed
              </div>
              <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#06b6d4" }}>
                {trendAnalysis.total_investigations_analyzed}
              </div>
            </div>

            <div className="panel" style={{ padding: "14px 18px" }}>
              <div className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>
                Sources & Citations
              </div>
              <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#3b82f6" }}>
                {trendAnalysis.total_sources_analyzed}
              </div>
            </div>

            <div className="panel" style={{ padding: "14px 18px" }}>
              <div className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>
                Temporal Horizon
              </div>
              <div style={{ fontSize: "1.3rem", fontWeight: 700, marginTop: "6px", color: "#eab308" }}>
                {trendAnalysis.temporal_span_start || "Early"} – {trendAnalysis.temporal_span_end || "Present"}
              </div>
            </div>

            <div className="panel" style={{ padding: "14px 18px" }}>
              <div className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>
                Active Contradictions
              </div>
              <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#ef4444" }}>
                {trendAnalysis.active_contradictions_count}
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="panel" style={{ padding: "18px 22px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 8px" }}>Longitudinal Analysis Summary</h3>
            <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.6, color: "#e2e8f0" }}>{trendAnalysis.summary}</p>
          </div>

          {/* Emerging Themes & Consensus Shifts */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {/* Emerging Themes */}
            <div className="panel" style={{ padding: "18px 20px" }}>
              <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase", margin: "0 0 12px" }}>
                🚀 Emerging Themes ({trendAnalysis.emerging_themes.length})
              </h4>
              {trendAnalysis.emerging_themes.length === 0 ? (
                <p className="muted" style={{ fontSize: "12.5px" }}>No rapid-growth themes identified yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {trendAnalysis.emerging_themes.map((th, idx) => (
                    <div key={idx} style={{ padding: "10px 14px", background: "rgba(59, 130, 246, 0.05)", borderLeft: "3px solid #3b82f6", borderRadius: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "13px", color: "#93c5fd" }}>{th.topic}</strong>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#60a5fa" }}>{th.growth_rate}</span>
                      </div>
                      <div className="muted" style={{ fontSize: "12px", marginTop: "3px" }}>{th.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Consensus Shifts */}
            <div className="panel" style={{ padding: "18px 20px" }}>
              <h4 style={{ fontSize: "13px", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", margin: "0 0 12px" }}>
                ⚡ Consensus Shifts & Tensions ({trendAnalysis.consensus_shifts.length})
              </h4>
              {trendAnalysis.consensus_shifts.length === 0 ? (
                <p className="muted" style={{ fontSize: "12.5px" }}>No major paradigm disagreements currently observed.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {trendAnalysis.consensus_shifts.map((cs, idx) => (
                    <div key={idx} style={{ padding: "10px 14px", background: "rgba(239, 68, 68, 0.05)", borderLeft: "3px solid #ef4444", borderRadius: "4px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 700, color: "#fca5a5" }}>{cs.topic}</div>
                      <div className="muted" style={{ fontSize: "12px", marginTop: "3px" }}>{cs.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Research Topic Clusters */}
          <div className="panel" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 16px" }}>
              Research Topics & Longitudinal Trajectories ({trendAnalysis.topics.length})
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "14px" }}>
              {trendAnalysis.topics.map((t) => {
                const badge = CLASSIFICATION_STYLES[t.classification] || { bg: "rgba(255,255,255,0.05)", text: "#cbd5e1", label: t.classification };
                return (
                  <div
                    key={t.id}
                    style={{
                      padding: "16px",
                      borderRadius: "6px",
                      border: "1px solid var(--border)",
                      background: "rgba(255,255,255,0.015)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                      <h4 style={{ fontSize: "14px", fontWeight: 700, margin: 0 }}>{t.topic_name}</h4>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: badge.bg,
                          color: badge.text,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {badge.label}
                      </span>
                    </div>

                    <p style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5, color: "#cbd5e1" }}>
                      {t.summary_narrative}
                    </p>

                    {/* Scores row */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "8px" }}>
                      <div>
                        <div className="muted" style={{ fontSize: "10px", textTransform: "uppercase" }}>Activity</div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "#3b82f6" }}>{t.activity_score.toFixed(0)} / 100</div>
                      </div>
                      <div>
                        <div className="muted" style={{ fontSize: "10px", textTransform: "uppercase" }}>Quality</div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "#10b981" }}>{t.quality_score.toFixed(0)} / 100</div>
                      </div>
                      <div>
                        <div className="muted" style={{ fontSize: "10px", textTransform: "uppercase" }}>Growth</div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: t.growth_rate >= 0 ? "#6ee7b7" : "#f87171" }}>
                          {t.growth_rate > 0 ? `+${t.growth_rate}%` : `${t.growth_rate}%`}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Strategic Action Recommendations */}
          {trendAnalysis.recommendations.length > 0 && (
            <div className="panel" style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, margin: "0 0 12px", color: "#eab308" }}>
                Strategic Longitudinal Research Recommendations
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {trendAnalysis.recommendations.map((rec, idx) => (
                  <div key={idx} style={{ padding: "10px 14px", background: "rgba(234, 179, 8, 0.05)", borderLeft: "3px solid #eab308", borderRadius: "4px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", padding: "1px 6px", borderRadius: "3px", background: "rgba(234,179,8,0.2)", color: "#facc15" }}>
                        {rec.priority} Priority
                      </span>
                      <strong style={{ fontSize: "13px" }}>{rec.action}</strong>
                    </div>
                    {rec.target_topics && rec.target_topics.length > 0 && (
                      <div className="muted" style={{ fontSize: "11px", marginTop: "4px" }}>
                        Relevant Topics: {rec.target_topics.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
