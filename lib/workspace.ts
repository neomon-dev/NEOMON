export type InvestigationSummary = {
  id: string;
  question: string;
  mode: string;
  status: string;
  created_at?: string | null;
  source_count: number;
  evidence_count: number;
  quality_status: string;
};

export type EvidenceClaimLink = {
  claim_id: string;
  claim_text: string;
  claim_status: string;
  relationship_type: string;
  explanation: string;
};

export type WorkspaceEvidenceItem = {
  id: string;
  investigation_id: string;
  investigation_question: string;
  source_id: string;
  source_title: string;
  source_type: string;
  source_url: string;
  source_canonical_url: string;
  source_publisher?: string | null;
  source_publication_date?: string | null;
  source_inclusion_status: string;
  source_rejection_reason?: string | null;
  source_open_access_status: string;
  document_id?: string | null;
  document_title?: string | null;
  document_url?: string | null;
  document_access_level?: string | null;
  document_extraction_quality?: string | null;
  document_version_type?: string | null;
  claim_id?: string | null;
  claim_text?: string | null;
  claim_status?: string | null;
  linked_claims: EvidenceClaimLink[];
  exact_text: string;
  surrounding_context?: string | null;
  evidence_type: string;
  relevance_score: number;
  relevance_reason: string;
  extraction_method: string;
  page_number?: number | null;
  section_name?: string | null;
  retrieval_timestamp?: string | null;
  traceable: boolean;
};

export type WorkspaceEvidencePage = {
  items: WorkspaceEvidenceItem[];
  total: number;
  limit: number;
  offset: number;
};

export type SourceDocumentSummary = {
  id: string;
  title?: string | null;
  content_type: string;
  access_level: string;
  extraction_quality: string;
  document_url?: string | null;
  version_type: string;
  access_route: string;
  metadata_match_status: string;
  page_count?: number | null;
  retrieved_at?: string | null;
  headings: string[];
};

export type OpenAccessLocationSummary = {
  id: string;
  url: string;
  repository?: string | null;
  version_type: string;
  license?: string | null;
  match_status: string;
  match_reason: string;
  acquisition_status: string;
  failure_reason?: string | null;
};

export type WorkspaceSourceItem = {
  id: string;
  investigation_id: string;
  investigation_question: string;
  title: string;
  canonical_url: string;
  original_url: string;
  source_type: string;
  publisher?: string | null;
  authors: string[];
  publication_date?: string | null;
  doi?: string | null;
  retrieval_timestamp?: string | null;
  relevance_score: number;
  relevance_reasons: string[];
  inclusion_status: string;
  rejection_reason?: string | null;
  access_level?: string | null;
  extraction_quality?: string | null;
  open_access_status: string;
  selected_document_url?: string | null;
  document_url?: string | null;
  version_type?: string | null;
  access_route?: string | null;
  metadata_match_status?: string | null;
  available_versions: string[];
  evidence_count: number;
  document_count: number;
  extraction_status?: string | null;
  extraction_error?: string | null;
  documents: SourceDocumentSummary[];
  open_access_locations: OpenAccessLocationSummary[];
};

export type WorkspaceSourcePage = {
  items: WorkspaceSourceItem[];
  total: number;
  limit: number;
  offset: number;
};

export type AgentRosterSummary = {
  identifier: string;
  name: string;
  description: string;
  system_instructions: string;
  demo_mode: boolean;
  total_executions: number;
  completed_count: number;
  failed_count: number;
  cancelled_count: number;
  waiting_in_queue_count: number;
  generating_count: number;
  latest_status: string;
  latest_model?: string | null;
  latest_provider_kind?: string | null;
  latest_job_id?: string | null;
  latest_investigation_id?: string | null;
  latest_started_at?: string | null;
  latest_completed_at?: string | null;
  latest_queue_wait_seconds?: number | null;
  latest_inference_duration_seconds?: number | null;
  latest_error_message?: string | null;
};

export type AgentExecutionObservatoryItem = {
  id: string;
  job_id: string;
  investigation_id: string;
  investigation_question: string;
  agent_identifier: string;
  agent_name: string;
  status: string;
  model?: string | null;
  provider_kind?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  total_duration_seconds?: number | null;
  queue_wait_seconds?: number | null;
  inference_duration_seconds?: number | null;
  token_usage: Record<string, unknown>;
  argument_count: number;
  cited_evidence_count: number;
  claims_processed_count: number;
  error_message?: string | null;
  output?: Record<string, unknown> | null;
};

export type ObservatorySummary = {
  total_jobs: number;
  active_jobs: number;
  total_executions: number;
  waiting_in_queue: number;
  generating: number;
  completed: number;
  failed: number;
  cancelled: number;
  provider_queue_wait_timeout_seconds: number;
  local_inference_timeout_seconds: number;
  local_provider_max_concurrency: number;
};

export type AgentObservatoryResponse = {
  summary: ObservatorySummary;
  agents: AgentRosterSummary[];
  executions: AgentExecutionObservatoryItem[];
  executions_total: number;
  limit: number;
  offset: number;
};

export function formatDurationSeconds(seconds?: number | null): string {
  if (seconds === undefined || seconds === null || Number.isNaN(seconds)) {
    return "—";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`;
  }
  const mins = Math.floor(seconds / 60);
  const rem = Math.round(seconds % 60);
  return `${mins}m ${rem}s`;
}

export function formatAgentStatus(status: string): string {
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
    case "ready":
      return "Ready";
    default:
      return status.replace(/_/g, " ");
  }
}

export function agentStatusBadgeClass(status: string): string {
  if (status === "waiting_in_queue" || status === "queued") return "exec-status-badge status-queued";
  if (status === "generating" || status === "running") return "exec-status-badge status-generating";
  if (status === "completed" || status === "included" || status === "resolved" || status === "full_text") {
    return "exec-status-badge status-completed";
  }
  if (status === "failed" || status === "rejected" || status === "contradicting") {
    return "exec-status-badge status-failed";
  }
  if (status === "cancelled" || status === "unavailable" || status === "low_relevance") {
    return "exec-status-badge status-cancelled";
  }
  return "exec-status-badge";
}

export function formatLabel(value?: string | null): string {
  if (!value) return "unknown";
  return value.replace(/_/g, " ");
}
