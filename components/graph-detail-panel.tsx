"use client";

import Link from "next/link";
import { NODE_TYPE_META, type GraphEdgeView, type GraphNodeView } from "@/lib/graph";
import { agentStatusBadgeClass, formatLabel } from "@/lib/workspace";

type GraphDetailPanelProps = {
  selectedNode: GraphNodeView | null;
  selectedEdge: GraphEdgeView | null;
  nodeMap: Map<string, GraphNodeView>;
  isCollapsed: boolean;
  expandingNodeId: string | null;
  onExpandNode: (nodeId: string) => void;
  onToggleCollapse: (nodeId: string) => void;
  onSelectNodeById: (nodeId: string) => void;
  onClearSelection: () => void;
};

type EvidenceRef = { id: string; text?: string; exact_text?: string; relevance_score?: number; evidence_type?: string };
type ClaimRef = { claim_id: string; text: string; status: string; type: string };
type ArgumentRef = { id: string; agent_identifier: string; argument_type: string; confidence_level: string; text: string };
type VersionRef = {
  document_id?: string;
  oa_location_id?: string;
  version_type?: string;
  access_level?: string;
  access_route?: string;
  repository?: string;
  acquisition_status?: string;
  document_url?: string;
  url?: string;
};

export function GraphDetailPanel({
  selectedNode,
  selectedEdge,
  nodeMap,
  isCollapsed,
  expandingNodeId,
  onExpandNode,
  onToggleCollapse,
  onSelectNodeById,
  onClearSelection,
}: GraphDetailPanelProps) {
  if (!selectedNode && !selectedEdge) {
    return (
      <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow blue">Traceability Inspector</p>
            <h3>Select a node or edge</h3>
          </div>
        </div>
        <p className="muted" style={{ fontSize: 12, lineHeight: 1.6 }}>
          Click any node to inspect claims, supporting and contradicting evidence passages, agent arguments,
          adjudication decisions, documents, and source publications. Click an edge to inspect its persisted
          relationship classification.
        </p>
      </aside>
    );
  }

  if (selectedEdge && !selectedNode) {
    const src = nodeMap.get(selectedEdge.source);
    const tgt = nodeMap.get(selectedEdge.target);
    return (
      <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow blue">Persisted Relationship</p>
            <h3>{formatLabel(selectedEdge.relationship_type)}</h3>
          </div>
          <button className="outline-button compact-button" type="button" onClick={onClearSelection}>
            Clear
          </button>
        </div>
        <div className="workspace-chain">
          <div>
            <strong>From:</strong>{" "}
            {src ? (
              <button className="inline-link kg-link-btn" type="button" onClick={() => onSelectNodeById(src.id)}>
                [{NODE_TYPE_META[src.type].shortLabel}] {src.label}
              </button>
            ) : (
              selectedEdge.source
            )}
          </div>
          <div>
            <strong>To:</strong>{" "}
            {tgt ? (
              <button className="inline-link kg-link-btn" type="button" onClick={() => onSelectNodeById(tgt.id)}>
                [{NODE_TYPE_META[tgt.type].shortLabel}] {tgt.label}
              </button>
            ) : (
              selectedEdge.target
            )}
          </div>
          <div>
            <strong>Classification:</strong>{" "}
            <span>{formatLabel(selectedEdge.classification ?? selectedEdge.relationship_type)}</span>
          </div>
          {selectedEdge.explanation && (
            <div>
              <strong>Rationale:</strong> <span className="muted">{selectedEdge.explanation}</span>
            </div>
          )}
        </div>
      </aside>
    );
  }

  if (!selectedNode) return null;

  const meta = NODE_TYPE_META[selectedNode.type];
  const m = selectedNode.metadata;
  const invId = selectedNode.investigation_id;

  return (
    <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow blue">{meta.label}</p>
          <h3 style={{ fontSize: 15 }}>{selectedNode.label}</h3>
        </div>
        <span className={agentStatusBadgeClass(selectedNode.status)}>{formatLabel(selectedNode.status)}</span>
      </div>

      <div className="analysis-actions">
        <button
          className="outline-button compact-button"
          disabled={expandingNodeId === selectedNode.id}
          type="button"
          onClick={() => onExpandNode(selectedNode.id)}
        >
          {expandingNodeId === selectedNode.id ? "Expanding..." : "Expand connected nodes"}
        </button>
        <button className="outline-button compact-button" type="button" onClick={() => onToggleCollapse(selectedNode.id)}>
          {isCollapsed ? "Expand branch" : "Collapse branch"}
        </button>
        <button className="outline-button compact-button" type="button" onClick={onClearSelection}>
          Close
        </button>
      </div>

      {selectedNode.missing_provenance.length > 0 && (
        <div className="workspace-chain" style={{ borderColor: "#6b5323" }}>
          <strong style={{ color: "var(--amber)", fontSize: 11 }}>Missing persisted provenance / links</strong>
          <small className="muted">
            Not fabricated: {selectedNode.missing_provenance.map((item) => formatLabel(item)).join(", ")}
          </small>
        </div>
      )}

      {selectedNode.type === "claim" && (
        <div className="workspace-chain">
          <div>
            <strong>Full claim:</strong>
            <p style={{ margin: "4px 0 0", lineHeight: 1.5 }}>{String(m.full_text ?? selectedNode.description)}</p>
          </div>
          {typeof m.explanation === "string" && m.explanation && (
            <div>
              <strong>Planner rationale:</strong> <span className="muted">{m.explanation}</span>
            </div>
          )}
          <div>
            <strong>Supporting evidence ({Array.isArray(m.supporting_evidence) ? m.supporting_evidence.length : 0}):</strong>
            {Array.isArray(m.supporting_evidence) && m.supporting_evidence.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.supporting_evidence as EvidenceRef[]).map((ev) => (
                  <li key={ev.id} style={{ marginBottom: 4 }}>
                    <button
                      className="inline-link kg-link-btn"
                      type="button"
                      onClick={() => onSelectNodeById(`evidence:${ev.id}`)}
                    >
                      {ev.text ?? ev.exact_text}
                    </button>{" "}
                    <span className="muted">(rel {Number(ev.relevance_score ?? 0).toFixed(2)})</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No supporting evidence linked.</p>
            )}
          </div>
          <div>
            <strong>Contradicting evidence ({Array.isArray(m.contradicting_evidence) ? m.contradicting_evidence.length : 0}):</strong>
            {Array.isArray(m.contradicting_evidence) && m.contradicting_evidence.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.contradicting_evidence as EvidenceRef[]).map((ev) => (
                  <li key={ev.id} style={{ marginBottom: 4 }}>
                    <button
                      className="inline-link kg-link-btn"
                      type="button"
                      onClick={() => onSelectNodeById(`evidence:${ev.id}`)}
                    >
                      {ev.text ?? ev.exact_text}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No contradicting evidence linked.</p>
            )}
          </div>
          <div>
            <strong>Related arguments ({Array.isArray(m.related_arguments) ? m.related_arguments.length : 0}):</strong>
            {Array.isArray(m.related_arguments) && m.related_arguments.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.related_arguments as ArgumentRef[]).map((arg) => (
                  <li key={arg.id} style={{ marginBottom: 4 }}>
                    <button
                      className="inline-link kg-link-btn"
                      type="button"
                      onClick={() => onSelectNodeById(`agent_argument:${arg.id}`)}
                    >
                      {formatLabel(arg.agent_identifier)} ({formatLabel(arg.argument_type)} · {arg.confidence_level})
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No agent arguments persisted.</p>
            )}
          </div>
          <div>
            <strong>Adjudication decision:</strong>{" "}
            {m.adjudication_decision && typeof m.adjudication_decision === "object" ? (
              <p style={{ margin: "4px 0 0" }}>
                <strong>{formatLabel(String((m.adjudication_decision as { decision?: string }).decision))}</strong>:{" "}
                <span className="muted">{String((m.adjudication_decision as { explanation?: string }).explanation)}</span>
              </p>
            ) : (
              <span className="muted">Not adjudicated yet.</span>
            )}
          </div>
        </div>
      )}

      {selectedNode.type === "evidence" && (
        <div className="workspace-chain">
          <div>
            <strong>Exact passage:</strong>
            <blockquote>
              <p>{String(m.exact_text ?? selectedNode.description)}</p>
              <small>
                Classification: {formatLabel(String(m.evidence_type ?? selectedNode.status))} · relevance{" "}
                {Number(m.relevance_score ?? 0).toFixed(3)}
              </small>
            </blockquote>
          </div>
          <div>
            <strong>Page & section provenance:</strong>{" "}
            <span className="muted">
              {m.page_number ? `Page ${String(m.page_number)}` : "Page missing"} ·{" "}
              {m.section_name ? String(m.section_name) : "Section not recorded"} ·{" "}
              {formatLabel(String(m.extraction_method ?? "unknown"))}
            </span>
          </div>
          <div>
            <strong>Associated claim(s):</strong>
            {Array.isArray(m.associated_claims) && m.associated_claims.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.associated_claims as ClaimRef[]).map((cl) => (
                  <li key={cl.claim_id}>
                    <button
                      className="inline-link kg-link-btn"
                      type="button"
                      onClick={() => onSelectNodeById(`claim:${cl.claim_id}`)}
                    >
                      {cl.text}
                    </button>{" "}
                    <span className="muted">({formatLabel(cl.status)})</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No claim association recorded.</p>
            )}
          </div>
          <div>
            <strong>Document & source:</strong>{" "}
            <span className="muted">
              {m.document_id
                ? `${String(m.document_title ?? "Document")} (${formatLabel(String(m.document_access_level ?? "metadata_only"))})`
                : "Document record missing (direct source FK only)"}{" "}
              ·{" "}
              {m.source_title ? String(m.source_title) : String(m.source_id)}
            </span>
          </div>
        </div>
      )}

      {selectedNode.type === "source" && (
        <div className="workspace-chain">
          <div>
            <strong>Title:</strong> <span>{String(m.title ?? selectedNode.label)}</span>
          </div>
          <div>
            <strong>Authors:</strong>{" "}
            <span className="muted">
              {Array.isArray(m.authors) && m.authors.length > 0 ? (m.authors as string[]).join(", ") : "Not recorded"}
            </span>
          </div>
          <div>
            <strong>Publication & DOI:</strong>{" "}
            <span className="muted">
              {m.publication_date ? String(m.publication_date) : "Date unknown"} ·{" "}
              {m.doi ? `DOI: ${String(m.doi)}` : "No DOI"} · {formatLabel(String(m.source_type ?? "other"))}
            </span>
          </div>
          <div>
            <strong>Original URL:</strong>{" "}
            {typeof m.original_url === "string" ? (
              <a className="inline-link" href={m.original_url} target="_blank" rel="noreferrer">
                {m.original_url} ↗
              </a>
            ) : (
              <span className="muted">Missing URL</span>
            )}
          </div>
          <div>
            <strong>Document versions ({Array.isArray(m.document_versions) ? m.document_versions.length : 0}):</strong>
            {Array.isArray(m.document_versions) && m.document_versions.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.document_versions as VersionRef[]).map((ver, idx) => (
                  <li key={`${ver.document_id ?? ver.oa_location_id ?? idx}`}>
                    <span>{formatLabel(ver.version_type ?? "unknown")}</span>{" "}
                    <span className="muted">
                      ({formatLabel(ver.access_level ?? ver.acquisition_status ?? "recorded")}
                      {ver.repository ? ` · ${ver.repository}` : ""})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No document versions persisted.</p>
            )}
          </div>
          <div>
            <strong>Related evidence ({Number(m.evidence_count ?? 0)}):</strong>
            {Array.isArray(m.related_evidence) && m.related_evidence.length > 0 ? (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                {(m.related_evidence as EvidenceRef[]).map((ev) => (
                  <li key={ev.id}>
                    <button
                      className="inline-link kg-link-btn"
                      type="button"
                      onClick={() => onSelectNodeById(`evidence:${ev.id}`)}
                    >
                      {ev.exact_text ?? ev.text}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted" style={{ margin: "4px 0 0" }}>No evidence extracted from this source.</p>
            )}
          </div>
        </div>
      )}

      {(selectedNode.type === "document" ||
        selectedNode.type === "agent_argument" ||
        selectedNode.type === "adjudication_decision" ||
        selectedNode.type === "research_question" ||
        selectedNode.type === "investigation") && (
        <div className="workspace-chain">
          <p style={{ margin: 0, lineHeight: 1.55 }}>{selectedNode.description}</p>
          {typeof m.reasoning_summary === "string" && m.reasoning_summary && (
            <div>
              <strong>Reasoning summary:</strong> <span className="muted">{m.reasoning_summary}</span>
            </div>
          )}
          {typeof m.document_url === "string" && m.document_url && (
            <a className="inline-link" href={m.document_url} target="_blank" rel="noreferrer">
              Open retrieved document ↗
            </a>
          )}
        </div>
      )}

      <div className="workspace-quick-links">
        <Link className="outline-button compact-button" href={`/investigations/${invId}`}>
          Investigation detail
        </Link>
        {selectedNode.type === "claim" && (
          <Link
            className="outline-button compact-button"
            href={`/evidence?investigation_id=${invId}&claim_id=${selectedNode.entity_id}`}
          >
            Claim evidence in Explorer
          </Link>
        )}
        {selectedNode.type === "evidence" && (
          <Link
            className="outline-button compact-button"
            href={`/evidence?investigation_id=${invId}&evidence_id=${selectedNode.entity_id}`}
          >
            Open in Evidence Explorer
          </Link>
        )}
        {selectedNode.type === "source" && (
          <Link
            className="outline-button compact-button"
            href={`/sources?investigation_id=${invId}&source_id=${selectedNode.entity_id}`}
          >
            Open in Source Intelligence
          </Link>
        )}
        {selectedNode.type === "document" && typeof m.source_id === "string" && (
          <Link
            className="outline-button compact-button"
            href={`/sources?investigation_id=${invId}&source_id=${m.source_id}`}
          >
            Inspect parent Source
          </Link>
        )}
      </div>
    </aside>
  );
}
