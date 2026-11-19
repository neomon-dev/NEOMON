"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";
import {
  PulseIndicator,
  DecryptedText,
  SpotlightCard,
  AnimatedCounter,
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

export default function HistoryPage() {
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [search, setSearch] = useState("");
  const [qualityFilter, setQualityFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const rows = await requestJson<InvestigationItem[]>("/research/investigations");
        if (active) {
          setInvestigations(rows);
          setError("");
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Could not load investigation history.");
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

  const filtered = investigations.filter((item) => {
    const matchesQuery = item.question.toLowerCase().includes(search.trim().toLowerCase());
    const matchesQuality = qualityFilter === "all" || item.quality_status === qualityFilter;
    return matchesQuery && matchesQuality;
  });

  return (
    <>
      <header className="topbar">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <PulseIndicator status="cyan" size={8} />
            <p className="eyebrow">Archive</p>
          </div>
          <h1>
            <DecryptedText text="Research History" speed={30} />
          </h1>
        </div>
        <Link className="primary-button" href="/investigations/new">
          + New investigation
        </Link>
      </header>

      <div className="content compact">
        <section className="panel" style={{ border: "1px solid rgba(37, 217, 242, 0.2)" }}>
          <div className="panel-heading history-controls" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ display: "flex", gap: "10px", flex: 1, minWidth: "260px" }}>
              <input
                aria-label="Filter investigations by question"
                className="filter-input"
                placeholder="Search research questions..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <select
                aria-label="Filter by quality status"
                className="filter-select"
                value={qualityFilter}
                onChange={(event) => setQualityFilter(event.target.value)}
              >
                <option value="all">All quality levels</option>
                <option value="strong">Strong</option>
                <option value="limited">Limited</option>
                <option value="insufficient_evidence">Insufficient evidence</option>
              </select>
            </div>
            <div className="muted" style={{ fontSize: "12px", fontFamily: "var(--font-mono, monospace)" }}>
              <span>MATCHING ARCHIVES: </span>
              <strong style={{ color: "var(--cyan)" }}>
                <AnimatedCounter value={filtered.length} />
              </strong>
            </div>
          </div>

          {error && <p className="connection-result error dashboard-error">{error}</p>}

          {loading ? (
            <div className="empty-state">
              <p className="muted">Loading investigation history...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">↺</div>
              <h4>No matching investigations</h4>
              <p>Try clearing your filter or start a new research investigation.</p>
            </div>
          ) : (
            <div className="source-list" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {filtered.map((item) => (
                <Link href={`/investigations/${item.id}`} key={item.id} style={{ textDecoration: "none" }}>
                  <SpotlightCard
                    className="source-row investigation-row"
                    spotlightColor="rgba(37, 217, 242, 0.1)"
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                      padding: "14px 18px",
                      borderRadius: "6px",
                      background: "rgba(12, 25, 43, 0.6)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      transition: "border-color 0.2s ease",
                    }}
                  >
                    <div className="row-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{item.question}</strong>
                      <span className="ready-badge">{item.quality_status}</span>
                    </div>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      {item.mode} · status: {item.status} · {item.source_count} sources ({item.relevant_source_count} relevant, {item.full_text_count} full-text) · {item.evidence_count} evidence
                    </span>
                    {item.created_at && (
                      <small className="muted" style={{ fontSize: "11px" }}>
                        Created {new Date(item.created_at).toLocaleString()}
                      </small>
                    )}
                  </SpotlightCard>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
