"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, requestJson } from "@/lib/api";
import { NeuralParticleCanvas, AtmosphericAurora } from "@/components/animated-neural-background";
import {
  SpotlightCard,
  AnimatedCounter,
  DecryptedText,
  PulseIndicator,
  RevealSection,
} from "@/components/motion";

type InvestigationItem = {
  id: string;
  question: string;
  mode: string;
  status: string;
  created_at?: string;
  source_count: number;
  evidence_count: number;
  quality_status: string;
  relevant_source_count: number;
  full_text_count: number;
};

type AgentItem = {
  identifier: string;
  name: string;
  description: string;
  status: string;
  demo_mode: boolean;
};

export default function Home() {
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isUnauthenticated, setIsUnauthenticated] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [loadedInvestigations, loadedAgents] = await Promise.all([
          requestJson<InvestigationItem[]>("/research/investigations"),
          requestJson<AgentItem[]>("/agents"),
        ]);
        if (active) {
          setInvestigations(loadedInvestigations);
          setAgents(loadedAgents);
          setError("");
          setIsUnauthenticated(false);
        }
      } catch (reason) {
        if (active) {
          if (reason instanceof ApiError && reason.status === 401) {
            setIsUnauthenticated(true);
            setInvestigations([]);
            setAgents([]);
            setError("");
          } else {
            setError(reason instanceof Error ? reason.message : "Could not load dashboard data.");
          }
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const totalSources = investigations.reduce((sum, item) => sum + item.source_count, 0);
  const totalEvidence = investigations.reduce((sum, item) => sum + item.evidence_count, 0);
  const totalFullText = investigations.reduce((sum, item) => sum + item.full_text_count, 0);
  const verifiedCount = investigations.filter((item) => item.quality_status === "verified" || item.quality_status === "strong").length;
  const recentInvestigations = investigations.slice(0, 6);

  const metrics = [
    {
      label: "Autonomous Investigations",
      value: loading ? "…" : String(investigations.length),
      detail: investigations.length === 0 ? "Awaiting initial run" : `${investigations.length} persisted research missions`,
      icon: "🔬",
      accent: "#38bdf8",
      tag: "CORPUS::RUNS",
    },
    {
      label: "Traceable Passages",
      value: loading ? "…" : String(totalEvidence),
      detail: totalEvidence === 0 ? "Awaiting first run" : `${totalEvidence} verified dialectical extracts`,
      icon: "⚡",
      accent: "#06b6d4",
      tag: "EVIDENCE::SYNAPSE",
    },
    {
      label: "Literature Ingested",
      value: loading ? "…" : String(totalSources),
      detail: totalSources === 0 ? "No sources retrieved yet" : `${totalFullText} full-text documents linked`,
      icon: "📚",
      accent: "#818cf8",
      tag: "SOURCE::INGESTION",
    },
    {
      label: "Scientific Quality Tiers",
      value: loading ? "…" : `${verifiedCount} / ${investigations.length}`,
      detail: verifiedCount === investigations.length && investigations.length > 0 ? "100% verified & calibrated" : "Calibrated across quality criteria",
      icon: "🛡️",
      accent: "#10b981",
      tag: "QUALITY::AUDIT",
    },
  ];

  return (
    <>
      <header className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div>
            <p className="eyebrow" style={{ display: "flex", alignItems: "center", gap: "8px", margin: "0 0 4px" }}>
              <PulseIndicator status="active" />
              <DecryptedText text="COMMAND CENTER // ONLINE" speed={30} />
            </p>
            <h1 style={{ display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/neomon-symbol.png"
                alt="NEOMON"
                width={26}
                height={26}
                style={{ objectFit: "contain", filter: "drop-shadow(0 0 8px rgba(37, 217, 242, 0.6))" }}
              />
              Research Intelligence Network
            </h1>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link className="outline-button compact-button" href="/graph">
            ⌘ Knowledge Graph
          </Link>
          <Link className="cyber-primary-btn" href="/investigations/new">
            <span>+ Launch Investigation</span>
            <span>→</span>
          </Link>
        </div>
      </header>

      <div className="content">
        {/* Cyber Hero Stage with Real Canvas Neural Network Background */}
        <section className="hero-cyber-card">
          {/* Animated Background Canvas & Aurora */}
          <NeuralParticleCanvas density="medium" interactive={true} />
          <AtmosphericAurora showGrid={false} showScanlines={true} />

          {/* Technical Corner Accents */}
          <div className="hud-corner-tl" />
          <div className="hud-corner-tr" />
          <div className="hud-corner-bl" />
          <div className="hud-corner-br" />

          {/* Hero Foreground Content */}
          <div className="hero-cyber-content">
            <div className="hero-telemetry-ribbon">
              <span className="telemetry-beacon" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/brand/neomon-symbol.png"
                  alt="NEOMON"
                  width={16}
                  height={16}
                  style={{ objectFit: "contain", filter: "drop-shadow(0 0 6px rgba(54, 197, 222, 0.6))" }}
                />
                <span className="telemetry-dot" />
                NEOMON // v1.0-GA
              </span>
              <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "monospace" }}>
                GRID::ACTIVE [24.12.98]
              </span>
              <span style={{ fontSize: "11px", color: "#38bdf8", fontFamily: "monospace" }}>
                AGENTS::17 ROSTER
              </span>
            </div>

            <h2 className="hero-cyber-title">
              Research beyond <span>the surface.</span>
            </h2>

            <p className="hero-cyber-copy">
              Autonomous multi-agent research intelligence across peer-reviewed repositories,
              preprints, and scientific literature. Extract traceable evidence passages, expose
              contradictions, and synthesize calibrated conclusions.
            </p>

            <div className="hero-cyber-actions">
              <Link className="cyber-primary-btn" href="/investigations/new">
                <span>+ Launch Autonomous Mission</span>
                <span>→</span>
              </Link>
              <Link className="outline-button" href="/autonomous">
                ⚡ Autonomous Research Suite
              </Link>
              <Link className="outline-button" href="/graph">
                ⌘ Interactive Graph Explorer
              </Link>
            </div>
          </div>
        </section>

        {isUnauthenticated ? (
          <section className="hud-card" style={{ marginBottom: "24px", padding: "20px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div className="hud-corner-tl" />
            <div className="hud-corner-tr" />
            <div className="hud-corner-bl" />
            <div className="hud-corner-br" />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ color: "#f59e0b" }}>⚠️</span>
                <h4 style={{ margin: 0, color: "#f8fafc", fontSize: "15px", fontWeight: 700 }}>
                  Guest Intelligence Session
                </h4>
              </div>
              <p style={{ margin: 0, color: "#94a3b8", fontSize: "13px" }}>
                Authenticate with an authorized research account to create multi-user workspaces, execute multi-agent debates, and export calibrated intelligence dossiers.
              </p>
            </div>
            <Link className="cyber-primary-btn" href="/login" style={{ padding: "8px 18px", fontSize: "12px", whiteSpace: "nowrap" }}>
              Sign In to Command Center →
            </Link>
          </section>
        ) : error ? (
          <p className="connection-result error dashboard-error">{error}</p>
        ) : null}

        {/* Section Divider & Transition */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "16px", marginTop: "28px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <p className="eyebrow blue" style={{ margin: "0 0 4px" }}>TELEMETRY & VERIFIED CORPUS</p>
            <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 700, color: "#f8fafc" }}>
              Research Intelligence Operations
            </h3>
          </div>
          <span style={{ fontSize: "11px", color: "#38bdf8", fontFamily: "monospace", background: "rgba(56, 189, 248, 0.08)", padding: "3px 8px", borderRadius: "4px", border: "1px solid rgba(56, 189, 248, 0.2)" }}>
            LIVE_DATA::SYNCHRONIZED
          </span>
        </div>

        {/* 4 HUD Metric Tiles with Cursor-Tracked Spotlight & Spring Counters */}
        <RevealSection delay={0.1}>
          <section className="metric-grid" aria-label="Research telemetry metrics">
            {metrics.map((m, idx) => (
              <SpotlightCard
                key={m.label}
                spotlightColor={`${m.accent}22`}
                borderColor={`${m.accent}66`}
                style={{
                  padding: "20px 22px",
                  borderBottom: `2px solid ${m.accent}`,
                  minHeight: "140px",
                }}
              >
                <div className="hud-corner-tl" />
                <div className="hud-corner-tr" />
                <div className="hud-corner-bl" />
                <div className="hud-corner-br" />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span className="metric-label">{m.label}</span>
                  <span style={{ fontSize: "16px", opacity: 0.9 }}>{m.icon}</span>
                </div>
                <strong style={{ fontSize: "32px", display: "block", margin: "4px 0", color: "#ECF5FF", letterSpacing: "-0.03em" }}>
                  {loading ? (
                    "…"
                  ) : idx === 3 ? (
                    <span>
                      <AnimatedCounter value={verifiedCount} />
                      <span style={{ opacity: 0.6 }}>/{investigations.length || 1}</span>
                    </span>
                  ) : (
                    <AnimatedCounter value={parseInt(m.value, 10) || 0} />
                  )}
                </strong>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                  <span className="metric-detail">{m.detail}</span>
                  <span style={{ fontSize: "9px", fontFamily: "monospace", color: m.accent, background: "rgba(255,255,255,0.06)", padding: "2px 7px", borderRadius: "4px" }}>
                    <DecryptedText text={m.tag} speed={25} />
                  </span>
                </div>
              </SpotlightCard>
            ))}
          </section>
        </RevealSection>

        {/* Lower Intelligence Operations Grid */}
        <RevealSection delay={0.25}>
          <section className="lower-grid" style={{ marginTop: "24px" }}>
            {/* Recent Investigations Deck */}
            <SpotlightCard style={{ padding: "24px" }}>
              <div className="hud-corner-tl" />
              <div className="hud-corner-tr" />
              <div className="hud-corner-bl" />
              <div className="hud-corner-br" />
              <div className="panel-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <p className="eyebrow blue" style={{ margin: "0 0 2px" }}>OPERATIONAL STREAM</p>
                  <h3 style={{ margin: 0, fontSize: "17px", fontWeight: 700, color: "#f8fafc" }}>
                    Active & Persisted Investigations
                  </h3>
                </div>
                <Link className="muted" href="/history" style={{ fontSize: "12px", fontWeight: 600, color: "#38bdf8", textDecoration: "none" }}>
                  View All Missions ({investigations.length}) →
                </Link>
              </div>

              {loading ? (
                <div className="empty-state">
                  <p className="muted">Syncing mission corpus...</p>
                </div>
              ) : recentInvestigations.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">⌁</div>
                  <h4>No investigations initiated</h4>
                  <p>Launch your first research question to activate the autonomous multi-agent pipeline.</p>
                  <Link className="cyber-primary-btn" href="/investigations/new" style={{ marginTop: "16px", display: "inline-flex" }}>
                    Launch Mission
                  </Link>
                </div>
              ) : (
                <div className="source-list" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {recentInvestigations.map((item, idx) => (
                    <Link
                      className="source-row investigation-row card-hover-lift"
                      href={`/investigations/${item.id}`}
                      key={item.id}
                      style={{
                        textDecoration: "none",
                        padding: "12px 16px",
                        borderRadius: "8px",
                        background: "rgba(12, 25, 43, 0.65)",
                        border: "1px solid rgba(37, 217, 242, 0.12)",
                        display: "block",
                        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                      }}
                    >
                      <div className="row-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                          <span style={{ fontSize: "10px", fontFamily: "monospace", color: "#38bdf8", fontWeight: 700 }}>
                            #{String(idx + 1).padStart(2, "0")}
                          </span>
                          <strong style={{ fontSize: "13.5px", color: "#ECF5FF", lineHeight: 1.45 }}>{item.question}</strong>
                        </div>
                        <span className="ready-badge" style={{ textTransform: "uppercase", fontSize: "10px", flexShrink: 0 }}>
                          {item.quality_status}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "10px", alignItems: "center", fontSize: "11px", color: "var(--muted)", flexWrap: "wrap", marginTop: "6px" }}>
                        <span style={{ color: "#38bdf8", fontWeight: 600, fontFamily: "monospace", textTransform: "uppercase" }}>
                          [{item.mode}]
                        </span>
                        <span>·</span>
                        <span>Status: <strong style={{ color: "#cbd5e1" }}>{item.status}</strong></span>
                        <span>·</span>
                        <span>{item.source_count} literature sources</span>
                        <span>·</span>
                        <span>{item.evidence_count} evidence passages</span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </SpotlightCard>

            {/* Agent Observatory Status Matrix */}
            <SpotlightCard style={{ padding: "24px" }}>
              <div className="hud-corner-tl" />
              <div className="hud-corner-tr" />
              <div className="hud-corner-bl" />
              <div className="hud-corner-br" />
              <div className="panel-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <p className="eyebrow blue" style={{ margin: "0 0 2px" }}>AGENT OBSERVATORY</p>
                  <h3 style={{ margin: 0, fontSize: "17px", fontWeight: 700, color: "#f8fafc" }}>
                    Research Agent Roster
                  </h3>
                </div>
                <PulseIndicator
                  status="active"
                  label={loading ? "POLLING" : `${agents.length} READY`}
                />
              </div>

              <div className="readiness-list" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {agents.length === 0 && !loading ? (
                  <p className="muted">Agent registry telemetry unavailable.</p>
                ) : (
                  agents.slice(0, 8).map((agent) => (
                    <div
                      className="readiness-row"
                      key={agent.identifier}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "8px 12px",
                        background: "rgba(12, 25, 43, 0.5)",
                        borderRadius: "6px",
                        border: "1px solid rgba(255, 255, 255, 0.05)",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <span style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12.5px", fontWeight: 500, color: "#e2e8f0" }}>
                        <PulseIndicator status={agent.demo_mode ? "warning" : "active"} size={6} />
                        {agent.name}
                      </span>
                      <span style={{ fontSize: "10px", fontFamily: "monospace", color: agent.demo_mode ? "#f59e0b" : "#38bdf8", background: "rgba(255, 255, 255, 0.05)", padding: "1px 6px", borderRadius: "4px" }}>
                        {agent.demo_mode ? "RULE/DEMO" : "ACTIVE_LOCAL"}
                      </span>
                    </div>
                  ))
                )}
              </div>

              <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                  Model provider: Local Ollama / OpenAI Compatible
                </span>
                <Link className="inline-link" href="/agents" style={{ fontSize: "12px", color: "#38bdf8", fontWeight: 600 }}>
                  Full Observatory →
                </Link>
              </div>
            </SpotlightCard>
          </section>
        </RevealSection>
      </div>
    </>
  );
}

