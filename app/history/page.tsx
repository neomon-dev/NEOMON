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
          <p className="eyebrow">Archive</p>
          <h1>Research history</h1>
        </div>
        <Link className="primary-button" href="/investigations/new">
          + New investigation
        </Link>
      </header>

      <div className="content">
        <section className="panel">
          <div className="panel-heading history-controls">
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
            <div className="source-list">
              {filtered.map((item) => (
                <Link className="source-row investigation-row" href={`/investigations/${item.id}`} key={item.id}>
                  <div className="row-header">
                    <strong>{item.question}</strong>
                    <span className="ready-badge">{item.quality_status}</span>
                  </div>
                  <span>
                    {item.mode} · status: {item.status} · {item.source_count} sources ({item.relevant_source_count} relevant, {item.full_text_count} full-text) · {item.evidence_count} evidence
                  </span>
                  {item.created_at && (
                    <small className="muted">
                      Created {new Date(item.created_at).toLocaleString()}
                    </small>
                  )}
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
