"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { requestJson } from "@/lib/api";
import {
  SpotlightCard,
  AnimatedCounter,
  PulseIndicator,
  DecryptedText,
  RevealSection,
} from "@/components/motion";

export type UnifiedIntelligenceOverview = {
  total_investigations: number;
  connected_investigations: number;
  total_claims: number;
  total_evidence: number;
  total_sources: number;
  total_gaps: number;
  total_hypotheses: number;
  active_contradictions: number;
  resolved_contradictions: number;
  total_cross_relationships: number;
  active_trends_count: number;
  system_status: string;
  last_updated?: string | null;
};

export type GlobalResearchSearchResultItem = {
  id: string;
  entity_type: string;
  title: string;
  snippet: string;
  investigation_id?: string | null;
  investigation_question?: string | null;
  severity_or_status?: string | null;
  score?: number | null;
  created_at?: string | null;
};

export type GlobalResearchSearchResponse = {
  items: GlobalResearchSearchResultItem[];
  total: number;
  query: string;
};

const ENTITY_ICONS: Record<string, string> = {
  investigation: "🔍",
  claim: "📌",
  evidence: "📄",
  source: "📚",
  hypothesis: "🔬",
  gap: "⚠️",
  contradiction: "⚖️",
  topic: "📈",
};

const ENTITY_COLORS: Record<string, string> = {
  investigation: "#3b82f6",
  claim: "#10b981",
  evidence: "#64748b",
  source: "#06b6d4",
  hypothesis: "#a855f7",
  gap: "#f59e0b",
  contradiction: "#ef4444",
  topic: "#eab308",
};

