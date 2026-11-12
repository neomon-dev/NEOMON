"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";
import {
  agentStatusBadgeClass,
  formatLabel,
  type InvestigationSummary,
  type WorkspaceSourceItem,
  type WorkspaceSourcePage,
} from "@/lib/workspace";

const PAGE_SIZE = 20;

export function SourceIntelligence() {
  const searchParams = useSearchParams();
  const initialInvId = searchParams.get("investigation_id") ?? "";
  const initialSourceId = searchParams.get("source_id") ?? "";

  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [pageData, setPageData] = useState<WorkspaceSourcePage>({
    items: [],
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [selectedId, setSelectedId] = useState<string>(initialSourceId);

  const [search, setSearch] = useState("");
  const [investigationId, setInvestigationId] = useState(initialInvId);
  const [inclusionStatus, setInclusionStatus] = useState("all");
  const [sourceType, setSourceType] = useState("all");
  const [accessLevel, setAccessLevel] = useState("all");
  const [openAccessStatus, setOpenAccessStatus] = useState("all");
  const [sort, setSort] = useState("relevance_desc");
  const [offset, setOffset] = useState(0);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const [loading, setLoading] = useState(true);
  const [refreshingSourceId, setRefreshingSourceId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    requestJson<InvestigationSummary[]>("/research/investigations")
      .then((rows) => {
        if (active) setInvestigations(rows);
      })
      .catch(() => {
        // Investigation list is optional filter metadata.
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadSources() {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(offset));
      params.set("sort", sort);
      if (investigationId) params.set("investigation_id", investigationId);
      if (search.trim()) params.set("q", search.trim());
      if (inclusionStatus !== "all") params.set("inclusion_status", inclusionStatus);
      if (sourceType !== "all") params.set("source_type", sourceType);
      if (accessLevel !== "all") params.set("access_level", accessLevel);
      if (openAccessStatus !== "all") params.set("open_access_status", openAccessStatus);

      try {
        const result = await requestJson<WorkspaceSourcePage>(`/research/sources?${params.toString()}`);
        if (!active) return;
        setPageData(result);
        setError("");
        setSelectedId((prev) => {
          if (prev && result.items.some((item) => item.id === prev)) return prev;
          return result.items[0]?.id ?? "";
        });
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Could not load persisted sources.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadSources();
    return () => {
      active = false;
    };
  }, [investigationId, search, inclusionStatus, sourceType, accessLevel, openAccessStatus, sort, offset, refreshNonce]);

  async function refreshSource(source: WorkspaceSourceItem) {
    setRefreshingSourceId(source.id);
    setActionMessage("");
    try {
      await requestJson(
        `/research/investigations/${source.investigation_id}/sources/${source.id}/refresh`,
        { method: "POST" },
      );
      setActionMessage(`Refreshed open-access acquisition for "${source.title}".`);
      setRefreshNonce((prev) => prev + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Source refresh failed.");
    } finally {
      setRefreshingSourceId(null);
    }
  }

  function clearFilters() {
    setSearch("");
    setInvestigationId("");
    setInclusionStatus("all");
    setSourceType("all");
    setAccessLevel("all");
    setOpenAccessStatus("all");
    setSort("relevance_desc");
    setOffset(0);
  }

  const selected: WorkspaceSourceItem | undefined =
    pageData.items.find((item) => item.id === selectedId) ?? pageData.items[0];
  const showingFrom = pageData.total === 0 ? 0 : pageData.offset + 1;
  const showingTo = Math.min(pageData.total, pageData.offset + pageData.items.length);

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Evidence Intelligence Workspace</p>
          <h1>Source Intelligence</h1>
        </div>
        <div className="analysis-actions">
          <Link className="outline-button compact-button" href="/evidence">
            Evidence explorer
          </Link>
          <Link className="primary-button" href="/investigations/new">
            + New investigation
          </Link>
        </div>
      </header>

      <div className="content">
        <div className="metric-grid">
          <article className="metric-card">
            <span className="metric-label">Matching sources</span>
            <strong>{pageData.total}</strong>
            <span className="metric-detail">Persisted sources across active filters</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Full-text on page</span>
            <strong>{pageData.items.filter((item) => item.access_level === "full_text").length}</strong>
            <span className="metric-detail">Sources with retrieved full-text content</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">OA resolved on page</span>
            <strong>{pageData.items.filter((item) => item.open_access_status === "resolved").length}</strong>
            <span className="metric-detail">Verified open-access full-text resolutions</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Evidence on page</span>
            <strong>{pageData.items.reduce((sum, item) => sum + item.evidence_count, 0)}</strong>
            <span className="metric-detail">Traceable passages extracted from visible sources</span>
          </article>
        </div>

        <section className="panel" style={{ marginTop: 18 }}>
          <div className="workspace-toolbar">
            <input
              aria-label="Search sources"
              className="filter-input"
              placeholder="Search title, publisher, DOI, or URL..."
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOffset(0);
              }}
            />
            <select
              aria-label="Filter by investigation"
              className="filter-select"
              value={investigationId}
              onChange={(event) => {
                setInvestigationId(event.target.value);
                setOffset(0);
              }}
            >
              <option value="">All investigations</option>
              {investigations.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.question.slice(0, 56)}
                  {inv.question.length > 56 ? "…" : ""} ({inv.source_count})
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by inclusion status"
              className="filter-select"
              value={inclusionStatus}
              onChange={(event) => {
                setInclusionStatus(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All inclusion states</option>
              <option value="included">Included</option>
              <option value="low_relevance">Low relevance</option>
              <option value="rejected">Rejected</option>
            </select>
            <select
              aria-label="Filter by source type"
              className="filter-select"
              value={sourceType}
              onChange={(event) => {
                setSourceType(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All source types</option>
              <option value="academic">Academic</option>
              <option value="institutional">Institutional</option>
              <option value="news">News</option>
              <option value="web">Web</option>
              <option value="other">Other</option>
            </select>
            <select
              aria-label="Filter by access level"
              className="filter-select"
              value={accessLevel}
              onChange={(event) => {
                setAccessLevel(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All access levels</option>
              <option value="full_text">Full text</option>
              <option value="abstract_only">Abstract only</option>
              <option value="metadata_only">Metadata only</option>
              <option value="none">No document retrieved</option>
            </select>
            <select
              aria-label="Filter by open access status"
              className="filter-select"
              value={openAccessStatus}
              onChange={(event) => {
                setOpenAccessStatus(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All OA statuses</option>
              <option value="resolved">OA resolved</option>
              <option value="metadata_only">Metadata only</option>
              <option value="unavailable">Unavailable</option>
              <option value="not_checked">Not checked</option>
              <option value="failed">Failed</option>
            </select>
            <select
              aria-label="Sort sources"
              className="filter-select"
              value={sort}
              onChange={(event) => {
                setSort(event.target.value);
                setOffset(0);
              }}
            >
              <option value="relevance_desc">Highest relevance</option>
              <option value="evidence_desc">Most evidence extracted</option>
              <option value="relevance_asc">Lowest relevance</option>
              <option value="recent_desc">Most recent</option>
            </select>
            <button className="outline-button compact-button" type="button" onClick={clearFilters}>
              Reset filters
            </button>
          </div>

          {actionMessage && <p className="connection-result success dashboard-error">{actionMessage}</p>}
          {error && <p className="connection-result error dashboard-error">{error}</p>}

          {loading ? (
            <div className="empty-state">
              <p className="muted">Loading persisted source intelligence...</p>
            </div>
          ) : pageData.items.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◈</div>
              <h4>No persisted sources match these filters</h4>
              <p>Start a research investigation or adjust your source, OA, or access filters.</p>
            </div>
          ) : (
            <div className="workspace-split">
              <div className="source-list" style={{ paddingTop: 0 }}>
                {pageData.items.map((source) => {
                  const isSelected = selected?.id === source.id;
                  return (
                    <button
                      key={source.id}
                      type="button"
                      className={`workspace-card${isSelected ? " selected" : ""}`}
                      onClick={() => setSelectedId(source.id)}
                    >
                      <div className="row-header">
                        <strong style={{ fontSize: 13 }}>{source.title}</strong>
                        <span className={agentStatusBadgeClass(source.inclusion_status)}>
                          {formatLabel(source.inclusion_status)}
                        </span>
                      </div>
                      <div className="workspace-card-meta">
                        <span className="mode-pill">{source.source_type}</span>
                        <span className={agentStatusBadgeClass(source.access_level ?? "metadata_only")}>
                          {formatLabel(source.access_level ?? "metadata_only")}
                        </span>
                        <span className={agentStatusBadgeClass(source.open_access_status)}>
                          OA: {formatLabel(source.open_access_status)}
                        </span>
                        <span className="mode-pill">relevance {source.relevance_score.toFixed(2)}</span>
                        <span className="mode-pill">{source.evidence_count} evidence</span>
                      </div>
                      <small className="muted">
                        {source.publisher ?? "Unknown publisher"}
                        {source.publication_date ? ` · ${source.publication_date}` : ""}
                        {source.doi ? ` · DOI ${source.doi}` : ""}
                        {source.extraction_quality ? ` · quality ${source.extraction_quality}` : ""}
                      </small>
                    </button>
                  );
                })}
              </div>

              {selected && (
                <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow blue">Source & Document Provenance</p>
                      <h3 style={{ fontSize: 15 }}>{selected.title}</h3>
                    </div>
                    <button
                      className="outline-button compact-button"
                      disabled={refreshingSourceId === selected.id}
                      type="button"
                      onClick={() => void refreshSource(selected)}
                    >
                      {refreshingSourceId === selected.id ? "Refreshing..." : "Refresh OA"}
                    </button>
                  </div>

                  <div className="workspace-chain">
                    <div>
                      <strong>Investigation:</strong>{" "}
                      <Link className="inline-link" href={`/investigations/${selected.investigation_id}`}>
                        {selected.investigation_question}
                      </Link>
                    </div>
                    <div>
                      <strong>Metadata:</strong>{" "}
                      <span>
                        {selected.source_type} · {selected.publisher ?? "Publisher not specified"}
                        {selected.publication_date ? ` · ${selected.publication_date}` : ""}
                        {selected.doi ? ` · DOI: ${selected.doi}` : ""}
                      </span>
                    </div>
                    {selected.authors.length > 0 && (
                      <div>
                        <strong>Authors:</strong> <span>{selected.authors.join(", ")}</span>
                      </div>
                    )}
                    <div>
                      <strong>Original URL:</strong>{" "}
                      <a className="inline-link" href={selected.original_url} target="_blank" rel="noreferrer">
                        {selected.original_url} ↗
                      </a>
                    </div>
                    <div>
                      <strong>Canonical URL:</strong>{" "}
                      <a className="inline-link" href={selected.canonical_url} target="_blank" rel="noreferrer">
                        {selected.canonical_url} ↗
                      </a>
                    </div>
                    <div>
                      <strong>Inclusion & Acquisition:</strong>{" "}
                      <span>
                        {formatLabel(selected.inclusion_status)} · OA {formatLabel(selected.open_access_status)} · access{" "}
                        {formatLabel(selected.access_level ?? "metadata_only")} · extraction quality{" "}
                        {formatLabel(selected.extraction_quality ?? "low")}
                        {selected.version_type ? ` · version ${formatLabel(selected.version_type)}` : ""}
                      </span>
                      {selected.rejection_reason && (
                        <p className="connection-result error" style={{ marginTop: 4 }}>
                          Rejection reason: {selected.rejection_reason}
                        </p>
                      )}
                      {selected.extraction_error && (
                        <p className="connection-result error" style={{ marginTop: 4 }}>
                          Extraction error ({selected.extraction_status ?? "failed"}): {selected.extraction_error}
                        </p>
                      )}
                    </div>
                    {selected.relevance_reasons.length > 0 && (
                      <div>
                        <strong>Relevance reasons ({selected.relevance_score.toFixed(3)}):</strong>
                        <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                          {selected.relevance_reasons.map((reason) => (
                            <li key={reason} className="muted">
                              {reason}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div>
                    <p className="eyebrow">Retrieved Documents ({selected.documents.length})</p>
                    {selected.documents.length === 0 ? (
                      <p className="muted" style={{ fontSize: 12 }}>
                        No document content persisted for this source yet.
                      </p>
                    ) : (
                      <div className="source-list" style={{ paddingTop: 0 }}>
                        {selected.documents.map((doc) => (
                          <div className="source-row" key={doc.id}>
                            <strong>{doc.title || doc.content_type}</strong>
                            <span>
                              {formatLabel(doc.access_level)} · quality {formatLabel(doc.extraction_quality)} · version{" "}
                              {formatLabel(doc.version_type)} · route {formatLabel(doc.access_route)} · metadata{" "}
                              {formatLabel(doc.metadata_match_status)}
                              {doc.page_count ? ` · ${doc.page_count} page(s)` : ""}
                            </span>
                            {doc.document_url && (
                              <a className="inline-link" href={doc.document_url} target="_blank" rel="noreferrer">
                                {doc.document_url} ↗
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {selected.open_access_locations.length > 0 && (
                    <div>
                      <p className="eyebrow">Open Access Locations ({selected.open_access_locations.length})</p>
                      <div className="source-list" style={{ paddingTop: 0 }}>
                        {selected.open_access_locations.map((loc) => (
                          <div className="source-row" key={loc.id}>
                            <div className="row-header">
                              <strong>{loc.repository || formatLabel(loc.version_type)}</strong>
                              <span className={agentStatusBadgeClass(loc.acquisition_status)}>
                                {formatLabel(loc.acquisition_status)}
                              </span>
                            </div>
                            <span>
                              match: {formatLabel(loc.match_status)} · {loc.match_reason || "No match reason"}
                            </span>
                            {loc.failure_reason && (
                              <small className="connection-result error">{loc.failure_reason}</small>
                            )}
                            <a className="inline-link" href={loc.url} target="_blank" rel="noreferrer">
                              {loc.url} ↗
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="workspace-quick-links">
                    <Link
                      className="primary-button compact-button"
                      href={`/evidence?investigation_id=${selected.investigation_id}&source_id=${selected.id}`}
                    >
                      Inspect {selected.evidence_count} evidence passage(s) →
                    </Link>
                    <Link className="outline-button compact-button" href={`/investigations/${selected.investigation_id}`}>
                      Open investigation
                    </Link>
                  </div>
                </aside>
              )}
            </div>
          )}

          {pageData.total > 0 && (
            <div className="workspace-pagination">
              <span>
                Showing {showingFrom}–{showingTo} of {pageData.total} sources
              </span>
              <div className="analysis-actions">
                <button
                  className="outline-button compact-button"
                  disabled={offset === 0 || loading}
                  type="button"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </button>
                <button
                  className="outline-button compact-button"
                  disabled={offset + PAGE_SIZE >= pageData.total || loading}
                  type="button"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
