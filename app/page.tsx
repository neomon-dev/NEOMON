"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";

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
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Could not load dashboard data.");
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
  const needsReviewCount = investigations.filter((item) => item.quality_status !== "strong").length;
  const recentInvestigations = investigations.slice(0, 6);

  const metrics = [
    [
      "Investigations",
      loading ? "…" : String(investigations.length),
      investigations.length === 0 ? "No investigations yet" : `${investigations.length} persisted run(s)`,
    ],
    [
      "Evidence passages",
      loading ? "…" : String(totalEvidence),
      totalEvidence === 0 ? "Awaiting first run" : "Traceable extracted passages",
    ],
    [
      "Sources collected",
      loading ? "…" : String(totalSources),
      totalSources === 0 ? "No sources retrieved yet" : `${totalFullText} full-text document(s)`,
    ],
    [
      "Qualified / gaps",
      loading ? "…" : String(needsReviewCount),
      needsReviewCount === 0 ? "All investigations strong" : "Limited or insufficient evidence",
    ],
  ];

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Command center</p>
          <h1>Research dashboard</h1>
        </div>
        <Link className="primary-button" href="/investigations/new">
          + New investigation
        </Link>
      </header>

      <div className="content">
        <section className="hero-card">
          <div>
            <p className="eyebrow blue">NEURAL EVIDENCE NETWORK</p>
            <h2>Make every conclusion earn its confidence.</h2>
            <p className="hero-copy">
              Plan questions, trace sources, and expose contradictions through transparent
              multi-agent research.
            </p>
            <Link className="outline-button" href="/investigations/new">
              Start an investigation <span>→</span>
            </Link>
          </div>
          <div className="hero-orbit" aria-hidden="true">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="orbit-core">N</div>
          </div>
        </section>

        {error && <p className="connection-result error dashboard-error">{error}</p>}

        <section className="metric-grid" aria-label="Research metrics">
          {metrics.map(([label, value, detail]) => (
            <article className="metric-card" key={label}>
              <span className="metric-label">{label}</span>
              <strong>{value}</strong>
              <span className="metric-detail">{detail}</span>
            </article>
          ))}
        </section>

        <section className="lower-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Activity</p>
                <h3>Recent investigations</h3>
              </div>
              <Link className="muted" href="/history">
                View all →
              </Link>
            </div>
            {loading ? (
              <div className="empty-state">
                <p className="muted">Loading investigations...</p>
              </div>
            ) : recentInvestigations.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">⌁</div>
                <h4>No investigations yet</h4>
                <p>Start a research question to see agent activity and evidence appear here.</p>
              </div>
            ) : (
              <div className="source-list">
                {recentInvestigations.map((item) => (
                  <Link className="source-row investigation-row" href={`/investigations/${item.id}`} key={item.id}>
                    <div className="row-header">
                      <strong>{item.question}</strong>
                      <span className="ready-badge">{item.quality_status}</span>
                    </div>
                    <span>
                      {item.mode} · {item.status} · {item.source_count} sources · {item.evidence_count} evidence
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">System</p>
                <h3>Agent readiness</h3>
              </div>
              <span className="ready-badge">
                {loading ? "Checking" : `${agents.length} registered`}
              </span>
            </div>
            <div className="readiness-list">
              {agents.length === 0 && !loading ? (
                <p className="muted">Agent registry unavailable.</p>
              ) : (
                agents.slice(0, 6).map((agent) => (
                  <div className="readiness-row" key={agent.identifier}>
                    <span>
                      <i className="status-dot" />
                      {agent.name}
                    </span>
                    <span className="muted">
                      {agent.demo_mode ? `${agent.status} (rule/demo)` : agent.status}
                    </span>
                  </div>
                ))
              )}
            </div>
            <p className="panel-note">
              Configure a local or OpenAI-compatible model provider in{" "}
              <Link className="inline-link" href="/settings">
                Settings
              </Link>{" "}
              to run LLM-backed analysis.
            </p>
          </article>
        </section>
      </div>
    </>
  );
}