export function UnifiedIntelligenceWorkspace() {
  const [overview, setOverview] = useState<UnifiedIntelligenceOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchCategory, setSearchCategory] = useState<string>("all");
  const [searchResults, setSearchResults] = useState<GlobalResearchSearchResultItem[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    setLoadingOverview(true);
    try {
      const data = await requestJson<UnifiedIntelligenceOverview>("/research/intelligence/overview");
      setOverview(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load intelligence overview.");
    } finally {
      setLoadingOverview(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSearching(true);
    setError(null);
    try {
      const resp = await requestJson<GlobalResearchSearchResponse>(
        `/research/intelligence/search?query=${encodeURIComponent(searchQuery)}&category=${searchCategory}`
      );
      setSearchResults(resp.items || []);
    } catch (err: any) {
      setError(err?.message || "Search failed.");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="unified-intelligence-workspace" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner */}
      <div className="panel compact" style={{ padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, margin: 0, color: "#f8fafc" }}>Research Intelligence Hub</h2>
            <span style={{ fontSize: "10px", fontWeight: 700, padding: "2px 8px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.15)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
              SYNTHESIS INTELLIGENCE
            </span>
          </div>
          <p className="muted" style={{ margin: "3px 0 0", fontSize: "12px" }}>
            Neural Evidence Orchestration & Multi-Agent Observation Network — interconnected multi-study intelligence.
          </p>
        </div>

        <button className="outline-button compact-button" onClick={loadOverview} disabled={loadingOverview} style={{ padding: "6px 14px", fontSize: "12px" }}>
          Refresh Metrics
        </button>
      </div>

      {error && (
        <div className="panel error-banner" style={{ padding: "12px 18px", color: "#ef4444" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Overview Metrics Cards with Spotlight & Counter */}
      {overview && (
        <RevealSection delay={0.08}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px" }}>
            <Link href="/gaps" style={{ textDecoration: "none", color: "inherit" }}>
              <SpotlightCard spotlightColor="rgba(255, 181, 71, 0.15)" style={{ padding: "16px 20px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>Research Gaps</span>
                  <span>⚠️</span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, marginTop: "4px", color: "#FFB547" }}>
                  <AnimatedCounter value={overview.total_gaps} />
                </div>
                <div className="muted" style={{ fontSize: "11px", marginTop: "2px", color: "#38bdf8" }}>8A Discovery Engine →</div>
              </SpotlightCard>
            </Link>

            <Link href="/hypotheses" style={{ textDecoration: "none", color: "inherit" }}>
              <SpotlightCard spotlightColor="rgba(133, 100, 255, 0.15)" style={{ padding: "16px 20px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>Hypotheses</span>
                  <span>🔬</span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, marginTop: "4px", color: "#8564FF" }}>
                  <AnimatedCounter value={overview.total_hypotheses} />
                </div>
                <div className="muted" style={{ fontSize: "11px", marginTop: "2px", color: "#38bdf8" }}>8B Testable Formulations →</div>
              </SpotlightCard>
            </Link>

            <Link href="/synthesis" style={{ textDecoration: "none", color: "inherit" }}>
              <SpotlightCard spotlightColor="rgba(37, 217, 242, 0.15)" style={{ padding: "16px 20px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>Cross-Study Links</span>
                  <span>🔗</span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, marginTop: "4px", color: "#25D9F2" }}>
                  <AnimatedCounter value={overview.total_cross_relationships} />
                </div>
                <div className="muted" style={{ fontSize: "11px", marginTop: "2px", color: "#38bdf8" }}>8C Knowledge Synthesis →</div>
              </SpotlightCard>
            </Link>

            <Link href="/contradictions" style={{ textDecoration: "none", color: "inherit" }}>
              <SpotlightCard spotlightColor="rgba(255, 82, 119, 0.15)" style={{ padding: "16px 20px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>Contradictions</span>
                  <span>⚖️</span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, marginTop: "4px", color: "#FF5277" }}>
                  <AnimatedCounter value={overview.active_contradictions} />
                </div>
                <div className="muted" style={{ fontSize: "11px", marginTop: "2px", color: "#38bdf8" }}>8D Empirical Tensions →</div>
              </SpotlightCard>
            </Link>

            <Link href="/trends" style={{ textDecoration: "none", color: "inherit" }}>
              <SpotlightCard spotlightColor="rgba(53, 224, 177, 0.15)" style={{ padding: "16px 20px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="muted" style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>Trend Topics</span>
                  <span>📈</span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, marginTop: "4px", color: "#35E0B1" }}>
                  <AnimatedCounter value={overview.active_trends_count} />
                </div>
                <div className="muted" style={{ fontSize: "11px", marginTop: "2px", color: "#38bdf8" }}>8E Temporal Intelligence →</div>
              </SpotlightCard>
            </Link>
          </div>
        </RevealSection>
      )}

      {/* Global Multi-Entity Research Search Engine */}
      <div className="panel" style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 4px" }}>Universal Research Search</h3>
          <p className="muted" style={{ margin: 0, fontSize: "13px" }}>
            Search across investigations, claims, empirical evidence, literature sources, hypotheses, gaps, and contradictions.
          </p>
        </div>

        <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
          <input
            type="text"
            className="text-input"
            placeholder="Search keywords, claims, concepts, or authors..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ flex: 1, minWidth: "260px", padding: "10px 14px", fontSize: "13.5px" }}
          />

          <select
            className="select-input"
            value={searchCategory}
            onChange={(e) => setSearchCategory(e.target.value)}
            style={{ padding: "10px 14px", fontSize: "13px" }}
          >
            <option value="all">All Entity Types</option>
            <option value="investigation">Investigations</option>
            <option value="claim">Claims</option>
            <option value="evidence">Evidence</option>
            <option value="source">Sources</option>
            <option value="hypothesis">Hypotheses</option>
            <option value="gap">Research Gaps</option>
            <option value="contradiction">Contradictions</option>
            <option value="topic">Trend Topics</option>
          </select>

          <button type="submit" className="button primary" disabled={searching} style={{ padding: "10px 18px" }}>
            {searching ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Search Results Display */}
        {searchResults.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}>
            <div className="muted" style={{ fontSize: "12px", fontWeight: 600 }}>
              Showing {searchResults.length} match(es) for "{searchQuery}":
            </div>
            {searchResults.map((item) => {
              const icon = ENTITY_ICONS[item.entity_type] || "📄";
              const color = ENTITY_COLORS[item.entity_type] || "#cbd5e1";
              return (
                <div
                  key={`${item.entity_type}-${item.id}`}
                  style={{
                    padding: "12px 16px",
                    borderRadius: "6px",
                    border: "1px solid var(--border)",
                    background: "rgba(255,255,255,0.015)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span>{icon}</span>
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          backgroundColor: `${color}22`,
                          color: color,
                        }}
                      >
                        {item.entity_type}
                      </span>
                      {item.severity_or_status && (
                        <span className="muted" style={{ fontSize: "11px" }}>
                          Status: {item.severity_or_status}
                        </span>
                      )}
                    </div>
                    {item.score !== undefined && item.score !== null && (
                      <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted)" }}>
                        Score: {item.score.toFixed(1)}
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: "13.5px", fontWeight: 600, marginTop: "2px" }}>{item.title}</div>
                  <div style={{ fontSize: "12.5px", color: "var(--muted)", lineHeight: 1.4 }}>{item.snippet}</div>

                  {item.investigation_question && (
                    <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
                      Study: <em>{item.investigation_question}</em>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Subsystem Direct Navigation Cards */}
      <div>
        <h3 style={{ fontSize: "1.15rem", fontWeight: 700, margin: "0 0 14px" }}>
          Research Intelligence Subsystems
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>⚠️</span>
              <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>8A: Autonomous Research Gap Discovery</h4>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5 }}>
              Detects unsupported claims, missing perspectives, methodological limitations, and high-priority inquiry directions.
            </p>
            <Link href="/gaps" className="button secondary" style={{ fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
              Open Research Gap Workspace →
            </Link>
          </div>

          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>🔬</span>
              <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>8B: Evidence-Grounded Hypotheses</h4>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5 }}>
              Formulates scientifically testable propositions with explicit falsification criteria, boundary conditions, and variables.
            </p>
            <Link href="/hypotheses" className="button secondary" style={{ fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
              Open Hypothesis Workspace →
            </Link>
          </div>

          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>🔗</span>
              <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>8C: Cross-Investigation Synthesis</h4>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5 }}>
              Synthesizes multi-study evidence, detects convergent & divergent claims, and discovers shared literature citations.
            </p>
            <Link href="/synthesis" className="button secondary" style={{ fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
              Open Cross-Study Synthesis →
            </Link>
          </div>

          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>⚖️</span>
              <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>8D: Contradiction Intelligence</h4>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5 }}>
              Preserves authentic empirical disagreement without forced consensus, tracking resolution lifecycles and scope distinctions.
            </p>
            <Link href="/contradictions" className="button secondary" style={{ fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
              Open Contradiction Workspace →
            </Link>
          </div>

          <div className="panel" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>📈</span>
              <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>8E: Research Trend Intelligence</h4>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.5 }}>
              Tracks longitudinal evidence timelines, topic velocity, emerging themes, and evolving scientific consensus shifts.
            </p>
            <Link href="/trends" className="button secondary" style={{ fontSize: "12px", marginTop: "8px", textAlign: "center" }}>
              Open Trend Intelligence →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
