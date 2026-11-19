"use client";

import Link from "next/link";
import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { useProviderSession } from "@/components/provider-context";
import { ResearchGapWorkspace } from "@/components/research-gap-workspace";
import { ScientificReliabilityWorkspace } from "@/components/scientific-reliability-workspace";
import { CollaborationPanel } from "@/components/collaboration-panel";
import { AtmosphericAurora } from "@/components/animated-neural-background";
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
  created_at?: string;
  mode?: string;
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
  publication_year?: number | null;
  authors?: string[];
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
  retrieval_timestamp?: string;
};

type AnalysisCoverageSummary = {
  required_agents: string[];
  completed_agents: string[];
  failed_agents: string[];
  skipped_agents: string[];
  pending_agents: string[];
  claims_total: number;
  claims_evaluated: number;
  claims_without_arguments: number;
  claims_without_evidence: number;
  claims_with_supporting_evidence: number;
  claims_with_conflicting_evidence: number;
  coverage_percentage: number;
  is_partially_completed: boolean;
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
  coverage?: AnalysisCoverageSummary | null;
};

type AgentExecution = {
  id: string;
  agent_identifier: string;
  status: string;
  model?: string | null;
  error_message?: string | null;
  queue_wait_seconds?: number | null;
  inference_duration_seconds?: number | null;
  queue_position?: number | null;
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

type EvidenceStrength = {
  score: number;
  tier: string;
  breakdown: {
    source_independence: number;
    source_quality: number;
    full_text_coverage: number;
    methodological_rigor: number;
    conflict_resolution: number;
  };
};

type ReportVersionSummary = {
  id: string;
  version_number: number;
  executive_summary: string;
  overall_assessment: string;
  evidence_strength: EvidenceStrength;
  created_at?: string | null;
};

type Report = {
  id?: string;
  job_id?: string;
  executive_summary: string;
  overall_assessment: string;
  evidence_gap?: string | null;
  version_number?: number;
  evidence_strength?: EvidenceStrength | null;
  versions?: ReportVersionSummary[];
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

const VALID_TABS = [
  "overview",
  "intelligence",
  "evidence",
  "sources",
  "graph",
  "report",
  "horizon",
  "collaboration",
] as const;

type WorkspaceTab = (typeof VALID_TABS)[number];

const EVIDENCE_PAGE_SIZE = 12;
const SOURCES_PAGE_SIZE = 10;

function formatExecutionStatus(status: string, queuePosition?: number | null): string {
  switch (status) {
    case "waiting_in_queue":
    case "queued":
      return queuePosition && queuePosition > 0
        ? `Waiting in queue (#${queuePosition})`
        : "Waiting in queue";
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

function evidenceClassificationBadge(evidenceType: string) {
  switch (evidenceType) {
    case "supporting":
      return {
        label: "Direct Supporting",
        className: "evidence-badge-supporting",
        borderClass: "border-emerald-500/40",
      };
    case "contradicting":
      return {
        label: "Direct Contradicting",
        className: "evidence-badge-contradicting",
        borderClass: "border-rose-500/40",
      };
    case "contextual":
      return {
        label: "Contextual Background",
        className: "evidence-badge-contextual",
        borderClass: "border-sky-500/40",
      };
    case "methodological_limitation":
      return {
        label: "Methodological Limitation",
        className: "evidence-badge-limitation",
        borderClass: "border-purple-500/40",
      };
    case "insufficient":
    default:
      return {
        label: "Unassessed / Insufficient",
        className: "evidence-badge-unassessed",
        borderClass: "border-amber-500/40",
      };
  }
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

  // Active Workspace Tab
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");

  // Report & Export state
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [regeneratingReport, setRegeneratingReport] = useState(false);
  const [showStrengthBreakdown, setShowStrengthBreakdown] = useState(false);
  const [showExportPanel, setShowExportPanel] = useState(false);
  const [downloadingExport, setDownloadingExport] = useState<string | null>(null);

  // General & SSE state
  const [analysisRefresh, setAnalysisRefresh] = useState(0);
  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [submittingAnalysis, setSubmittingAnalysis] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [useSessionProvider, setUseSessionProvider] = useState(true);
  const [sseStatus, setSseStatus] = useState<"connecting" | "connected" | "reconnecting">("connecting");
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const lastEventIdRef = useRef<string | null>(null);

  // Evidence Explorer Filters & Pagination
  const [evidenceSearch, setEvidenceSearch] = useState("");
  const [evidenceFilter, setEvidenceFilter] = useState("all");
  const [evidenceClaimFilter, setEvidenceClaimFilter] = useState("all");
  const [evidenceSourceFilter, setEvidenceSourceFilter] = useState("all");
  const [evidenceMinRelevance, setEvidenceMinRelevance] = useState("all");
  const [evidenceTraceableOnly, setEvidenceTraceableOnly] = useState(false);
  const [evidenceSort, setEvidenceSort] = useState<"relevance_desc" | "relevance_asc" | "source_title" | "type">("relevance_desc");
  const [evidencePage, setEvidencePage] = useState(1);
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState<Set<string>>(new Set());
  const [highlightedEvidenceId, setHighlightedEvidenceId] = useState<string | null>(null);
  const [showGuidanceCallout, setShowGuidanceCallout] = useState(true);

  // Sources Library Filters & Pagination
  const [sourceSearch, setSourceSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [sourceAccessFilter, setSourceAccessFilter] = useState("all");
  const [sourceSort, setSourceSort] = useState<"relevance_desc" | "title_asc" | "publisher">("relevance_desc");
  const [sourcePage, setSourcePage] = useState(1);
  const [expandedSourceIds, setExpandedSourceIds] = useState<Set<string>>(new Set());

  // URL Hash Sync for Back/Forward Navigation
  useEffect(() => {
    const applyHash = () => {
      const hash = window.location.hash.replace("#", "") as WorkspaceTab;
      if (VALID_TABS.includes(hash)) {
        setActiveTab(hash);
      }
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  const switchTab = useCallback((tab: WorkspaceTab) => {
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      window.history.pushState(null, "", `#${tab}`);
    }
  }, []);

  // Main Data Loader
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

  // SSE Event Listener
  useEffect(() => {
    let active = true;
    let source: EventSource | null = null;
    void params.then(async ({ id }) => {
      if (!active) return;
      setSseStatus("connecting");
      const token = typeof window !== "undefined" ? localStorage.getItem("neomon_session_token") : null;
      let ticketParam = "";
      if (token) {
        try {
          const tRes = await requestJson<{ ticket: string }>("/auth/stream-ticket", {
            method: "POST",
          });
          if (tRes?.ticket) {
            ticketParam = `&ticket=${encodeURIComponent(tRes.ticket)}`;
          }
        } catch {
          // Fallback to query token if ticket endpoint unreachable
          ticketParam = `&token=${encodeURIComponent(token)}`;
        }
      }
      if (!active) return;
      const cursorParam = lastEventIdRef.current
        ? `&last_event_id=${encodeURIComponent(lastEventIdRef.current)}`
        : "";
      source = new EventSource(`${apiBaseUrl}/events?investigation_id=${id}${cursorParam}${ticketParam}`, {
        withCredentials: true,
      });
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

  // Polling fallback when job is active
  useEffect(() => {
    if (!isJobActive) return;
    const timer = window.setInterval(() => {
      setAnalysisRefresh((value) => value + 1);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [isJobActive]);

  // Lookup maps for fast relational queries
  const sourceMap = useMemo(() => new Map(sources.map((item) => [item.id, item])), [sources]);
  const claimMap = useMemo(() => new Map(claims.map((item) => [item.id, item])), [claims]);
  const evidenceMap = useMemo(() => new Map(evidence.map((item) => [item.id, item])), [evidence]);

  // Filtered & Sorted Evidence
  const filteredEvidence = useMemo(() => {
    let result = evidence;

    if (evidenceFilter !== "all") {
      result = result.filter((item) => item.evidence_type === evidenceFilter);
    }
    if (evidenceClaimFilter !== "all") {
      result = result.filter((item) => item.claim_id === evidenceClaimFilter);
    }
    if (evidenceSourceFilter !== "all") {
      result = result.filter((item) => item.source_id === evidenceSourceFilter);
    }
    if (evidenceTraceableOnly) {
      result = result.filter((item) => item.traceable);
    }
    if (evidenceMinRelevance !== "all") {
      const min = parseFloat(evidenceMinRelevance);
      result = result.filter((item) => item.relevance_score >= min);
    }
    if (evidenceSearch.trim()) {
      const q = evidenceSearch.toLowerCase().trim();
      result = result.filter((item) => {
        const text = item.exact_text.toLowerCase();
        const reason = item.relevance_reason.toLowerCase();
        const srcTitle = sourceMap.get(item.source_id)?.title.toLowerCase() ?? "";
        const sec = (item.section_name ?? "").toLowerCase();
        return text.includes(q) || reason.includes(q) || srcTitle.includes(q) || sec.includes(q);
      });
    }

    // Sorting
    return [...result].sort((a, b) => {
      if (evidenceSort === "relevance_desc") return b.relevance_score - a.relevance_score;
      if (evidenceSort === "relevance_asc") return a.relevance_score - b.relevance_score;
      if (evidenceSort === "source_title") {
        const titleA = sourceMap.get(a.source_id)?.title ?? "";
        const titleB = sourceMap.get(b.source_id)?.title ?? "";
        return titleA.localeCompare(titleB);
      }
      if (evidenceSort === "type") return a.evidence_type.localeCompare(b.evidence_type);
      return 0;
    });
  }, [
    evidence,
    evidenceFilter,
    evidenceClaimFilter,
    evidenceSourceFilter,
    evidenceTraceableOnly,
    evidenceMinRelevance,
    evidenceSearch,
    evidenceSort,
    sourceMap,
  ]);

  // Paginated Evidence
  const paginatedEvidence = useMemo(() => {
    const start = (evidencePage - 1) * EVIDENCE_PAGE_SIZE;
    return filteredEvidence.slice(start, start + EVIDENCE_PAGE_SIZE);
  }, [filteredEvidence, evidencePage]);

  const totalEvidencePages = Math.ceil(filteredEvidence.length / EVIDENCE_PAGE_SIZE) || 1;

  // Filtered & Sorted Sources
  const filteredSources = useMemo(() => {
    let result = sources;

    if (sourceFilter !== "all") {
      result = result.filter((item) => item.inclusion_status === sourceFilter);
    }
    if (sourceAccessFilter !== "all") {
      result = result.filter((item) => item.access_level === sourceAccessFilter);
    }
    if (sourceSearch.trim()) {
      const q = sourceSearch.toLowerCase().trim();
      result = result.filter((item) => {
        const title = item.title.toLowerCase();
        const pub = (item.publisher ?? "").toLowerCase();
        const url = item.original_url.toLowerCase();
        return title.includes(q) || pub.includes(q) || url.includes(q);
      });
    }

    return [...result].sort((a, b) => {
      if (sourceSort === "relevance_desc") return b.relevance_score - a.relevance_score;
      if (sourceSort === "title_asc") return a.title.localeCompare(b.title);
      if (sourceSort === "publisher") return (a.publisher ?? "").localeCompare(b.publisher ?? "");
      return 0;
    });
  }, [sources, sourceFilter, sourceAccessFilter, sourceSearch, sourceSort]);

  const paginatedSources = useMemo(() => {
    const start = (sourcePage - 1) * SOURCES_PAGE_SIZE;
    return filteredSources.slice(start, start + SOURCES_PAGE_SIZE);
  }, [filteredSources, sourcePage]);

  const totalSourcePages = Math.ceil(filteredSources.length / SOURCES_PAGE_SIZE) || 1;

  // Evidence distribution counts for Overview
  const evidenceDistribution = useMemo(() => {
    const supporting = evidence.filter((e) => e.evidence_type === "supporting").length;
    const contradicting = evidence.filter((e) => e.evidence_type === "contradicting").length;
    const contextual = evidence.filter((e) => e.evidence_type === "contextual").length;
    const limitations = evidence.filter((e) => e.evidence_type === "methodological_limitation").length;
    const unassessed = evidence.length - (supporting + contradicting + contextual + limitations);
    return { supporting, contradicting, contextual, limitations, unassessed };
  }, [evidence]);

  // Jump to specific evidence passage across tabs
  const focusEvidence = useCallback((evidenceId: string) => {
    switchTab("evidence");
    setEvidenceFilter("all");
    setEvidenceClaimFilter("all");
    setEvidenceSourceFilter("all");
    setEvidenceSearch("");
    setEvidenceMinRelevance("all");
    setEvidenceTraceableOnly(false);

    // Calculate which page this item is on
    const targetIdx = evidence.findIndex((e) => e.id === evidenceId);
    if (targetIdx !== -1) {
      const targetPage = Math.floor(targetIdx / EVIDENCE_PAGE_SIZE) + 1;
      setEvidencePage(targetPage);
    }

    setHighlightedEvidenceId(evidenceId);
    setExpandedEvidenceIds((prev) => new Set([...prev, evidenceId]));

    window.setTimeout(() => {
      const element = document.getElementById(`evidence-${evidenceId}`);
      element?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 120);
  }, [evidence, switchTab]);

  const toggleEvidenceExpand = (id: string) => {
    setExpandedEvidenceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSourceExpand = (id: string) => {
    setExpandedSourceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Report loading and regeneration
  async function loadReportVersion(versionNumber: number) {
    try {
      const { id } = await params;
      const loaded = await requestJson<Report>(`/research/investigations/${id}/reports/${versionNumber}`);
      setReport(loaded);
      setSelectedVersion(versionNumber);
    } catch (err) {
      console.error("Failed to load report version", err);
    }
  }

  async function regenerateReportVersion() {
    if (regeneratingReport) return;
    setRegeneratingReport(true);
    try {
      const { id } = await params;
      const regenerated = await requestJson<Report>(`/research/investigations/${id}/reports/generate`, {
        method: "POST",
      });
      setReport(regenerated);
      setSelectedVersion(regenerated.version_number ?? null);
      setAnalysisRefresh((v) => v + 1);
    } catch (err) {
      console.error("Failed to regenerate report", err);
    } finally {
      setRegeneratingReport(false);
    }
  }

  // Trigger Analysis
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
      switchTab("intelligence");
    } catch (reason) {
      setAnalysisError(reason instanceof Error ? reason.message : "Could not start analysis.");
    } finally {
      setSubmittingAnalysis(false);
    }
  }

  // Cancel Analysis
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

  // Authenticated file download handler with zero credential leakage in URLs
  async function handleDownloadExport(endpoint: string, ext: string) {
    if (!investigation) return;
    setDownloadingExport(endpoint);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("neomon_session_token") : null;
      const headers: HeadersInit = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${apiBaseUrl}/research/investigations/${investigation.id}/export/${endpoint}`, {
        headers,
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`Export download failed with status ${res.status}`);
      }
      const blob = await res.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `investigation-${investigation.id}-${endpoint}${ext.toLowerCase()}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error("Export download error:", err);
      alert("Failed to download export file. Please verify network connection or permissions.");
    } finally {
      setDownloadingExport(null);
    }
  }

  // Render citation buttons
  const renderEvidenceButtons = (evidenceIds: string[]) => {
    if (evidenceIds.length === 0) {
      return <small className="muted">No evidence passages cited.</small>;
    }
    return (
      <div className="provenance-links" style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
        {evidenceIds.map((evidenceId, index) => {
          const item = evidenceMap.get(evidenceId);
          const src = item ? sourceMap.get(item.source_id) : undefined;
          const label = src
            ? `[${index + 1}] ${src.title.slice(0, 32)}${src.title.length > 32 ? "…" : ""}${
                item?.page_number ? ` · p.${item.page_number}` : ""
              }`
            : `Passage ${evidenceId.slice(0, 8)}`;
          return (
            <button
              className="evidence-chip"
              key={evidenceId}
              type="button"
              onClick={() => focusEvidence(evidenceId)}
              title="Click to jump directly to this passage in Evidence Explorer"
            >
              {label}
            </button>
          );
        })}
      </div>
    );
  };

  if (error) {
    return (
      <main className="placeholder-page" style={{ padding: "60px 20px", textAlign: "center" }}>
        <p className="connection-result error" style={{ maxWidth: "600px", margin: "0 auto 20px" }}>{error}</p>
        <Link className="outline-button" href="/">
          Return to dashboard
        </Link>
      </main>
    );
  }

  if (!investigation) {
    return (
      <main className="placeholder-page" style={{ padding: "80px 20px", textAlign: "center" }}>
        <p className="eyebrow blue">NEOMON RESEARCH INTELLIGENCE</p>
        <h1 style={{ color: "#f8fafc", marginTop: "12px" }}>Loading scientific investigation...</h1>
      </main>
    );
  }

  const advocateArguments = argumentsList.filter((item) => item.agent_identifier === "advocate");
  const skepticArguments = argumentsList.filter((item) => item.agent_identifier === "skeptic");
  const specialistArguments = argumentsList.filter(
    (item) => item.agent_identifier !== "advocate" && item.agent_identifier !== "skeptic"
  );

  return (
    <div className="inv-workspace-container" style={{ position: "relative" }}>
      {/* Persistent Investigation Header */}
      <header className="inv-workspace-header" style={{ position: "relative", overflow: "hidden" }}>
        <AtmosphericAurora showGrid={true} showScanlines={false} />
        <div className="inv-header-top" style={{ position: "relative", zIndex: 1 }}>
          <div className="inv-breadcrumb-bar">
            <Link href="/">Dashboard</Link>
            <span>/</span>
            <Link href="/history">Investigations</Link>
            <span>/</span>
            <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>MISSION::{investigation.id.slice(0, 8)}</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px" }}>
            <span className="telemetry-beacon">
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  backgroundColor: sseStatus === "connected" ? "#10b981" : sseStatus === "connecting" ? "#f59e0b" : "#f43f5e",
                  boxShadow: sseStatus === "connected" ? "0 0 8px #10b981" : undefined,
                  display: "inline-block",
                }}
              />
              SSE::{sseStatus.toUpperCase()}
              {isJobActive ? " · POLLING_FALLBACK" : ""}
            </span>
          </div>
        </div>

        <div className="inv-header-main" style={{ position: "relative", zIndex: 1 }}>
          <div className="inv-title-group">
            <p className="eyebrow blue" style={{ margin: "0 0 4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>RESEARCH WORKSPACE</span>
              <span>{"//"}</span>
              <span style={{ color: "var(--muted)", fontFamily: "monospace" }}>{investigation.mode?.toUpperCase() || "AUTONOMOUS"}</span>
            </p>
            <h1 className="inv-question-title">{investigation.question}</h1>

            <div className="inv-meta-badges">
              <span className="ready-badge" style={{ textTransform: "uppercase", fontSize: "11px", fontWeight: 700 }}>
                {investigation.status}
              </span>
              <span className="mode-pill">
                ◈ {sources.length} Sources Ingested
              </span>
              <span className="mode-pill">
                ◇ {evidence.length} Traceable Passages
              </span>
              <span className="mode-pill" style={{ borderColor: investigation.quality_status === "verified" ? "#10b981" : undefined }}>
                Quality: <strong style={{ color: "#fff" }}>{investigation.quality_status}</strong>
              </span>
              {analysis?.coverage && (
                <span className={`mode-pill ${analysis.coverage.is_partially_completed ? "status-queued" : "status-completed"}`}>
                  Coverage: {analysis.coverage.coverage_percentage.toFixed(0)}%
                </span>
              )}
            </div>
          </div>

          <div className="inv-header-actions">
            {(!analysis || isJobTerminal) && (
              <button
                className="cyber-primary-btn"
                disabled={submittingAnalysis || isJobActive || (sources.length === 0 && !analysis)}
                type="button"
                onClick={() => void triggerAnalysis()}
                title={sources.length === 0 && !analysis ? "Please discover sources before running analysis" : undefined}
                style={{ padding: "8px 18px", fontSize: "12px" }}
              >
                {submittingAnalysis ? "Starting Analysis..." : analysis ? "↻ Re-run Analysis" : "▶ Start Analysis"}
              </button>
            )}

            {isJobActive && (
              <button
                className="outline-button danger-button compact-button"
                disabled={cancelling || analysis?.cancel_requested}
                type="button"
                onClick={() => void cancelAnalysis()}
              >
                {cancelling || analysis?.cancel_requested ? "Cancelling..." : "⏹ Cancel Analysis"}
              </button>
            )}

            <button
              type="button"
              className="outline-button compact-button"
              onClick={() => setShowExportPanel((v) => !v)}
              style={{ background: showExportPanel ? "rgba(56, 189, 248, 0.15)" : undefined, borderColor: showExportPanel ? "#38bdf8" : undefined }}
            >
              {showExportPanel ? "Hide Exports ▲" : "Export Knowledge ⤓"}
            </button>
          </div>
        </div>
      </header>

      {/* Sticky Tab Navigation Bar */}
      <nav className="inv-tab-nav-bar" aria-label="Investigation Workspace Sections">
        <div className="inv-tab-nav-inner">
          <button
            type="button"
            className={`inv-tab-button ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => switchTab("overview")}
          >
            <span>⌂ Overview</span>
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "intelligence" ? "active" : ""}`}
            onClick={() => switchTab("intelligence")}
          >
            <span>◎ Multi-Agent Intelligence</span>
            {executions.length > 0 && <span className="inv-tab-pill">{executions.length}</span>}
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "evidence" ? "active" : ""}`}
            onClick={() => switchTab("evidence")}
          >
            <span>◇ Evidence Explorer</span>
            <span className="inv-tab-pill">{evidence.length}</span>
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "sources" ? "active" : ""}`}
            onClick={() => switchTab("sources")}
          >
            <span>◈ Sources Library</span>
            <span className="inv-tab-pill">{sources.length}</span>
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "graph" ? "active" : ""}`}
            onClick={() => switchTab("graph")}
          >
            <span>⌘ Knowledge Graph</span>
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "report" ? "active" : ""}`}
            onClick={() => switchTab("report")}
          >
            <span>📄 Research Report</span>
            {report?.evidence_strength && (
              <span className="inv-tab-pill" style={{ color: "#34d399", background: "rgba(16, 185, 129, 0.15)" }}>
                {report.evidence_strength.score.toFixed(0)}/100
              </span>
            )}
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "horizon" ? "active" : ""}`}
            onClick={() => switchTab("horizon")}
          >
            <span>🎯 Research Gaps & Horizon</span>
          </button>

          <button
            type="button"
            className={`inv-tab-button ${activeTab === "collaboration" ? "active" : ""}`}
            onClick={() => switchTab("collaboration")}
          >
            <span>👥 Collaboration & Review</span>
          </button>
        </div>
      </nav>

      {/* Main Workspace Body */}
      <main className="inv-workspace-body">
        {/* Export Panel Dropdown (Available across all tabs when toggled) */}
        {showExportPanel && (
          <section className="export-panel" id="export-panel" style={{ marginBottom: "28px" }}>
            <div className="panel-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>Knowledge Export & Reproducibility</h3>
              <span className="mode-pill">8 Standard Formats</span>
            </div>
            <p className="muted" style={{ fontSize: "12px", margin: "4px 0 14px" }}>
              Export the complete research investigation, interactive knowledge graph, and evidence datasets for peer review, archival, and offline analysis.
            </p>
            <div className="export-grid">
              {[
                {
                  endpoint: "markdown",
                  ext: ".MD",
                  label: "Research Report (Markdown)",
                  desc: "Complete 18-section research report with frontmatter and bibliography.",
                },
                {
                  endpoint: "pdf",
                  ext: ".PDF",
                  label: "Intelligence Report (PDF)",
                  desc: "Paginated PDF document with title header and evidence strength scores.",
                },
                {
                  endpoint: "json",
                  ext: ".JSON",
                  label: "Research Snapshot (JSON)",
                  desc: "Machine-readable research snapshot containing all claims, evidence, and arguments.",
                },
                {
                  endpoint: "html-graph",
                  ext: ".HTML",
                  label: "Interactive Graph (Standalone)",
                  desc: "Single-file interactive graph with pan, zoom, search, and zero CDN dependencies.",
                },
                {
                  endpoint: "svg",
                  ext: ".SVG",
                  label: "Vector Knowledge Graph",
                  desc: "High-resolution vector graphic for publications or vector illustration tools.",
                },
                {
                  endpoint: "json-ld",
                  ext: ".JSONLD",
                  label: "Linked Data (JSON-LD)",
                  desc: "Schema.org ScholarlyArticle & ClaimReview structured metadata.",
                },
                {
                  endpoint: "evidence-csv",
                  ext: ".CSV",
                  label: "Evidence Dataset",
                  desc: "Tabular dataset of all extracted evidence passages with provenance.",
                },
                {
                  endpoint: "sources-csv",
                  ext: ".CSV",
                  label: "Source Catalog",
                  desc: "Tabular catalog of all discovered academic & institutional sources.",
                },
              ].map((f) => {
                const downloadPath = `/research/investigations/${investigation?.id}/export/${f.endpoint}`;
                return (
                  <button
                    key={f.endpoint}
                    type="button"
                    className="export-card"
                    data-path={downloadPath}
                    onClick={() => void handleDownloadExport(f.endpoint, f.ext)}
                    disabled={downloadingExport === f.endpoint}
                    style={{ textAlign: "left", width: "100%", background: "#0e1526", cursor: "pointer", border: "1px solid #1e293b", borderRadius: "8px", padding: "16px" }}
                  >
                    <div className="export-card-header">
                      <strong>{f.label}</strong>
                      <span className="export-ext">{f.ext}</span>
                    </div>
                    <p className="export-card-desc">{f.desc}</p>
                    <div className="export-card-footer">
                      <span className="export-download-pill">
                        {downloadingExport === f.endpoint ? "Downloading..." : `Download ${f.ext} ↓`}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div style={{ display: "grid", gap: "24px" }}>
            {/* Key Metrics Grid */}
            <div className="overview-metric-grid">
              <div className="overview-metric-card hud-card" style={{ padding: "20px" }}>
                <div className="hud-corner-tl" />
                <div className="hud-corner-tr" />
                <div className="hud-corner-bl" />
                <div className="hud-corner-br" />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="overview-metric-label">Literature Ingestion</div>
                  <span style={{ fontSize: "16px", color: "#38bdf8" }}>◈</span>
                </div>
                <div className="overview-metric-value" style={{ margin: "8px 0 4px", fontSize: "28px" }}>{sources.length}</div>
                <div className="overview-metric-subtext">
                  {sources.filter((s) => s.inclusion_status === "included").length} relevant · {sources.filter((s) => s.document_url).length} full text
                </div>
              </div>

              <div className="overview-metric-card hud-card" style={{ padding: "20px" }}>
                <div className="hud-corner-tl" />
                <div className="hud-corner-tr" />
                <div className="hud-corner-bl" />
                <div className="hud-corner-br" />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="overview-metric-label">Evidence Passages</div>
                  <span style={{ fontSize: "16px", color: "#06b6d4" }}>◇</span>
                </div>
                <div className="overview-metric-value" style={{ margin: "8px 0 4px", fontSize: "28px" }}>{evidence.length}</div>
                <div className="overview-metric-subtext">
                  {evidence.filter((e) => e.traceable).length} traceable · {evidenceDistribution.supporting} supporting
                </div>
              </div>

              <div className="overview-metric-card hud-card" style={{ padding: "20px" }}>
                <div className="hud-corner-tl" />
                <div className="hud-corner-tr" />
                <div className="hud-corner-bl" />
                <div className="hud-corner-br" />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="overview-metric-label">Decomposed Claims</div>
                  <span style={{ fontSize: "16px", color: "#a855f7" }}>🔬</span>
                </div>
                <div className="overview-metric-value" style={{ margin: "8px 0 4px", fontSize: "28px" }}>{claims.length}</div>
                <div className="overview-metric-subtext">
                  {decisions.length} adjudicated · {debates.length} debate rounds
                </div>
              </div>

              <div className="overview-metric-card hud-card" style={{ padding: "20px" }}>
                <div className="hud-corner-tl" />
                <div className="hud-corner-tr" />
                <div className="hud-corner-bl" />
                <div className="hud-corner-br" />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="overview-metric-label">Evidence Strength</div>
                  <span style={{ fontSize: "16px", color: "#10b981" }}>🛡️</span>
                </div>
                <div className="overview-metric-value" style={{ margin: "8px 0 4px", fontSize: "28px", color: "#34d399" }}>
                  {report?.evidence_strength ? `${report.evidence_strength.score.toFixed(1)}/100` : "Calibrating"}
                </div>
                <div className="overview-metric-subtext">
                  {report?.evidence_strength?.tier.replace("_", " ").toUpperCase() ?? "Awaiting Synthesis"}
                </div>
              </div>
            </div>

            {/* Evidence Distribution Card */}
            <div className="hud-card" style={{ padding: "24px" }}>
              <div className="hud-corner-tl" />
              <div className="hud-corner-tr" />
              <div className="hud-corner-bl" />
              <div className="hud-corner-br" />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Evidence Classification Distribution</h3>
                <span className="muted" style={{ fontSize: "12px" }}>{evidence.length} total passages</span>
              </div>
              <p className="muted" style={{ fontSize: "12px", margin: "0 0 12px" }}>
                Distribution of extracted scientific evidence across supporting proofs, direct contradictions, contextual background, and methodological limitations.
              </p>

              {evidence.length > 0 ? (
                <>
                  <div className="distribution-bar-track">
                    <div
                      className="distribution-segment"
                      style={{
                        width: `${(evidenceDistribution.supporting / evidence.length) * 100}%`,
                        backgroundColor: "#10b981",
                      }}
                      title={`Supporting: ${evidenceDistribution.supporting}`}
                    />
                    <div
                      className="distribution-segment"
                      style={{
                        width: `${(evidenceDistribution.contradicting / evidence.length) * 100}%`,
                        backgroundColor: "#f43f5e",
                      }}
                      title={`Contradicting: ${evidenceDistribution.contradicting}`}
                    />
                    <div
                      className="distribution-segment"
                      style={{
                        width: `${(evidenceDistribution.contextual / evidence.length) * 100}%`,
                        backgroundColor: "#0284c7",
                      }}
                      title={`Contextual: ${evidenceDistribution.contextual}`}
                    />
                    <div
                      className="distribution-segment"
                      style={{
                        width: `${(evidenceDistribution.limitations / evidence.length) * 100}%`,
                        backgroundColor: "#8b5cf6",
                      }}
                      title={`Limitations: ${evidenceDistribution.limitations}`}
                    />
                    <div
                      className="distribution-segment"
                      style={{
                        width: `${(evidenceDistribution.unassessed / evidence.length) * 100}%`,
                        backgroundColor: "#f59e0b",
                      }}
                      title={`Unassessed: ${evidenceDistribution.unassessed}`}
                    />
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", fontSize: "12px", marginTop: "12px" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: "#10b981" }} />
                      Supporting: <strong>{evidenceDistribution.supporting}</strong>
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: "#f43f5e" }} />
                      Contradicting: <strong>{evidenceDistribution.contradicting}</strong>
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: "#0284c7" }} />
                      Contextual: <strong>{evidenceDistribution.contextual}</strong>
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: "#8b5cf6" }} />
                      Limitations: <strong>{evidenceDistribution.limitations}</strong>
                    </span>
                    {evidenceDistribution.unassessed > 0 && (
                      <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ width: "10px", height: "10px", borderRadius: "2px", backgroundColor: "#f59e0b" }} />
                        Unassessed: <strong>{evidenceDistribution.unassessed}</strong>
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <p className="muted" style={{ fontSize: "13px" }}>No evidence passages extracted yet.</p>
              )}
            </div>

            {/* Quality Assessment & Warnings */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "20px" }}>
              <div className="panel" style={{ padding: "20px" }}>
                <h3 style={{ margin: "0 0 10px", fontSize: "15px", fontWeight: 600 }}>
                  Scientific Quality Status: <span style={{ color: "#38bdf8" }}>{investigation.quality_status}</span>
                </h3>
                <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: 1.6, margin: "0 0 12px" }}>
                  {investigation.quality_summary ?? "Standard autonomous quality calibration active."}
                </p>
                {investigation.evidence_gap && (
                  <div className="connection-result error" style={{ fontSize: "12px", marginTop: "10px" }}>
                    <strong>Evidence Gap Detected:</strong> {investigation.evidence_gap}
                  </div>
                )}
              </div>

              {/* Multi-Agent Execution Highlights */}
              <div className="panel" style={{ padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ margin: 0, fontSize: "15px", fontWeight: 600 }}>Multi-Agent Execution Summary</h3>
                  <button
                    type="button"
                    className="outline-button compact-button"
                    onClick={() => switchTab("intelligence")}
                    style={{ fontSize: "11px" }}
                  >
                    View Agent Workspace →
                  </button>
                </div>

                <div style={{ fontSize: "13px", color: "#94a3b8", display: "grid", gap: "8px" }}>
                  <div>
                    Stage: <strong style={{ color: "#f8fafc" }}>{analysis?.status ?? "Not initiated"}</strong> · Provider:{" "}
                    <strong style={{ color: "#f8fafc" }}>{analysis?.provider_kind ?? "Rule-based"}</strong>
                  </div>
                  <div>
                    Active Agent Pool: <strong style={{ color: "#f8fafc" }}>{executions.length} agents</strong> (
                    {executions.filter((e) => e.status === "completed").length} completed,{" "}
                    {executions.filter((e) => e.status === "generating" || e.status === "running").length} running)
                  </div>
                  {debates.length > 0 && (
                    <div>
                      Adversarial Dialectic: <strong style={{ color: "#f8fafc" }}>{debates.length} moderation rounds</strong> with{" "}
                      <strong style={{ color: "#f8fafc" }}>{argumentsList.length} arguments</strong>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Launch Hub */}
            <div className="panel" style={{ padding: "20px" }}>
              <h3 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 600 }}>Dedicated Workspace Navigation</h3>
              <div className="workspace-quick-links" style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("intelligence")}
                >
                  ⚡ Multi-Agent Intelligence ({executions.length})
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("evidence")}
                >
                  🔍 Evidence Explorer ({evidence.length})
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("sources")}
                >
                  📚 Sources Library ({sources.length})
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("graph")}
                >
                  🕸️ Knowledge Graph
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("report")}
                >
                  📄 Research Report {report?.evidence_strength ? `(${report.evidence_strength.score.toFixed(0)}/100)` : ""}
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("horizon")}
                  style={{ borderColor: "#f97316", color: "#f97316" }}
                >
                  🎯 Research Gaps & Horizon
                </button>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => switchTab("collaboration")}
                  style={{ borderColor: "#38bdf8", color: "#38bdf8" }}
                >
                  💬 Collaboration & Review
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: MULTI-AGENT INTELLIGENCE */}
        {activeTab === "intelligence" && (
          <section className="panel analysis-panel" style={{ marginTop: 0 }}>
            <div className="panel-heading analysis-header" style={{ marginBottom: "20px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 4px" }}>Multi-Agent Intelligence</h3>
                <p className="muted" style={{ margin: 0, fontSize: "12px" }}>
                  {sessionProvider?.connected ? (
                    <>
                      Active session provider: <strong>{sessionProvider.kind}</strong> ({sessionProvider.model ?? "default model"})
                    </>
                  ) : (
                    <>
                      Rule-based research & debate orchestration active. Configure external LLM providers in{" "}
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
                    className="primary-button compact-button"
                    disabled={submittingAnalysis || isJobActive || (sources.length === 0 && !analysis)}
                    type="button"
                    onClick={() => void triggerAnalysis()}
                    title={sources.length === 0 && !analysis ? "Please discover sources before running analysis" : undefined}
                    style={{ background: "#2563eb", color: "#fff" }}
                  >
                    {submittingAnalysis ? "Starting..." : analysis ? "↻ Re-run Analysis" : "▶ Start Analysis"}
                  </button>
                )}

                {isJobActive && (
                  <button
                    className="outline-button danger-button compact-button"
                    disabled={cancelling || analysis?.cancel_requested}
                    type="button"
                    onClick={() => void cancelAnalysis()}
                  >
                    {cancelling || analysis?.cancel_requested ? "Cancelling..." : "⏹ Cancel Analysis"}
                  </button>
                )}
              </div>
            </div>

            {analysisError && <p className="connection-result error">{analysisError}</p>}

            {analysis ? (
              <div className="analysis-body">
                {/* Status Bar */}
                <div className="analysis-status-bar" style={{ background: "rgba(14, 20, 34, 0.6)", padding: "12px 16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                  <span>
                    Current stage: <strong style={{ color: "#38bdf8" }}>{analysis.status}</strong>
                  </span>
                  <span className="mode-pill">
                    {analysis.provider_kind
                      ? `Provider: ${analysis.provider_kind}${analysis.default_model ? ` · ${analysis.default_model}` : ""}`
                      : "Rule-based execution"}
                  </span>
                  {analysis.coverage && (
                    <span className={`mode-pill ${analysis.coverage.is_partially_completed ? "status-queued" : "status-completed"}`}>
                      Coverage: {analysis.coverage.coverage_percentage.toFixed(0)}% ({analysis.coverage.completed_agents.length}/{analysis.coverage.required_agents.length} agents)
                    </span>
                  )}
                  {executions.length > 0 && (
                    <span className="muted">
                      {executions.filter((item) => item.status === "generating" || item.status === "running").length} generating ·{" "}
                      {executions.filter((item) => item.status === "waiting_in_queue" || item.status === "queued").length} waiting ·{" "}
                      {executions.filter((item) => item.status === "completed").length} completed
                    </span>
                  )}
                  {analysis.cancel_requested && <span className="muted">Cancellation requested</span>}
                  {analysis.status === "completed_with_warnings" && (
                    <span className="connection-result warning">Investigation completed with warnings. Fallback synthesis active.</span>
                  )}
                  {analysis.error_message && <span className="connection-result error">{analysis.error_message}</span>}
                </div>

                {/* Agent Execution Grid */}
                {executions.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "14px", fontWeight: 600, color: "#cbd5e1", margin: "0 0 10px" }}>
                      Agent Execution Pool ({executions.length})
                    </h4>
                    <div className="execution-grid">
                      {executions.map((execution) => (
                        <div className="source-row" key={execution.id} style={{ padding: "12px" }}>
                          <div className="row-header" style={{ marginBottom: "4px" }}>
                            <strong style={{ fontSize: "13px" }}>{execution.agent_identifier}</strong>
                            <span className={`exec-status-badge ${executionStatusClass(execution.status)}`}>
                              {formatExecutionStatus(execution.status, execution.queue_position)}
                            </span>
                          </div>
                          <small style={{ fontSize: "11px", color: "#94a3b8" }}>
                            {execution.model ?? "rule_based"}
                            {execution.queue_wait_seconds ? ` · wait ${execution.queue_wait_seconds.toFixed(1)}s` : ""}
                            {execution.inference_duration_seconds ? ` · gen ${execution.inference_duration_seconds.toFixed(1)}s` : ""}
                            {execution.error_message ? ` · ${execution.error_message}` : ""}
                          </small>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Decomposed Claims */}
                {claims.length > 0 && (
                  <div className="analysis-subsection" style={{ marginTop: "16px" }}>
                    <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 12px" }}>
                      Decomposed Scientific Claims ({claims.length})
                    </h4>
                    <div className="source-list" style={{ gap: "12px" }}>
                      {claims.map((claim) => {
                        const claimEvidence = evidence.filter((item) => item.claim_id === claim.id);
                        const citedByArguments = Array.from(
                          new Set(
                            argumentsList
                              .filter((arg) => arg.claim_id === claim.id)
                              .flatMap((arg) => arg.evidence_ids)
                          )
                        );
                        const linkedIds = Array.from(new Set([...claimEvidence.map((item) => item.id), ...citedByArguments]));
                        return (
                          <div className="source-row" key={claim.id} style={{ padding: "16px" }}>
                            <div className="row-header" style={{ marginBottom: "6px" }}>
                              <strong style={{ fontSize: "14px", color: "#f8fafc" }}>
                                P{claim.priority}: {claim.text}
                              </strong>
                              <span className="ready-badge">{claim.status}</span>
                            </div>
                            <p className="muted" style={{ margin: "0 0 8px", fontSize: "13px" }}>{claim.explanation}</p>
                            {claim.search_objectives.length > 0 && (
                              <small style={{ color: "#94a3b8", display: "block", marginBottom: "8px" }}>
                                Objectives: {claim.search_objectives.join(" · ")}
                              </small>
                            )}
                            {renderEvidenceButtons(linkedIds)}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Adversarial Analysis: Advocate vs Skeptic */}
                {argumentsList.length > 0 && (
                  <div className="analysis-subsection" style={{ marginTop: "20px" }}>
                    <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 14px" }}>
                      Adversarial Analysis: Advocate vs. Skeptic
                    </h4>
                    <div className="argument-columns">
                      <div className="argument-column advocate-column">
                        <h5 style={{ color: "#34d399", margin: "0 0 12px", fontSize: "14px", fontWeight: 600 }}>
                          Advocate ({advocateArguments.length})
                        </h5>
                        {advocateArguments.length === 0 ? (
                          <p className="muted">No Advocate arguments persisted.</p>
                        ) : (
                          advocateArguments.map((arg) => (
                            <div className="source-row" key={arg.id} style={{ padding: "14px" }}>
                              <div className="row-header" style={{ marginBottom: "6px" }}>
                                <strong style={{ fontSize: "13px" }}>{claimMap.get(arg.claim_id)?.text ?? "Claim"}</strong>
                                <span className="ready-badge" style={{ color: "#34d399" }}>{arg.confidence.level}</span>
                              </div>
                              <p style={{ margin: "0 0 6px", fontSize: "13px", lineHeight: 1.5 }}>{arg.text}</p>
                              <small style={{ color: "#94a3b8", display: "block", marginBottom: "6px" }}>{arg.reasoning_summary}</small>
                              {renderEvidenceButtons(arg.evidence_ids)}
                            </div>
                          ))
                        )}
                      </div>

                      <div className="argument-column skeptic-column">
                        <h5 style={{ color: "#fb7185", margin: "0 0 12px", fontSize: "14px", fontWeight: 600 }}>
                          Skeptic ({skepticArguments.length})
                        </h5>
                        {skepticArguments.length === 0 ? (
                          <p className="muted">No Skeptic arguments persisted.</p>
                        ) : (
                          skepticArguments.map((arg) => (
                            <div className="source-row" key={arg.id} style={{ padding: "14px" }}>
                              <div className="row-header" style={{ marginBottom: "6px" }}>
                                <strong style={{ fontSize: "13px" }}>{claimMap.get(arg.claim_id)?.text ?? "Claim"}</strong>
                                <span className="ready-badge" style={{ color: "#fb7185" }}>{arg.confidence.level}</span>
                              </div>
                              <p style={{ margin: "0 0 6px", fontSize: "13px", lineHeight: 1.5 }}>{arg.text}</p>
                              <small style={{ color: "#94a3b8", display: "block", marginBottom: "6px" }}>{arg.reasoning_summary}</small>
                              {renderEvidenceButtons(arg.evidence_ids)}
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {specialistArguments.length > 0 && (
                      <div className="specialist-section" style={{ marginTop: "20px" }}>
                        <h5 style={{ fontSize: "14px", fontWeight: 600, color: "#cbd5e1", margin: "0 0 10px" }}>
                          Specialist Assessments ({specialistArguments.length})
                        </h5>
                        <div className="source-list">
                          {specialistArguments.map((arg) => (
                            <div className="source-row" key={arg.id} style={{ padding: "14px" }}>
                              <div className="row-header" style={{ marginBottom: "4px" }}>
                                <strong>{arg.agent_identifier} · {arg.argument_type}</strong>
                                <span className="ready-badge">{arg.confidence.level}</span>
                              </div>
                              <small style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                Claim: {claimMap.get(arg.claim_id)?.text ?? arg.claim_id}
                              </small>
                              <p style={{ margin: "0 0 6px", fontSize: "13px" }}>{arg.text}</p>
                              {arg.limitations.length > 0 && (
                                <small style={{ color: "#a855f7", display: "block", marginBottom: "6px" }}>
                                  Limitations: {arg.limitations.join(" · ")}
                                </small>
                              )}
                              {renderEvidenceButtons(arg.evidence_ids)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Debate Moderation Rounds */}
                {debates.length > 0 && (
                  <div className="analysis-subsection" style={{ marginTop: "20px" }}>
                    <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 12px" }}>
                      Debate Moderation ({debates.length} round(s))
                    </h4>
                    <div className="source-list">
                      {debates.map((debate) => (
                        <div className="source-row" key={debate.id} style={{ padding: "16px" }}>
                          <strong style={{ fontSize: "14px" }}>Debate Round {debate.round_number}</strong>
                          <p style={{ fontSize: "13px", color: "#cbd5e1", margin: "6px 0 10px" }}>{debate.moderator_summary}</p>
                          {debate.unresolved_disagreements.map((item) => (
                            <small key={item} className="connection-result error" style={{ display: "block", margin: "4px 0" }}>
                              Unresolved Disagreement: {item}
                            </small>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Adjudication Decisions */}
                {decisions.length > 0 && (
                  <div className="analysis-subsection" style={{ marginTop: "20px" }}>
                    <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 12px" }}>
                      Adjudication Decisions ({decisions.length})
                    </h4>
                    <div className="evidence-list">
                      {decisions.map((decision) => (
                        <blockquote key={decision.id} style={{ padding: "16px" }}>
                          <strong style={{ fontSize: "14px", color: "#f8fafc" }}>
                            {claimMap.get(decision.claim_id)?.text ?? decision.claim_id} —{" "}
                            <span style={{ color: decision.decision === "accepted" ? "#34d399" : decision.decision === "rejected" ? "#fb7185" : "#38bdf8" }}>
                              {decision.decision.toUpperCase()}
                            </span>
                          </strong>
                          <p style={{ fontSize: "13px", margin: "8px 0" }}>{decision.explanation}</p>
                          {renderEvidenceButtons(decision.evidence_ids)}
                        </blockquote>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <p className="muted" style={{ margin: "0 0 16px" }}>
                  No multi-agent analysis has been run for this investigation yet.
                </p>
                <button
                  className="primary-button compact-button"
                  disabled={submittingAnalysis}
                  type="button"
                  onClick={() => void triggerAnalysis()}
                  style={{ background: "#2563eb", color: "#fff" }}
                >
                  ▶ Launch Autonomous Analysis & Debate
                </button>
              </div>
            )}
          </section>
        )}

        {/* TAB 3: EVIDENCE EXPLORER */}
        {activeTab === "evidence" && (
          <div style={{ display: "grid", gap: "20px" }}>
            {/* Epistemological Guidance Callout (Replaces repeated explanations on individual cards) */}
            {showGuidanceCallout && (
              <div className="guidance-callout">
                <div className="guidance-callout-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "16px" }}>🛡️</span>
                    <strong style={{ fontSize: "13px", color: "#f0f9ff" }}>
                      Scientific Evidence Calibration Principles
                    </strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowGuidanceCallout(false)}
                    style={{ background: "transparent", border: "none", color: "#64748b", cursor: "pointer", fontSize: "14px" }}
                    title="Dismiss guidance callout"
                  >
                    ✕
                  </button>
                </div>

                <div className="guidance-callout-grid">
                  <div className="guidance-item">
                    <strong>1. Relevance ≠ Truth Probability</strong>
                    A high relevance score indicates semantic match with the claim, not empirical truth.
                  </div>
                  <div className="guidance-item">
                    <strong>2. Relevance ≠ Source Credibility</strong>
                    Authoritative calibration and peer-review rigor are assessed independently of query relevance.
                  </div>
                  <div className="guidance-item">
                    <strong>3. Contextual ≠ Direct Proof</strong>
                    Contextual passages provide definitional and background grounding without establishing direct proof.
                  </div>
                  <div className="guidance-item">
                    <strong>4. Claim-Level Assessment</strong>
                    Evidence classification is adjudicated through adversarial debate and contradiction checks.
                  </div>
                </div>
              </div>
            )}

            {/* Evidence Control Bar: Search, Filters, Sorters */}
            <div className="panel" style={{ padding: "18px 20px" }}>
              <div style={{ display: "grid", gap: "14px" }}>
                {/* Search & Main Selectors */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", alignItems: "center" }}>
                  {/* Text Search */}
                  <div>
                    <input
                      type="text"
                      placeholder="Search passages, sections, or reasons..."
                      value={evidenceSearch}
                      onChange={(e) => {
                        setEvidenceSearch(e.target.value);
                        setEvidencePage(1);
                      }}
                      style={{
                        width: "100%",
                        padding: "8px 12px",
                        background: "#080c15",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        color: "#fff",
                        fontSize: "12px",
                      }}
                    />
                  </div>

                  {/* Classification Filter */}
                  <div>
                    <select
                      value={evidenceFilter}
                      onChange={(e) => {
                        setEvidenceFilter(e.target.value);
                        setEvidencePage(1);
                      }}
                      style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                    >
                      <option value="all">All Classifications ({evidence.length})</option>
                      <option value="supporting">Direct Supporting ({evidenceDistribution.supporting})</option>
                      <option value="contradicting">Direct Contradicting ({evidenceDistribution.contradicting})</option>
                      <option value="contextual">Contextual Background ({evidenceDistribution.contextual})</option>
                      <option value="methodological_limitation">Methodological Limitations ({evidenceDistribution.limitations})</option>
                      <option value="insufficient">Unassessed / Insufficient ({evidenceDistribution.unassessed})</option>
                    </select>
                  </div>

                  {/* Claim Filter */}
                  <div>
                    <select
                      value={evidenceClaimFilter}
                      onChange={(e) => {
                        setEvidenceClaimFilter(e.target.value);
                        setEvidencePage(1);
                      }}
                      style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                    >
                      <option value="all">All Associated Claims ({claims.length})</option>
                      {claims.map((c) => (
                        <option key={c.id} value={c.id}>
                          P{c.priority}: {c.text.slice(0, 40)}...
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Source Filter */}
                  <div>
                    <select
                      value={evidenceSourceFilter}
                      onChange={(e) => {
                        setEvidenceSourceFilter(e.target.value);
                        setEvidencePage(1);
                      }}
                      style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                    >
                      <option value="all">All Sources ({sources.length})</option>
                      {sources.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.title.slice(0, 40)}...
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Sub-Filters: Relevance, Traceable, Sorter, Reset */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                    {/* Minimum Relevance */}
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#94a3b8" }}>
                      <span>Relevance:</span>
                      <select
                        value={evidenceMinRelevance}
                        onChange={(e) => {
                          setEvidenceMinRelevance(e.target.value);
                          setEvidencePage(1);
                        }}
                        style={{ padding: "4px 8px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "4px", color: "#fff", fontSize: "11px" }}
                      >
                        <option value="all">All Scores</option>
                        <option value="0.8">High (≥ 0.8)</option>
                        <option value="0.5">Moderate (≥ 0.5)</option>
                      </select>
                    </div>

                    {/* Traceable Toggle */}
                    <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#cbd5e1", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={evidenceTraceableOnly}
                        onChange={(e) => {
                          setEvidenceTraceableOnly(e.target.checked);
                          setEvidencePage(1);
                        }}
                      />
                      <span>Traceable Passages Only</span>
                    </label>

                    {/* Sorter */}
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#94a3b8" }}>
                      <span>Sort:</span>
                      <select
                        value={evidenceSort}
                        onChange={(e) => setEvidenceSort(e.target.value as typeof evidenceSort)}
                        style={{ padding: "4px 8px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "4px", color: "#fff", fontSize: "11px" }}
                      >
                        <option value="relevance_desc">Relevance (High → Low)</option>
                        <option value="relevance_asc">Relevance (Low → High)</option>
                        <option value="source_title">Source Title (A → Z)</option>
                        <option value="type">Evidence Classification</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                      Showing <strong>{filteredEvidence.length}</strong> of {evidence.length} passages
                    </span>

                    {(evidenceFilter !== "all" ||
                      evidenceClaimFilter !== "all" ||
                      evidenceSourceFilter !== "all" ||
                      evidenceSearch ||
                      evidenceMinRelevance !== "all" ||
                      evidenceTraceableOnly) && (
                      <button
                        type="button"
                        onClick={() => {
                          setEvidenceFilter("all");
                          setEvidenceClaimFilter("all");
                          setEvidenceSourceFilter("all");
                          setEvidenceSearch("");
                          setEvidenceMinRelevance("all");
                          setEvidenceTraceableOnly(false);
                          setEvidencePage(1);
                        }}
                        style={{ background: "transparent", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "11px", textDecoration: "underline" }}
                      >
                        Clear Filters
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Evidence Cards List */}
            {paginatedEvidence.length === 0 ? (
              <div className="panel" style={{ padding: "40px", textAlign: "center" }}>
                <p className="muted" style={{ margin: 0 }}>No evidence passages match your current search and filter criteria.</p>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                {paginatedEvidence.map((item) => {
                  const src = sourceMap.get(item.source_id);
                  const isExpanded = expandedEvidenceIds.has(item.id);
                  const isHighlighted = highlightedEvidenceId === item.id;
                  const badge = evidenceClassificationBadge(item.evidence_type);
                  const linkedClaim = item.claim_id ? claimMap.get(item.claim_id) : undefined;

                  return (
                    <article
                      key={item.id}
                      id={`evidence-${item.id}`}
                      className={`evidence-workspace-card ${isHighlighted ? "highlighted" : ""}`}
                    >
                      {/* Compact Card Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "8px", flexWrap: "wrap" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                          <span className={`exec-status-badge ${badge.className}`}>
                            {badge.label}
                          </span>

                          <span className="mode-pill" style={{ borderColor: item.relevance_score >= 0.8 ? "rgba(16, 185, 129, 0.4)" : undefined }}>
                            Relevance: <strong>{item.relevance_score.toFixed(2)}</strong>
                          </span>

                          {item.traceable && (
                            <span className="mode-pill" style={{ color: "#38bdf8", borderColor: "rgba(56, 189, 248, 0.3)" }}>
                              ✓ Traceable
                            </span>
                          )}

                          {item.page_number && (
                            <span className="mode-pill" style={{ fontSize: "10px" }}>
                              p. {item.page_number}
                            </span>
                          )}

                          {item.section_name && (
                            <span className="mode-pill" style={{ fontSize: "10px" }}>
                              § {item.section_name}
                            </span>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => toggleEvidenceExpand(item.id)}
                          style={{
                            background: "transparent",
                            border: "1px solid var(--border)",
                            color: "#94a3b8",
                            padding: "3px 10px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            cursor: "pointer",
                          }}
                        >
                          {isExpanded ? "Collapse ▲" : "Inspect Provenance ▼"}
                        </button>
                      </div>

                      {/* Excerpt Body */}
                      <blockquote
                        style={{
                          margin: "6px 0 10px",
                          padding: "10px 14px",
                          borderLeft: `3px solid ${item.evidence_type === "supporting" ? "#10b981" : item.evidence_type === "contradicting" ? "#f43f5e" : "#0284c7"}`,
                          background: "rgba(8, 12, 21, 0.5)",
                          borderRadius: "0 6px 6px 0",
                        }}
                      >
                        <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.6, color: "#f1f5f9" }}>
                          {isExpanded ? item.exact_text : (item.exact_text.length > 220 ? `${item.exact_text.slice(0, 220)}…` : item.exact_text)}
                        </p>
                      </blockquote>

                      {/* Card Footer: Attribution & Claim Linking */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "#94a3b8", flexWrap: "wrap", gap: "8px" }}>
                        <div>
                          {src && (
                            <span>
                              Source:{" "}
                              <a
                                href={src.original_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-link"
                                style={{ fontWeight: 500 }}
                              >
                                {src.title}
                              </a>{" "}
                              ({src.publisher ?? src.source_type})
                            </span>
                          )}
                        </div>

                        {linkedClaim && (
                          <div style={{ fontSize: "11px", color: "#cbd5e1" }}>
                            Linked Claim: <strong>P{linkedClaim.priority}</strong> {linkedClaim.text.slice(0, 35)}...
                          </div>
                        )}
                      </div>

                      {/* Expanded Provenance & Full Passage Details */}
                      {isExpanded && (
                        <div
                          style={{
                            marginTop: "14px",
                            paddingTop: "14px",
                            borderTop: "1px solid var(--border)",
                            display: "grid",
                            gap: "10px",
                            fontSize: "12px",
                            background: "rgba(14, 20, 34, 0.5)",
                            padding: "14px",
                            borderRadius: "6px",
                          }}
                        >
                          {item.surrounding_context && (
                            <div>
                              <strong style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                Surrounding Context in Document:
                              </strong>
                              <p style={{ margin: 0, color: "#cbd5e1", fontSize: "12px", fontStyle: "italic", lineHeight: 1.5 }}>
                                &ldquo;{item.surrounding_context}&rdquo;
                              </p>
                            </div>
                          )}

                          <div>
                            <strong style={{ color: "#94a3b8", display: "block", marginBottom: "3px" }}>
                              Assessment Rationale:
                            </strong>
                            <p style={{ margin: 0, color: "#f8fafc" }}>{item.relevance_reason}</p>
                          </div>

                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px", marginTop: "4px" }}>
                            <div>
                              <span style={{ color: "#64748b" }}>Extraction Method:</span>{" "}
                              <span style={{ color: "#cbd5e1" }}>{item.extraction_method}</span>
                            </div>
                            {item.retrieval_timestamp && (
                              <div>
                                <span style={{ color: "#64748b" }}>Ingested:</span>{" "}
                                <span style={{ color: "#cbd5e1" }}>{new Date(item.retrieval_timestamp).toLocaleString()}</span>
                              </div>
                            )}
                            {src?.document_url && (
                              <div>
                                <a
                                  href={src.document_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-link"
                                  style={{ fontWeight: 600 }}
                                >
                                  Open Retrieved Document ↗
                                </a>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}

            {/* Pagination Controls */}
            {totalEvidencePages > 1 && (
              <div className="inv-pagination-bar">
                <span>
                  Page <strong>{evidencePage}</strong> of <strong>{totalEvidencePages}</strong>
                </span>

                <div className="inv-pagination-controls">
                  <button
                    type="button"
                    className="inv-page-button"
                    disabled={evidencePage <= 1}
                    onClick={() => setEvidencePage((p) => Math.max(1, p - 1))}
                  >
                    ← Previous
                  </button>

                  {Array.from({ length: totalEvidencePages }, (_, i) => i + 1)
                    .filter((p) => p === 1 || p === totalEvidencePages || Math.abs(p - evidencePage) <= 2)
                    .map((p, idx, arr) => (
                      <React.Fragment key={p}>
                        {idx > 0 && arr[idx - 1] !== p - 1 && <span style={{ padding: "0 4px", color: "#64748b" }}>…</span>}
                        <button
                          type="button"
                          className={`inv-page-button ${evidencePage === p ? "active" : ""}`}
                          onClick={() => setEvidencePage(p)}
                        >
                          {p}
                        </button>
                      </React.Fragment>
                    ))}

                  <button
                    type="button"
                    className="inv-page-button"
                    disabled={evidencePage >= totalEvidencePages}
                    onClick={() => setEvidencePage((p) => Math.min(totalEvidencePages, p + 1))}
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: SOURCES LIBRARY */}
        {activeTab === "sources" && (
          <div style={{ display: "grid", gap: "20px" }}>
            {/* Sources Control Bar */}
            <div className="panel" style={{ padding: "18px 20px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", alignItems: "center" }}>
                {/* Search */}
                <div>
                  <input
                    type="text"
                    placeholder="Search by title, publisher, or URL..."
                    value={sourceSearch}
                    onChange={(e) => {
                      setSourceSearch(e.target.value);
                      setSourcePage(1);
                    }}
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      background: "#080c15",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                </div>

                {/* Inclusion Status Filter */}
                <div>
                  <select
                    value={sourceFilter}
                    onChange={(e) => {
                      setSourceFilter(e.target.value);
                      setSourcePage(1);
                    }}
                    style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                  >
                    <option value="all">All Sources ({sources.length})</option>
                    <option value="included">Relevant / Included ({sources.filter((s) => s.inclusion_status === "included").length})</option>
                    <option value="filtered">Filtered / Low Relevance ({sources.filter((s) => s.inclusion_status === "filtered").length})</option>
                  </select>
                </div>

                {/* Access Level Filter */}
                <div>
                  <select
                    value={sourceAccessFilter}
                    onChange={(e) => {
                      setSourceAccessFilter(e.target.value);
                      setSourcePage(1);
                    }}
                    style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                  >
                    <option value="all">All Access Levels</option>
                    <option value="open_access">Open Access</option>
                    <option value="metadata_only">Metadata Only</option>
                  </select>
                </div>

                {/* Sorter */}
                <div>
                  <select
                    value={sourceSort}
                    onChange={(e) => setSourceSort(e.target.value as typeof sourceSort)}
                    style={{ width: "100%", padding: "8px 10px", background: "#080c15", border: "1px solid var(--border)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                  >
                    <option value="relevance_desc">Relevance Score (High → Low)</option>
                    <option value="title_asc">Title (A → Z)</option>
                    <option value="publisher">Publisher</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Sources List */}
            {paginatedSources.length === 0 ? (
              <div className="panel" style={{ padding: "40px", textAlign: "center" }}>
                <p className="muted" style={{ margin: 0 }}>No sources match your current filter criteria.</p>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                {paginatedSources.map((source) => {
                  const isExpanded = expandedSourceIds.has(source.id);
                  const sourceEvidence = evidence.filter((e) => e.source_id === source.id);

                  return (
                    <div key={source.id} className="source-row" style={{ padding: "16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "8px", flexWrap: "wrap" }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <a
                            href={source.original_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ textDecoration: "none", color: "inherit" }}
                          >
                            <strong style={{ fontSize: "15px", color: "#f8fafc", lineHeight: 1.4, display: "block", marginBottom: "4px" }}>
                              {source.title}
                            </strong>
                          </a>

                          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", fontSize: "12px", color: "#94a3b8" }}>
                            <span>{source.publisher ?? source.source_type}</span>
                            <span>·</span>
                            <span className="mode-pill" style={{ borderColor: source.inclusion_status === "included" ? "#10b981" : undefined }}>
                              {source.inclusion_status}
                            </span>
                            <span className="mode-pill">
                              Relevance: <strong>{source.relevance_score.toFixed(2)}</strong>
                            </span>
                            {source.open_access_status && (
                              <span className="mode-pill" style={{ color: "#34d399" }}>
                                {source.open_access_status}
                              </span>
                            )}
                            <span className="mode-pill">
                              {sourceEvidence.length} Extracted Passages
                            </span>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {source.document_url && (
                            <a
                              href={source.document_url}
                              target="_blank"
                              rel="noreferrer"
                              className="outline-button compact-button"
                              style={{ textDecoration: "none", fontSize: "11px" }}
                            >
                              Open Document ↗
                            </a>
                          )}
                          <button
                            type="button"
                            className="outline-button compact-button"
                            onClick={() => toggleSourceExpand(source.id)}
                            style={{ fontSize: "11px" }}
                          >
                            {isExpanded ? "Hide Passages ▲" : `View Passages (${sourceEvidence.length}) ▼`}
                          </button>
                        </div>
                      </div>

                      {/* Expandable Source Passages & Details */}
                      {isExpanded && (
                        <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "grid", gap: "12px" }}>
                          <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                            Original URL:{" "}
                            <a href={source.original_url} target="_blank" rel="noreferrer" className="inline-link">
                              {source.original_url}
                            </a>
                            {source.version_type && <span> · Version: {source.version_type}</span>}
                            {source.rejection_reason && <span> · Filter reason: {source.rejection_reason}</span>}
                          </div>

                          <h5 style={{ fontSize: "13px", fontWeight: 600, color: "#cbd5e1", margin: "4px 0" }}>
                            Extracted Passages from this Source ({sourceEvidence.length})
                          </h5>

                          {sourceEvidence.length === 0 ? (
                            <p className="muted" style={{ fontSize: "12px" }}>No passages extracted from this source.</p>
                          ) : (
                            <div style={{ display: "grid", gap: "8px" }}>
                              {sourceEvidence.map((ev) => {
                                const badge = evidenceClassificationBadge(ev.evidence_type);
                                return (
                                  <div
                                    key={ev.id}
                                    style={{
                                      background: "rgba(8, 12, 21, 0.6)",
                                      padding: "10px 14px",
                                      borderRadius: "6px",
                                      border: "1px solid var(--border)",
                                      fontSize: "12px",
                                    }}
                                  >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                                      <span className={`exec-status-badge ${badge.className}`}>{badge.label}</span>
                                      <button
                                        type="button"
                                        onClick={() => focusEvidence(ev.id)}
                                        style={{ background: "transparent", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "11px" }}
                                      >
                                        Inspect in Evidence Explorer →
                                      </button>
                                    </div>
                                    <p style={{ margin: 0, color: "#e2e8f0", lineHeight: 1.5 }}>{ev.exact_text}</p>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Source Pagination */}
            {totalSourcePages > 1 && (
              <div className="inv-pagination-bar">
                <span>Page <strong>{sourcePage}</strong> of <strong>{totalSourcePages}</strong></span>
                <div className="inv-pagination-controls">
                  <button
                    type="button"
                    className="inv-page-button"
                    disabled={sourcePage <= 1}
                    onClick={() => setSourcePage((p) => Math.max(1, p - 1))}
                  >
                    ← Previous
                  </button>
                  <button
                    type="button"
                    className="inv-page-button"
                    disabled={sourcePage >= totalSourcePages}
                    onClick={() => setSourcePage((p) => Math.min(totalSourcePages, p + 1))}
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: KNOWLEDGE GRAPH */}
        {activeTab === "graph" && (
          <div className="panel" style={{ padding: "30px", textAlign: "center" }}>
            <h3 style={{ fontSize: "18px", fontWeight: 700, margin: "0 0 10px" }}>Interactive Knowledge Graph</h3>
            <p className="muted" style={{ maxWidth: "600px", margin: "0 auto 24px", fontSize: "13px" }}>
              Explore the dialectical relationship network between decomposed claims, supporting and contradicting evidence passages, and underlying academic literature.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", maxWidth: "700px", margin: "0 auto 28px" }}>
              <div className="overview-metric-card" style={{ padding: "14px" }}>
                <span className="overview-metric-label">Graph Claims</span>
                <span className="overview-metric-value">{claims.length}</span>
              </div>
              <div className="overview-metric-card" style={{ padding: "14px" }}>
                <span className="overview-metric-label">Evidence Nodes</span>
                <span className="overview-metric-value">{evidence.length}</span>
              </div>
              <div className="overview-metric-card" style={{ padding: "14px" }}>
                <span className="overview-metric-label">Literature Nodes</span>
                <span className="overview-metric-value">{sources.length}</span>
              </div>
            </div>

            <Link
              href={`/graph?investigation_id=${investigation.id}`}
              className="primary-button"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px", textDecoration: "none", background: "#2563eb", color: "#fff" }}
            >
              Open Fullscreen Knowledge Graph Explorer →
            </Link>
          </div>
        )}

        {/* TAB 6: RESEARCH REPORT */}
        {activeTab === "report" && (
          <div>
            {report ? (
              <div className="report-container">
                <div className="report-header-bar">
                  <div className="report-title-group">
                    <h4>Research Report: {report.overall_assessment.replace("_", " ").toUpperCase()}</h4>
                    {report.evidence_strength && (
                      <button
                        type="button"
                        className={`report-strength-pill tier-${report.evidence_strength.tier}`}
                        onClick={() => setShowStrengthBreakdown((prev) => !prev)}
                        title="Click to toggle component breakdown"
                      >
                        Evidence Strength: {report.evidence_strength.score.toFixed(1)}/100 · {report.evidence_strength.tier.replace("_", " ").toUpperCase()}
                      </button>
                    )}
                  </div>

                  <div className="report-version-bar">
                    {report.versions && report.versions.length > 0 && <span>Versions:</span>}
                    {report.versions?.map((v) => (
                      <button
                        key={v.id}
                        type="button"
                        className={`report-version-chip ${(selectedVersion ?? report.version_number) === v.version_number ? "active" : ""}`}
                        onClick={() => void loadReportVersion(v.version_number)}
                      >
                        v{v.version_number}
                      </button>
                    ))}
                    <button
                      type="button"
                      className="btn"
                      onClick={() => void regenerateReportVersion()}
                      disabled={regeneratingReport}
                      style={{ padding: "4px 10px", fontSize: "11px" }}
                    >
                      {regeneratingReport ? "Regenerating..." : "+ New Version"}
                    </button>
                  </div>
                </div>

                {showStrengthBreakdown && report.evidence_strength && (
                  <div className="report-breakdown-card">
                    <div className="report-breakdown-item">
                      <span className="report-breakdown-label">Source Independence</span>
                      <span className="report-breakdown-score">
                        {report.evidence_strength.breakdown.source_independence}/25
                      </span>
                    </div>
                    <div className="report-breakdown-item">
                      <span className="report-breakdown-label">Source Quality</span>
                      <span className="report-breakdown-score">
                        {report.evidence_strength.breakdown.source_quality}/25
                      </span>
                    </div>
                    <div className="report-breakdown-item">
                      <span className="report-breakdown-label">Full-Text Coverage</span>
                      <span className="report-breakdown-score">
                        {report.evidence_strength.breakdown.full_text_coverage}/20
                      </span>
                    </div>
                    <div className="report-breakdown-item">
                      <span className="report-breakdown-label">Methodological Rigor</span>
                      <span className="report-breakdown-score">
                        {report.evidence_strength.breakdown.methodological_rigor}/15
                      </span>
                    </div>
                    <div className="report-breakdown-item">
                      <span className="report-breakdown-label">Conflict Resolution</span>
                      <span className="report-breakdown-score">
                        {report.evidence_strength.breakdown.conflict_resolution}/15
                      </span>
                    </div>
                  </div>
                )}

                {/* Executive Summary Card */}
                <div className="panel" style={{ padding: "20px", marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 10px" }}>Executive Summary</h4>
                  <p style={{ fontSize: "13px", lineHeight: 1.6, color: "#cbd5e1", margin: 0 }}>{report.executive_summary}</p>
                </div>

                {report.evidence_gap && (
                  <p className="connection-result error" style={{ marginBottom: "20px" }}>Evidence gap: {report.evidence_gap}</p>
                )}

                {/* Table of Contents Navigation Bar */}
                {report.sections.length > 0 && (
                  <div className="report-toc-bar">
                    <span className="muted" style={{ fontSize: "11px", alignSelf: "center", marginRight: "4px" }}>
                      Sections ({report.sections.length}):
                    </span>
                    {report.sections.map((section) => (
                      <button
                        key={section.id}
                        type="button"
                        className="report-toc-item"
                        onClick={() => {
                          const el = document.getElementById(`report-sec-${section.section_type}`);
                          el?.scrollIntoView({ behavior: "smooth", block: "start" });
                        }}
                      >
                        {section.title}
                      </button>
                    ))}
                  </div>
                )}

                {/* Structured 18 Section Cards */}
                <div className="source-list" style={{ gap: "16px" }}>
                  {report.sections.map((section, idx) => (
                    <div
                      className="report-section-card"
                      id={`report-sec-${section.section_type}`}
                      key={section.id}
                    >
                      <h4>
                        <span>{idx + 1}. {section.title}</span>
                        <span className="report-section-type">{section.section_type}</span>
                      </h4>
                      <div className="report-content">{section.content}</div>

                      {section.provenance && section.provenance.length > 0 && (
                        <div className="report-provenance-list">
                          {section.provenance.map((p) => (
                            <button
                              key={p.evidence_id}
                              type="button"
                              className="report-provenance-chip"
                              onClick={() => focusEvidence(p.evidence_id)}
                              title={`View passage in Source: ${p.source_title || p.source_url}`}
                            >
                              Cite: {p.source_title ? p.source_title.slice(0, 30) + "..." : "Source"}
                              {p.page_number ? ` · p.${p.page_number}` : ""}
                              {p.section_name ? ` · §${p.section_name}` : ""}
                            </button>
                          ))}
                        </div>
                      )}

                      {renderEvidenceButtons(section.evidence_ids)}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="panel" style={{ padding: "40px", textAlign: "center" }}>
                <p className="muted" style={{ margin: "0 0 16px" }}>
                  Scientific research report has not been generated yet. Complete multi-agent analysis to produce the 18-section report.
                </p>
                <button
                  type="button"
                  className="primary-button compact-button"
                  onClick={() => switchTab("intelligence")}
                  style={{ background: "#2563eb", color: "#fff" }}
                >
                  Go to Multi-Agent Intelligence →
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 7: GAPS & HORIZON */}
        {activeTab === "horizon" && (
          <div style={{ display: "grid", gap: "28px" }}>
            <ResearchGapWorkspace
              investigationId={investigation.id}
              investigationQuestion={investigation.question}
            />

            <ScientificReliabilityWorkspace investigationId={investigation.id} />
          </div>
        )}

        {/* TAB 8: COLLABORATION & REVIEWS */}
        {activeTab === "collaboration" && (
          <div>
            <CollaborationPanel investigationId={investigation.id} />
          </div>
        )}
      </main>
    </div>
  );
}
