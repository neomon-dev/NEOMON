"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";
import {
  agentStatusBadgeClass,
  formatLabel,
  type InvestigationSummary,
  type WorkspaceEvidenceItem,
  type WorkspaceEvidencePage,
} from "@/lib/workspace";

const PAGE_SIZE = 20;

function evidenceTypeBadgeClass(evidenceType: string): string {
  if (evidenceType === "supporting") return "exec-status-badge status-supporting";
  if (evidenceType === "contradicting") return "exec-status-badge status-failed";
  if (evidenceType === "mitigating") return "exec-status-badge status-mitigating";
  if (evidenceType === "methodological_limitation") return "exec-status-badge status-methodological";
  if (evidenceType === "insufficient") return "exec-status-badge status-insufficient";
  return "exec-status-badge status-contextual";
}

export function EvidenceExplorer() {
  const searchParams = useSearchParams();
  const initialInvId = searchParams.get("investigation_id") ?? "";
  const initialSourceId = searchParams.get("source_id") ?? "";
  const initialClaimId = searchParams.get("claim_id") ?? "";
  const initialEvidenceId = searchParams.get("evidence_id") ?? "";

  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [pageData, setPageData] = useState<WorkspaceEvidencePage>({
    items: [],
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [selectedId, setSelectedId] = useState<string>(initialEvidenceId);

  const [search, setSearch] = useState("");
  const [investigationId, setInvestigationId] = useState(initialInvId);
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [claimId, setClaimId] = useState(initialClaimId);
  const [evidenceType, setEvidenceType] = useState("all");
  const [inclusionStatus, setInclusionStatus] = useState("all");
  const [traceableFilter, setTraceableFilter] = useState("all");
  const [minRelevance, setMinRelevance] = useState("all");
  const [sort, setSort] = useState("relevance_desc");
  const [offset, setOffset] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    requestJson<InvestigationSummary[]>("/research/investigations")
      .then((rows) => {
        if (active) setInvestigations(rows);
      })
      .catch(() => {
        // Investigation list is supplementary filter metadata; evidence query surfaces main backend errors.
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadEvidence() {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(offset));
      params.set("sort", sort);
      if (investigationId) params.set("investigation_id", investigationId);
      if (sourceId) params.set("source_id", sourceId);
      if (claimId) params.set("claim_id", claimId);
      if (search.trim()) params.set("q", search.trim());
      if (evidenceType !== "all") params.set("evidence_type", evidenceType);
      if (inclusionStatus !== "all") params.set("inclusion_status", inclusionStatus);
      if (traceableFilter !== "all") params.set("traceable", traceableFilter);
      if (minRelevance !== "all") params.set("min_relevance", minRelevance);

      try {
        const result = await requestJson<WorkspaceEvidencePage>(`/research/evidence?${params.toString()}`);
        if (!active) return;
        setPageData(result);
        setError("");
        setSelectedId((prev) => {
          if (prev && result.items.some((item) => item.id === prev)) return prev;
          return result.items[0]?.id ?? "";
        });
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Could not load evidence passages.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadEvidence();
    return () => {
      active = false;
    };
  }, [investigationId, sourceId, claimId, search, evidenceType, inclusionStatus, traceableFilter, minRelevance, sort, offset]);

  function clearFilters() {
    setSearch("");
    setInvestigationId("");
    setSourceId("");
    setClaimId("");
    setEvidenceType("all");
    setInclusionStatus("all");
    setTraceableFilter("all");
    setMinRelevance("all");
    setSort("relevance_desc");
    setOffset(0);
  }

  const selected: WorkspaceEvidenceItem | undefined =
    pageData.items.find((item) => item.id === selectedId) ?? pageData.items[0];
  const showingFrom = pageData.total === 0 ? 0 : pageData.offset + 1;
  const showingTo = Math.min(pageData.total, pageData.offset + pageData.items.length);

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Evidence Intelligence Workspace</p>
          <h1>Evidence Explorer</h1>
        </div>
        <div className="analysis-actions">
          <Link className="outline-button compact-button" href="/sources">
            Source intelligence
          </Link>
          <Link className="primary-button" href="/investigations/new">
            + New investigation
          </Link>
        </div>
      </header>

      <div className="content">
        <div className="metric-grid">
          <article className="metric-card">
            <span className="metric-label">Matching evidence</span>
            <strong>{pageData.total}</strong>
            <span className="metric-detail">Persisted passages matching active filters</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Traceable on page</span>
            <strong>{pageData.items.filter((item) => item.traceable).length}</strong>
            <span className="metric-detail">Direct source & extraction provenance preserved</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Supporting / Challenging</span>
            <strong>
              {pageData.items.filter((item) => item.evidence_type === "supporting").length} /{" "}
              {pageData.items.filter((item) => item.evidence_type === "contradicting").length}
            </strong>
            <span className="metric-detail">On current page (never inferred from score)</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Investigations</span>
            <strong>{investigations.length}</strong>
            <span className="metric-detail">Isolated investigation corpora available</span>
          </article>
        </div>

        <section className="panel" style={{ marginTop: 18 }}>
          <div className="workspace-toolbar">
            <input
              aria-label="Search evidence passages"
              className="filter-input"
              placeholder="Search passage text, context, section, source title, or claim..."
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
                setSourceId("");
                setClaimId("");
                setOffset(0);
              }}
            >
              <option value="">All investigations</option>
              {investigations.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.question.slice(0, 56)}
                  {inv.question.length > 56 ? "…" : ""} ({inv.evidence_count})
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by evidence classification"
              className="filter-select"
              value={evidenceType}
              onChange={(event) => {
                setEvidenceType(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All classifications</option>
              <option value="supporting">Supporting</option>
              <option value="contradicting">Contradicting</option>
              <option value="mitigating">Mitigating (Counterbalancing)</option>
              <option value="methodological_limitation">Methodological limitation</option>
              <option value="contextual">Contextual</option>
              <option value="insufficient">Insufficient</option>
            </select>
            <select
              aria-label="Filter by minimum relevance"
              className="filter-select"
              value={minRelevance}
              onChange={(event) => {
                setMinRelevance(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">Any relevance</option>
              <option value="0.2">Relevance &gt;= 0.20</option>
              <option value="0.4">Relevance &gt;= 0.40</option>
              <option value="0.6">Relevance &gt;= 0.60</option>
              <option value="0.8">Relevance &gt;= 0.80</option>
            </select>
            <select
              aria-label="Filter by source inclusion status"
              className="filter-select"
              value={inclusionStatus}
              onChange={(event) => {
                setInclusionStatus(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All inclusion states</option>
              <option value="included">Included sources</option>
              <option value="low_relevance">Low relevance</option>
              <option value="rejected">Rejected sources</option>
            </select>
            <select
              aria-label="Filter by traceability"
              className="filter-select"
              value={traceableFilter}
              onChange={(event) => {
                setTraceableFilter(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All traceability</option>
              <option value="true">Traceable only</option>
              <option value="false">Untraceable only</option>
            </select>
            <select
              aria-label="Sort evidence"
              className="filter-select"
              value={sort}
              onChange={(event) => {
                setSort(event.target.value);
                setOffset(0);
              }}
            >
              <option value="relevance_desc">Highest relevance</option>
              <option value="relevance_asc">Lowest relevance</option>
              <option value="recent_desc">Most recent</option>
            </select>
            <button className="outline-button compact-button" type="button" onClick={clearFilters}>
              Reset filters
            </button>
          </div>

          {(sourceId || claimId) && (
            <div className="workspace-quick-links">
              {sourceId && (
                <button
                  className="evidence-chip"
                  type="button"
                  onClick={() => {
                    setSourceId("");
                    setOffset(0);
                  }}
                >
                  Scoped to source {sourceId.slice(0, 8)} ×
                </button>
              )}
              {claimId && (
                <button
                  className="evidence-chip"
                  type="button"
                  onClick={() => {
                    setClaimId("");
                    setOffset(0);
                  }}
                >
                  Scoped to claim {claimId.slice(0, 8)} ×
                </button>
              )}
            </div>
          )}

          {error && <p className="connection-result error dashboard-error">{error}</p>}

          {loading ? (
            <div className="empty-state">
              <p className="muted">Loading persisted evidence passages...</p>
            </div>
          ) : pageData.items.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◇</div>
              <h4>No persisted evidence matches these filters</h4>
              <p>Run an investigation or broaden your search and classification filters.</p>
            </div>
          ) : (
            <div className="workspace-split">
              <div className="source-list" style={{ paddingTop: 0 }}>
                {pageData.items.map((item) => {
                  const isSelected = selected?.id === item.id;
                  const primaryClaim = item.claim_text ?? item.linked_claims[0]?.claim_text ?? null;
                  const primaryClaimStatus = item.claim_status ?? item.linked_claims[0]?.claim_status ?? "unassessed";
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`workspace-card${isSelected ? " selected" : ""}`}
                      onClick={() => setSelectedId(item.id)}
                    >
                      <div className="row-header">
                        <div className="workspace-card-meta">
                          <span className={evidenceTypeBadgeClass(item.evidence_type)}>
                            {formatLabel(item.evidence_type)}
                          </span>
                          <span className={agentStatusBadgeClass(item.source_inclusion_status)}>
                            {formatLabel(item.source_inclusion_status)}
                          </span>
                          <span className="mode-pill">relevance {item.relevance_score.toFixed(2)}</span>
                          <span className="mode-pill">{item.traceable ? "traceable" : "untraceable"}</span>
                        </div>
                        <small className="muted">
                          {item.page_number ? `p.${item.page_number}` : "no page"}
                          {item.section_name ? ` · ${item.section_name}` : ""}
                        </small>
                      </div>
                      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55 }}>{item.exact_text}</p>
                      <div className="workspace-card-meta">
                        <span>Source: {item.source_title}</span>
                        <span>·</span>
                        <span>Doc access: {formatLabel(item.document_access_level ?? "metadata_only")}</span>
                        <span>·</span>
                        <span>Method: {formatLabel(item.extraction_method)}</span>
                      </div>
                      {primaryClaim && (
                        <small className="muted">
                          Claim ({formatLabel(primaryClaimStatus)}): {primaryClaim}
                        </small>
                      )}
                    </button>
                  );
                })}
              </div>

              {selected && (
                <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow blue">Provenance Inspector</p>
                      <h3>Evidence {selected.id.slice(0, 8)}</h3>
                    </div>
                    <span className={evidenceTypeBadgeClass(selected.evidence_type)}>
                      {formatLabel(selected.evidence_type)}
                    </span>
                  </div>

                  <div>
                    <p className="eyebrow">Exact Passage</p>
                    <blockquote>
                      <p>{selected.exact_text}</p>
                      <small>
                        Relevance: {selected.relevance_score.toFixed(3)} · {selected.relevance_reason || "No score rationale recorded"}
                      </small>
                    </blockquote>
                  </div>

                  {selected.surrounding_context && (
                    <div>
                      <p className="eyebrow">Surrounding Context</p>
                      <p className="muted" style={{ fontSize: 12, lineHeight: 1.55 }}>
                        {selected.surrounding_context}
                      </p>
                    </div>
                  )}

                  <div className="workspace-chain">
                    <p className="eyebrow" style={{ marginBottom: 4 }}>
                      Traceability Chain (Claim → Evidence → Document → Source)
                    </p>
                    <div>
                      <strong>Investigation:</strong>{" "}
                      <Link className="inline-link" href={`/investigations/${selected.investigation_id}`}>
                        {selected.investigation_question}
                      </Link>
                    </div>
                    <div>
                      <strong>Associated claims ({selected.linked_claims.length || (selected.claim_text ? 1 : 0)}):</strong>
                      {selected.linked_claims.length > 0 ? (
                        <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                          {selected.linked_claims.map((link) => (
                            <li key={link.claim_id} style={{ marginBottom: 6 }}>
                              <span>{link.claim_text}</span>{" "}
                              <span className={agentStatusBadgeClass(link.claim_status)}>
                                {formatLabel(link.claim_status)}
                              </span>{" "}
                              <span className="muted">
                                ({formatLabel(link.relationship_type)} · {link.explanation})
                              </span>
                            </li>
                          ))}
                        </ul>
                      ) : selected.claim_text ? (
                        <p style={{ margin: "4px 0 0" }}>
                          {selected.claim_text}{" "}
                          <span className={agentStatusBadgeClass(selected.claim_status ?? "unassessed")}>
                            {formatLabel(selected.claim_status ?? "unassessed")}
                          </span>
                        </p>
                      ) : (
                        <p className="muted" style={{ margin: "4px 0 0" }}>
                          No claim relationship linked yet (unassessed).
                        </p>
                      )}
                    </div>
                    <div>
                      <strong>Document:</strong>{" "}
                      <span>
                        {selected.document_title || "Metadata record only"} · access{" "}
                        {formatLabel(selected.document_access_level ?? "metadata_only")} · quality{" "}
                        {formatLabel(selected.document_extraction_quality ?? "low")}
                        {selected.page_number ? ` · page ${selected.page_number}` : ""}
                        {selected.section_name ? ` · section ${selected.section_name}` : ""}
                      </span>
                      {selected.document_url && (
                        <div>
                          <a className="inline-link" href={selected.document_url} target="_blank" rel="noreferrer">
                            Open retrieved document ↗
                          </a>
                        </div>
                      )}
                    </div>
                    <div>
                      <strong>Source:</strong>{" "}
                      <Link
                        className="inline-link"
                        href={`/sources?investigation_id=${selected.investigation_id}&source_id=${selected.source_id}`}
                      >
                        {selected.source_title}
                      </Link>{" "}
                      <span className="muted">
                        ({selected.source_type} · {formatLabel(selected.source_inclusion_status)} · OA{" "}
                        {formatLabel(selected.source_open_access_status)})
                      </span>
                      {selected.source_rejection_reason && (
                        <p className="connection-result error" style={{ marginTop: 4 }}>
                          Rejection reason: {selected.source_rejection_reason}
                        </p>
                      )}
                      <div>
                        <a className="inline-link" href={selected.source_url} target="_blank" rel="noreferrer">
                          Original source URL ↗
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="workspace-quick-links">
                    <Link
                      className="outline-button compact-button"
                      href={`/investigations/${selected.investigation_id}#evidence-${selected.id}`}
                    >
                      View in investigation
                    </Link>
                    <Link
                      className="outline-button compact-button"
                      href={`/sources?investigation_id=${selected.investigation_id}&source_id=${selected.source_id}`}
                    >
                      Inspect source
                    </Link>
                    <Link
                      className="outline-button compact-button"
                      href={`/agents?investigation_id=${selected.investigation_id}`}
                    >
                      Agent runs
                    </Link>
                  </div>
                </aside>
              )}
            </div>
          )}

          {pageData.total > 0 && (
            <div className="workspace-pagination">
              <span>
                Showing {showingFrom}–{showingTo} of {pageData.total} evidence passages
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
