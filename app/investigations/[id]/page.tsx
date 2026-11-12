"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useProviderSession } from "@/components/provider-context";
import { apiBaseUrl, requestJson } from "../../../lib/api";

type Investigation = {
  id: string;
  question: string;
  status: string;
  source_count: number;
  evidence_count: number;
  quality_status: string;
  quality_summary?: string;
  evidence_gap?: string;
};

type Source = {
  id: string;
  title: string;
  original_url: string;
  publisher?: string;
  source_type: string;
  relevance_score: number;
  relevance_reasons: string[];
  inclusion_status: string;
  rejection_reason?: string;
  access_level?: string;
  extraction_quality?: string;
  open_access_status?: string;
  selected_document_url?: string;
  document_url?: string;
  version_type?: string;
  access_route?: string;
  available_versions?: string[];
};

type Evidence = {
  id: string;
  source_id: string;
  claim_id?: string | null;
  exact_text: string;
  surrounding_context?: string | null;
  evidence_type: string;
  relevance_score: number;
  extraction_method: string;
  relevance_reason: string;
  page_number?: number | null;
  section_name?: string | null;
  document_id?: string | null;
  traceable: boolean;
};

type AnalysisJob = {
  id: string;
  investigation_id: string;
  status: string;
  max_debate_rounds: number;
  max_concurrent_agents: number;
  provider_kind?: string | null;
  default_model?: string | null;
  cancel_requested: boolean;
  error_message?: string | null;
};

type AgentExecution = {
  id: string;
  agent_identifier: string;
  status: string;
  model?: string | null;
  error_message?: string | null;
};

type ClaimAnalysis = {
  id: string;
  text: string;
  explanation: string;
  priority: number;
  search_objectives: string[];
  evidence_categories: string[];
  dependencies: string[];
  status: string;
};

type ArgumentItem = {
  id: string;
  claim_id: string;
  agent_identifier: string;
  argument_type: string;
  text: string;
  evidence_ids: string[];
  source_ids: string[];
  evidence_basis: string;
  reasoning_summary: string;
  limitations: string[];
  confidence: { level: string; explanation: string };
};

type DebateRound = {
  id: string;
  round_number: number;
  moderator_summary: string;
  unresolved_disagreements: string[];
  requested_follow_up: string[];
};

type Decision = {
  id: string;
  claim_id: string;
  decision: string;
  explanation: string;
  supporting_argument_ids: string[];
  evidence_ids: string[];
  unresolved_disagreements: string[];
};

type EvidenceProvenance = {
  evidence_id: string;
  source_id: string;
  document_id?: string | null;
  source_title: string;
  source_url: string;
  access_level: string;
  page_number?: number | null;
  section_name?: string | null;
};

type Report = {
  executive_summary: string;
  overall_assessment: string;
  evidence_gap?: string | null;
  sections: Array<{
    id: string;
    section_type: string;
    title: string;
    content: string;
    claim_ids: string[];
    evidence_ids: string[];
    provenance: EvidenceProvenance[];
  }>;
};

const ACTIVE_JOB_STATUSES = new Set([
  "queued",
  "planning",
  "researching",
  "debating",
  "adjudicating",
  "reporting",
]);

const TERMINAL_JOB_STATUSES = new Set([
  "completed",
  "completed_with_warnings",
  "failed",
  "cancelled",
]);

function formatExecutionStatus(status: string): string {
  switch (status) {
    case "waiting_in_queue":
    case "queued":
      return "Waiting in queue";
    case "generating":
    case "running":
      return "Generating";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

function executionStatusClass(status: string): string {
  if (status === "waiting_in_queue" || status === "queued") return "status-queued";
  if (status === "generating" || status === "running") return "status-generating";
  if (status === "completed") return "status-completed";
  if (status === "failed") return "status-failed";
  if (status === "cancelled") return "status-cancelled";
  return "";
}

export default function InvestigationPage({ params }: { params: Promise<{ id: string }> }) {
  const { config: sessionProvider } = useProviderSession();
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisJob | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [claims, setClaims] = useState<ClaimAnalysis[]>([]);
  const [argumentsList, setArgumentsList] = useState<ArgumentItem[]>([]);
  const [debates, setDebates] = useState<DebateRound[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [analysisRefresh, setAnalysisRefresh] = useState(0);
  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [evidenceFilter, setEvidenceFilter] = useState("all");
  const [highlightedEvidenceId, setHighlightedEvidenceId] = useState<string | null>(null);
  const [submittingAnalysis, setSubmittingAnalysis] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [useSessionProvider, setUseSessionProvider] = useState(true);
  const [sseStatus, setSseStatus] = useState<"connecting" | "connected" | "reconnecting">("connecting");
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const lastEventIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const { id } = await params;
        const [loadedInvestigation, loadedSources, loadedEvidence] = await Promise.all([
          requestJson<Investigation>(`/research/investigations/${id}`),
          requestJson<Source[]>(`/research/investigations/${id}/sources`),
          requestJson<Evidence[]>(`/research/investigations/${id}/evidence`),
        ]);
        if (active) {
          setInvestigation(loadedInvestigation);
          setSources(loadedSources);
          setEvidence(loadedEvidence);
        }
        try {
          const loadedAnalysis = await requestJson<AnalysisJob>(`/research/investigations/${id}/analysis`);
          const [loadedExecutions, loadedClaims, loadedArguments, loadedDebates, loadedDecisions] =
            await Promise.all([
              requestJson<AgentExecution[]>(`/research/analysis/${loadedAnalysis.id}/executions`),
              requestJson<ClaimAnalysis[]>(`/research/analysis/${loadedAnalysis.id}/claims`),
              requestJson<ArgumentItem[]>(`/research/analysis/${loadedAnalysis.id}/arguments`),
              requestJson<DebateRound[]>(`/research/analysis/${loadedAnalysis.id}/debates`),
              requestJson<Decision[]>(`/research/analysis/${loadedAnalysis.id}/decisions`),
            ]);
          let loadedReport: Report | null = null;
          if (
            loadedAnalysis.status === "completed" ||
            loadedAnalysis.status === "completed_with_warnings"
          ) {
            loadedReport = await requestJson<Report>(`/research/analysis/${loadedAnalysis.id}/report`);
          }
          if (active) {
            setAnalysis(loadedAnalysis);
            setExecutions(loadedExecutions);
            setClaims(loadedClaims);
            setArgumentsList(loadedArguments);
            setDebates(loadedDebates);
            setDecisions(loadedDecisions);
            setReport(loadedReport);
          }
        } catch {
          if (active) {
            setAnalysis(null);
            setExecutions([]);
            setClaims([]);
            setArgumentsList([]);
            setDebates([]);
            setDecisions([]);
            setReport(null);
          }
        }
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Investigation data could not be loaded.");
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [params, analysisRefresh]);

  useEffect(() => {
    let active = true;
    let source: EventSource | null = null;
    void params.then(({ id }) => {
      if (!active) return;
      setSseStatus("connecting");
      const cursorParam = lastEventIdRef.current
        ? `&last_event_id=${encodeURIComponent(lastEventIdRef.current)}`
        : "";
      source = new EventSource(`${apiBaseUrl}/events?investigation_id=${id}${cursorParam}`);
      source.onopen = () => {
        if (active) setSseStatus("connected");
      };
      source.onerror = () => {
        if (active) setSseStatus("reconnecting");
      };
      const refresh = (event: Event) => {
        if (!active) return;
        const messageEvent = event as MessageEvent<string>;
        let eventId = messageEvent.lastEventId || "";
        if (!eventId && messageEvent.data) {
          try {
            const parsed = JSON.parse(messageEvent.data) as { id?: string };
            eventId = parsed.id ?? "";
          } catch {
            eventId = "";
          }
        }
        if (eventId) {
          if (seenEventIdsRef.current.has(eventId)) {
            return;
          }
          if (seenEventIdsRef.current.size >= 500) {
            const oldest = seenEventIdsRef.current.values().next().value;
            if (oldest) seenEventIdsRef.current.delete(oldest);
          }
          seenEventIdsRef.current.add(eventId);
          lastEventIdRef.current = eventId;
        }
        setAnalysisRefresh((value) => value + 1);
      };
      [
        "analysis.queued",
        "analysis.stage_changed",
        "analysis.agent_queued",
        "analysis.agent_started",
        "analysis.agent_completed",
        "analysis.agent_failed",
        "analysis.agent_cancelled",
        "analysis.debate_round",
        "analysis.completed",
        "analysis.failed",
      ].forEach((eventName) => {
        source?.addEventListener(eventName, refresh);
      });
    });
    return () => {
      active = false;
      source?.close();
    };
  }, [params]);

  const isJobActive = Boolean(analysis && ACTIVE_JOB_STATUSES.has(analysis.status));
  const isJobTerminal = Boolean(analysis && TERMINAL_JOB_STATUSES.has(analysis.status));

  useEffect(() => {
    if (!isJobActive) return;
    const timer = window.setInterval(() => {
      setAnalysisRefresh((value) => value + 1);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [isJobActive]);

  function focusEvidence(evidenceId: string) {
    setEvidenceFilter("all");
    setHighlightedEvidenceId(evidenceId);
    window.setTimeout(() => {
      const element = document.getElementById(`evidence-${evidenceId}`);
      element?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  async function triggerAnalysis() {
    if (submittingAnalysis || isJobActive) return;
    setAnalysisError("");

    const shouldUseProvider = Boolean(useSessionProvider && sessionProvider?.connected);
    if (
      shouldUseProvider &&
      sessionProvider?.kind === "openai_compatible" &&
      !sessionProvider.apiKey
    ) {
      setAnalysisError(
        "OpenAI-compatible provider requires an API key in memory. Please re-enter credentials in Settings."
      );
      return;
    }

    setSubmittingAnalysis(true);
    try {
      const { id } = await params;
      const bodyPayload = shouldUseProvider && sessionProvider
        ? {
            max_debate_rounds: 2,
            max_concurrent_agents: 2,
            provider: {
              kind: sessionProvider.kind,
              endpoint: sessionProvider.endpoint,
              model: sessionProvider.model || undefined,
              api_key: sessionProvider.apiKey || undefined,
              allow_local_runtime: sessionProvider.allowLocalRuntime,
            },
          }
        : {
            max_debate_rounds: 2,
            max_concurrent_agents: 2,
          };

      const started = await requestJson<AnalysisJob>(`/research/investigations/${id}/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyPayload),
      });
      setAnalysis(started);
      setAnalysisRefresh((value) => value + 1);
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Could not start analysis.");
    } finally {
      setSubmittingAnalysis(false);
    }
  }

  async function cancelAnalysis() {
    if (!analysis || cancelling || !isJobActive) return;
    setCancelling(true);
    setAnalysisError("");
    try {
      const updated = await requestJson<AnalysisJob>(`/research/analysis/${analysis.id}/cancel`, {
        method: "POST",
      });
      setAnalysis(updated);
      setAnalysisRefresh((value) => value + 1);
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Could not cancel analysis.");
    } finally {
      setCancelling(false);
    }
  }

  if (error) {
    return (
      <main className="placeholder-page">
        <p className="connection-result error">{error}</p>
        <Link className="outline-button" href="/">
          Return to dashboard
        </Link>
      </main>
    );
  }
  if (!investigation) {
    return (
      <main className="placeholder-page">
        <p className="eyebrow blue">RESEARCH MONITOR</p>
        <h1>Loading investigation...</h1>
      </main>
    );
  }

  const sourceMap = new Map(sources.map((item) => [item.id, item]));
  const claimMap = new Map(claims.map((item) => [item.id, item]));
  const evidenceMap = new Map(evidence.map((item) => [item.id, item]));

  const visibleSources = sources.filter(
    (source) => sourceFilter === "all" || source.inclusion_status === sourceFilter
  );
  const visibleEvidence = evidence.filter(
    (item) => evidenceFilter === "all" || item.evidence_type === evidenceFilter
  );

  const advocateArguments = argumentsList.filter((item) => item.agent_identifier === "advocate");
  const skepticArguments = argumentsList.filter((item) => item.agent_identifier === "skeptic");
  const specialistArguments = argumentsList.filter(
    (item) => item.agent_identifier !== "advocate" && item.agent_identifier !== "skeptic"
  );

  const renderEvidenceButtons = (evidenceIds: string[]) => {
    if (evidenceIds.length === 0) {
      return <small className="muted">No evidence passages cited.</small>;
    }
    return (
      <div className="provenance-links">
        {evidenceIds.map((evidenceId, index) => {
          const item = evidenceMap.get(evidenceId);
          const src = item ? sourceMap.get(item.source_id) : undefined;
          const label = src
            ? `[${index + 1}] ${src.title.slice(0, 36)}${src.title.length > 36 ? "…" : ""}${
                item?.page_number ? ` · p.${item.page_number}` : ""
              }`
            : `Evidence ${evidenceId.slice(0, 8)}`;
          return (
            <button
              className="evidence-chip"
              key={evidenceId}
              type="button"
              onClick={() => focusEvidence(evidenceId)}
            >
              {label}
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <main className="investigation-page">
      <div className="row-header">
        <Link className="muted" href="/">
          ← Dashboard
        </Link>
        <span className="muted">
          Live updates: {sseStatus}
          {isJobActive ? " · polling fallback active" : ""}
        </span>
      </div>
      <p className="eyebrow blue">RESEARCH MONITOR</p>
      <h1>{investigation.question}</h1>
      <div className="investigation-status">
        <span className="ready-badge">{investigation.status}</span>
        <span>
          {investigation.source_count} sources · {investigation.evidence_count} evidence passages
        </span>
      </div>
      <div className="workspace-quick-links">
        <Link className="outline-button compact-button" href={`/evidence?investigation_id=${investigation.id}`}>
          Open in Evidence Explorer →
        </Link>
        <Link className="outline-button compact-button" href={`/sources?investigation_id=${investigation.id}`}>
          Open in Source Intelligence →
        </Link>
        <Link className="outline-button compact-button" href={`/agents?investigation_id=${investigation.id}`}>
          Open in Agent Observatory →
        </Link>
      </div>

      <section className="panel quality-panel">
        <div className="panel-heading">
          <h3>Research quality: {investigation.quality_status}</h3>
        </div>
        <p>{investigation.quality_summary ?? "Quality assessment is not available."}</p>
        {investigation.evidence_gap && <p className="connection-result error">{investigation.evidence_gap}</p>}
      </section>

      <section className="research-columns">
        <article className="panel">
          <div className="panel-heading">
            <h3>Sources</h3>
            <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
              <option value="all">All sources</option>
              <option value="included">Relevant</option>
              <option value="filtered">Filtered / low relevance</option>
            </select>
          </div>
          {visibleSources.length === 0 ? (
            <p className="muted">No sources match this filter.</p>
          ) : (
            <div className="source-list">
              {visibleSources.map((source) => (
                <div className="source-row" key={source.id}>
                  <a href={source.original_url} target="_blank" rel="noreferrer">
                    <strong>{source.title}</strong>
                    <span>
                      {source.publisher ?? source.source_type} · {source.inclusion_status} · score{" "}
                      {source.relevance_score}
                    </span>
                  </a>
                  <small>
                    {source.access_level ?? "metadata-only"} · {source.open_access_status ?? "not checked"}
                    {source.version_type ? ` · ${source.version_type}` : ""}
                    {source.rejection_reason ? ` · ${source.rejection_reason}` : ""}
                  </small>
                  {source.document_url && (
                    <a className="inline-link" href={source.document_url} target="_blank" rel="noreferrer">
                      Open retrieved document
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <h3>Evidence explorer</h3>
            <select value={evidenceFilter} onChange={(event) => setEvidenceFilter(event.target.value)}>
              <option value="all">All evidence</option>
              <option value="supporting">Supporting</option>
              <option value="contradicting">Contradicting</option>
              <option value="contextual">Contextual</option>
              <option value="methodological_limitation">Limitations</option>
            </select>
          </div>
          {visibleEvidence.length === 0 ? (
            <p className="muted">No relevant passages match this filter.</p>
          ) : (
            <div className="evidence-list">
              {visibleEvidence.map((item) => {
                const src = sourceMap.get(item.source_id);
                const isHighlighted = highlightedEvidenceId === item.id;
                return (
                  <blockquote
                    className={isHighlighted ? "evidence-highlighted" : ""}
                    id={`evidence-${item.id}`}
                    key={item.id}
                  >
                    <p>{item.exact_text}</p>
                    <small>
                      {item.evidence_type} · relevance {item.relevance_score}
                      {item.page_number ? ` · page ${item.page_number}` : ""}
                      {item.section_name ? ` · ${item.section_name}` : ""}
                      {` · ${item.extraction_method}`}
                    </small>
                    {src && (
                      <div className="evidence-provenance">
                        <span>
                          Source:{" "}
                          <a className="inline-link" href={src.original_url} target="_blank" rel="noreferrer">
                            {src.title}
                          </a>{" "}
                          ({src.access_level ?? "metadata_only"})
                        </span>
                        {src.document_url && (
                          <a className="inline-link" href={src.document_url} target="_blank" rel="noreferrer">
                            Document
                          </a>
                        )}
                      </div>
                    )}
                    <footer>{item.relevance_reason}</footer>
                  </blockquote>
                );
              })}
            </div>
          )}
        </article>
      </section>

      <section className="panel analysis-panel">
        <div className="panel-heading analysis-header">
          <div>
            <h3>Multi-agent intelligence</h3>
            <p className="muted">
              {sessionProvider?.connected ? (
                <>
                  Active session provider: <strong>{sessionProvider.kind}</strong> (
                  {sessionProvider.model ?? "default model"})
                </>
              ) : (
                <>
                  No in-memory provider active for this tab session (credentials are cleared on browser
                  refresh). Runs use <code>rule_based</code> mode unless you configure a provider in{" "}
                  <Link className="inline-link" href="/settings">
                    Settings
                  </Link>
                  .
                </>
              )}
            </p>
          </div>
          <div className="analysis-actions">
            {sessionProvider?.connected && !isJobActive && (
              <label className="mode-toggle">
                <input
                  type="checkbox"
                  checked={useSessionProvider}
                  onChange={(event) => setUseSessionProvider(event.target.checked)}
                />
                Use session provider
              </label>
            )}
            {(!analysis || isJobTerminal) && (
              <button
                className="primary-button"
                disabled={submittingAnalysis || isJobActive}
                type="button"
                onClick={() => void triggerAnalysis()}
              >
                {submittingAnalysis
                  ? "Starting..."
                  : analysis
                    ? "Re-run analysis"
                    : "Start analysis"}
              </button>
            )}
            {isJobActive && (
              <button
                className="outline-button danger-button"
                disabled={cancelling || analysis?.cancel_requested}
                type="button"
                onClick={() => void cancelAnalysis()}
              >
                {cancelling || analysis?.cancel_requested ? "Cancelling..." : "Cancel analysis"}
              </button>
            )}
          </div>
        </div>

        {analysisError && <p className="connection-result error">{analysisError}</p>}

        {analysis ? (
          <div className="analysis-body">
            <div className="analysis-status-bar">
              <span>
                Current stage: <strong>{analysis.status}</strong>
              </span>
              <span className="mode-pill">
                {analysis.provider_kind
                  ? `Provider-backed: ${analysis.provider_kind}${
                      analysis.default_model ? ` · ${analysis.default_model}` : ""
                    }`
                  : "Rule-based execution (no LLM provider)"}
              </span>
              {executions.length > 0 && (
                <span className="muted">
                  {executions.filter((item) => item.status === "generating" || item.status === "running").length}{" "}
                  generating ·{" "}
                  {executions.filter((item) => item.status === "waiting_in_queue" || item.status === "queued").length}{" "}
                  waiting in queue ·{" "}
                  {executions.filter((item) => item.status === "completed").length} completed
                </span>
              )}
              {analysis.cancel_requested && <span className="muted">Cancellation requested</span>}
              {analysis.error_message && (
                <span className="connection-result error">{analysis.error_message}</span>
              )}
            </div>

            {executions.length > 0 && (
              <div className="execution-grid">
                {executions.map((execution) => (
                  <div className="source-row" key={execution.id}>
                    <div className="row-header">
                      <strong>{execution.agent_identifier}</strong>
                      <span className={`exec-status-badge ${executionStatusClass(execution.status)}`}>
                        {formatExecutionStatus(execution.status)}
                      </span>
                    </div>
                    <small>
                      {execution.model ?? "default model"}
                      {execution.error_message ? ` · ${execution.error_message}` : ""}
                    </small>
                  </div>
                ))}
              </div>
            )}

            {claims.length > 0 && (
              <div className="analysis-subsection">
                <h4>Decomposed claims ({claims.length})</h4>
                <div className="source-list">
                  {claims.map((claim) => {
                    const claimEvidence = evidence.filter(
                      (item) => item.claim_id === claim.id
                    );
                    const citedByArguments = Array.from(
                      new Set(
                        argumentsList
                          .filter((arg) => arg.claim_id === claim.id)
                          .flatMap((arg) => arg.evidence_ids)
                      )
                    );
                    const linkedIds = Array.from(
                      new Set([...claimEvidence.map((item) => item.id), ...citedByArguments])
                    );
                    return (
                      <div className="source-row" key={claim.id}>
                        <div className="row-header">
                          <strong>
                            P{claim.priority}: {claim.text}
                          </strong>
                          <span className="ready-badge">{claim.status}</span>
                        </div>
                        <p className="muted">{claim.explanation}</p>
                        {claim.search_objectives.length > 0 && (
                          <small>Objectives: {claim.search_objectives.join(" · ")}</small>
                        )}
                        {renderEvidenceButtons(linkedIds)}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {argumentsList.length > 0 && (
              <div className="analysis-subsection">
                <h4>Adversarial analysis: Advocate vs. Skeptic</h4>
                <div className="argument-columns">
                  <div className="argument-column advocate-column">
                    <h5>Advocate ({advocateArguments.length})</h5>
                    {advocateArguments.length === 0 ? (
                      <p className="muted">No Advocate arguments persisted.</p>
                    ) : (
                      advocateArguments.map((arg) => (
                        <div className="source-row" key={arg.id}>
                          <div className="row-header">
                            <strong>{claimMap.get(arg.claim_id)?.text ?? "Claim"}</strong>
                            <span className="ready-badge">{arg.confidence.level}</span>
                          </div>
                          <p>{arg.text}</p>
                          <small>{arg.reasoning_summary}</small>
                          {renderEvidenceButtons(arg.evidence_ids)}
                        </div>
                      ))
                    )}
                  </div>

                  <div className="argument-column skeptic-column">
                    <h5>Skeptic ({skepticArguments.length})</h5>
                    {skepticArguments.length === 0 ? (
                      <p className="muted">No Skeptic arguments persisted.</p>
                    ) : (
                      skepticArguments.map((arg) => (
                        <div className="source-row" key={arg.id}>
                          <div className="row-header">
                            <strong>{claimMap.get(arg.claim_id)?.text ?? "Claim"}</strong>
                            <span className="ready-badge">{arg.confidence.level}</span>
                          </div>
                          <p>{arg.text}</p>
                          <small>{arg.reasoning_summary}</small>
                          {renderEvidenceButtons(arg.evidence_ids)}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {specialistArguments.length > 0 && (
                  <div className="specialist-section">
                    <h5>Specialist assessments ({specialistArguments.length})</h5>
                    <div className="source-list">
                      {specialistArguments.map((arg) => (
                        <div className="source-row" key={arg.id}>
                          <div className="row-header">
                            <strong>
                              {arg.agent_identifier} · {arg.argument_type}
                            </strong>
                            <span className="ready-badge">{arg.confidence.level}</span>
                          </div>
                          <small>Claim: {claimMap.get(arg.claim_id)?.text ?? arg.claim_id}</small>
                          <p>{arg.text}</p>
                          {arg.limitations.length > 0 && (
                            <small>Limitations: {arg.limitations.join(" · ")}</small>
                          )}
                          {renderEvidenceButtons(arg.evidence_ids)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {debates.length > 0 && (
              <div className="analysis-subsection">
                <h4>Debate moderation ({debates.length} round(s))</h4>
                <div className="source-list">
                  {debates.map((debate) => (
                    <div className="source-row" key={debate.id}>
                      <strong>Debate round {debate.round_number}</strong>
                      <p>{debate.moderator_summary}</p>
                      {debate.unresolved_disagreements.map((item) => (
                        <small key={item} className="connection-result error">
                          Unresolved: {item}
                        </small>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {decisions.length > 0 && (
              <div className="analysis-subsection">
                <h4>Adjudication decisions ({decisions.length})</h4>
                <div className="evidence-list">
                  {decisions.map((decision) => (
                    <blockquote key={decision.id}>
                      <strong>
                        {claimMap.get(decision.claim_id)?.text ?? decision.claim_id} —{" "}
                        {decision.decision}
                      </strong>
                      <p>{decision.explanation}</p>
                      {renderEvidenceButtons(decision.evidence_ids)}
                    </blockquote>
                  ))}
                </div>
              </div>
            )}

            {report && (
              <div className="analysis-subsection">
                <h4>Report: {report.overall_assessment}</h4>
                <p>{report.executive_summary}</p>
                {report.evidence_gap && (
                  <p className="connection-result error">Evidence gap: {report.evidence_gap}</p>
                )}
                <div className="source-list">
                  {report.sections.map((section) => (
                    <div className="source-row" key={section.id}>
                      <strong>{section.title}</strong>
                      <p>{section.content}</p>
                      {renderEvidenceButtons(section.evidence_ids)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="muted">No multi-agent analysis has been run for this investigation.</p>
        )}
      </section>
    </main>
  );
}
