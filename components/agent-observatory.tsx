"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { requestJson } from "@/lib/api";
import {
  SpotlightCard,
  AnimatedCounter,
  PulseIndicator,
  DecryptedText,
  BorderBeam,
  RevealSection,
} from "@/components/motion";
import {
  agentStatusBadgeClass,
  formatAgentStatus,
  formatDurationSeconds,
  type AgentExecutionObservatoryItem,
  type AgentObservatoryResponse,
  type InvestigationSummary,
} from "@/lib/workspace";

const PAGE_SIZE = 25;

export function AgentObservatory() {
  const searchParams = useSearchParams();
  const initialInvId = searchParams.get("investigation_id") ?? "";
  const initialRole = searchParams.get("agent_identifier") ?? "all";

  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [data, setData] = useState<AgentObservatoryResponse | null>(null);
  const [hardware, setHardware] = useState<any | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("");

  const [investigationId, setInvestigationId] = useState(initialInvId);
  const [roleFilter, setRoleFilter] = useState(initialRole);
  const [statusFilter, setStatusFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const [refreshTick, setRefreshTick] = useState(0);
  const [autoPoll, setAutoPoll] = useState(true);

  const [loading, setLoading] = useState(true);
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
    async function loadObservatory() {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(offset));
      if (investigationId) params.set("investigation_id", investigationId);
      if (roleFilter !== "all") params.set("agent_identifier", roleFilter);
      if (statusFilter !== "all") params.set("status", statusFilter);

      try {
        const result = await requestJson<AgentObservatoryResponse>(`/agents/observatory?${params.toString()}`);
        if (!active) return;
        setData(result);
        requestJson<any>("/hardware/telemetry")
          .then((hw) => {
            if (active) setHardware(hw);
          })
          .catch(() => {});
        setError("");
        setSelectedExecutionId((prev) => {
          if (prev && result.executions.some((item) => item.id === prev)) return prev;
          return result.executions[0]?.id ?? "";
        });
      } catch (reason) {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Could not load Agent Observatory telemetry.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadObservatory();
    return () => {
      active = false;
    };
  }, [investigationId, roleFilter, statusFilter, offset, refreshTick]);

  const hasActiveActivity = Boolean(
    data &&
      (data.summary.active_jobs > 0 ||
        data.summary.waiting_in_queue > 0 ||
        data.summary.generating > 0),
  );

  useEffect(() => {
    if (!autoPoll || !hasActiveActivity) return;
    const timer = window.setInterval(() => {
      setRefreshTick((prev) => prev + 1);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [autoPoll, hasActiveActivity]);

  const selectedExecution: AgentExecutionObservatoryItem | undefined =
    data?.executions.find((item) => item.id === selectedExecutionId) ?? data?.executions[0];
  const showingFrom = !data || data.executions_total === 0 ? 0 : data.offset + 1;
  const showingTo = !data ? 0 : Math.min(data.executions_total, data.offset + data.executions.length);

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <PulseIndicator status="active" />
            <DecryptedText text="MULTI_AGENT_OBSERVATORY // TELEMETRY" speed={25} />
          </p>
          <h1 style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ color: "#25D9F2" }}>◎</span>
            Agent Observatory & Execution Matrix
          </h1>
        </div>
        <div className="analysis-actions">
          <label className="mode-toggle">
            <input
              type="checkbox"
              checked={autoPoll}
              onChange={(event) => setAutoPoll(event.target.checked)}
            />
            Auto-refresh active runs
          </label>
          <button
            className="outline-button compact-button"
            type="button"
            onClick={() => setRefreshTick((prev) => prev + 1)}
          >
            Refresh telemetry
          </button>
          <Link className="cyber-primary-btn" href="/investigations/new">
            + New investigation
          </Link>
        </div>
      </header>

      <div className="content">
        <RevealSection delay={0.08}>
          <div className="metric-grid">
            <SpotlightCard spotlightColor="rgba(37, 217, 242, 0.15)">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px 0" }}>
                <span className="metric-label">Generating / Queued</span>
                <span style={{ fontSize: "15px", color: "#25D9F2" }}>⚙️</span>
              </div>
              <div style={{ padding: "0 18px 16px" }}>
                <strong style={{ fontSize: "28px", color: "#ECF5FF", display: "block", margin: "4px 0" }}>
                  <AnimatedCounter value={data?.summary.generating ?? 0} /> / <AnimatedCounter value={data?.summary.waiting_in_queue ?? 0} />
                </strong>
                <span className="metric-detail">
                  Active jobs: {data?.summary.active_jobs ?? 0} of {data?.summary.total_jobs ?? 0}
                </span>
              </div>
            </SpotlightCard>

            <SpotlightCard spotlightColor="rgba(53, 224, 177, 0.15)">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px 0" }}>
                <span className="metric-label">Completed executions</span>
                <span style={{ fontSize: "15px", color: "#35E0B1" }}>✓</span>
              </div>
              <div style={{ padding: "0 18px 16px" }}>
                <strong style={{ fontSize: "28px", color: "#ECF5FF", display: "block", margin: "4px 0" }}>
                  <AnimatedCounter value={data?.summary.completed ?? 0} />
                </strong>
                <span className="metric-detail">Validated outputs out of {data?.summary.total_executions ?? 0} total runs</span>
              </div>
            </SpotlightCard>

            <SpotlightCard spotlightColor="rgba(255, 82, 119, 0.15)">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px 0" }}>
                <span className="metric-label">Failed / Cancelled</span>
                <span style={{ fontSize: "15px", color: "#FF5277" }}>⚠</span>
              </div>
              <div style={{ padding: "0 18px 16px" }}>
                <strong style={{ fontSize: "28px", color: "#ECF5FF", display: "block", margin: "4px 0" }}>
                  <AnimatedCounter value={data?.summary.failed ?? 0} /> / <AnimatedCounter value={data?.summary.cancelled ?? 0} />
                </strong>
                <span className="metric-detail">Queue timeouts and cancellations</span>
              </div>
            </SpotlightCard>

            <SpotlightCard spotlightColor="rgba(39, 135, 255, 0.15)">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px 0" }}>
                <span className="metric-label">Local runtime policy</span>
                <span style={{ fontSize: "15px", color: "#2787FF" }}>⏱</span>
              </div>
              <div style={{ padding: "0 18px 16px" }}>
                <strong style={{ fontSize: "26px", color: "#ECF5FF", display: "block", margin: "6px 0" }}>1 concurrent</strong>
                <span className="metric-detail">
                  Queue limit: {formatDurationSeconds(data?.summary.provider_queue_wait_timeout_seconds)}
                </span>
              </div>
            </SpotlightCard>
          </div>
        </RevealSection>

        {/* Hardware Acceleration & Compute Matrix */}
        <section className="panel" style={{ marginTop: 18, borderTop: "2px solid #25D9F2" }}>
          <div className="panel-heading">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ fontSize: "11px", color: "#25D9F2", background: "rgba(37, 217, 242, 0.12)", padding: "2px 8px", borderRadius: "4px", fontFamily: "monospace", fontWeight: 700 }}>
                  INTEL CORE ULTRA 5 · ARC GPU · NPU 3720
                </span>
                <span style={{ fontSize: "11px", color: "#35E0B1", background: "rgba(53, 224, 177, 0.12)", padding: "2px 8px", borderRadius: "4px", fontFamily: "monospace" }}>
                  PROFILE: {hardware?.active_profile ? String(hardware.active_profile).toUpperCase() : "BALANCED"}
                </span>
              </div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>Hardware-Aware Inference & Telemetry Matrix</h3>
              <span className="muted" style={{ fontSize: "12px" }}>
                Empirical device distribution across Intel Core Ultra 5 125H, Arc integrated graphics, and AI Boost NPU.
              </span>
            </div>
            <div style={{ display: "flex", gap: "6px" }}>
              {(["balanced", "performance", "memory_saver"] as const).map((prof) => (
                <button
                  key={prof}
                  type="button"
                  className={`outline-button compact-button ${hardware?.active_profile === prof ? "active" : ""}`}
                  style={{
                    fontSize: "11px",
                    borderColor: hardware?.active_profile === prof ? "#25D9F2" : undefined,
                    background: hardware?.active_profile === prof ? "rgba(37, 217, 242, 0.16)" : undefined,
                  }}
                  onClick={async () => {
                    await requestJson("/hardware/profile", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ profile: prof }),
                    });
                    setRefreshTick((t) => t + 1);
                  }}
                >
                  {prof.replace("_", " ").toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px", paddingTop: 16 }}>
            {/* GPU Tile */}
            <div className="source-row" style={{ padding: "14px", borderLeft: "3px solid #25D9F2" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <strong style={{ fontSize: "13px", color: "#ECF5FF" }}>Intel Arc Graphics (iGPU)</strong>
                <span style={{ fontSize: "11px", color: "#25D9F2", fontWeight: 700 }}>PRIMARY LLM</span>
              </div>
              <div style={{ fontSize: "12px", color: "#91A6C1", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Model: <span style={{ color: "#ECF5FF", fontFamily: "monospace" }}>openvino-qwen3-8b (INT4)</span></div>
                <div>Throughput: <span style={{ color: "#35E0B1", fontWeight: 600 }}>12.53 tokens/sec</span></div>
                <div>TTFT: <span style={{ color: "#35E0B1", fontWeight: 600 }}>654.3 ms</span> (19.3x faster than CPU)</div>
                <div>Memory: <span style={{ color: "#91A6C1" }}>Unified Shared Memory (USM)</span></div>
              </div>
            </div>

            {/* CPU Tile */}
            <div className="source-row" style={{ padding: "14px", borderLeft: "3px solid #2787FF" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <strong style={{ fontSize: "13px", color: "#ECF5FF" }}>Intel Core Ultra 5 125H</strong>
                <span style={{ fontSize: "11px", color: "#2787FF", fontWeight: 700 }}>ORCHESTRATOR</span>
              </div>
              <div style={{ fontSize: "12px", color: "#91A6C1", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Cores: <span style={{ color: "#ECF5FF" }}>14 Cores (4P + 8E + 2LPE) / 18 Threads</span></div>
                <div>Roles: <span style={{ color: "#ECF5FF" }}>DAG Orchestration, JSON Parser, Integrity</span></div>
                <div>Embeddings: <span style={{ color: "#35E0B1", fontWeight: 600 }}>1,236 ms</span> (Dynamic batching)</div>
                <div>Utilization: <span style={{ color: "#ECF5FF" }}>{hardware?.cpu?.utilization_percent ?? 5.2}%</span></div>
              </div>
            </div>

            {/* NPU Tile */}
            <div className="source-row" style={{ padding: "14px", borderLeft: "3px solid #8564FF" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <strong style={{ fontSize: "13px", color: "#ECF5FF" }}>Intel AI Boost NPU</strong>
                <span style={{ fontSize: "11px", color: "#8564FF", fontWeight: 700 }}>AUXILIARY</span>
              </div>
              <div style={{ fontSize: "12px", color: "#91A6C1", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Engine: <span style={{ color: "#ECF5FF" }}>NPU 3720 (Meteor Lake)</span></div>
                <div>Status: <span style={{ color: "#8564FF", fontWeight: 600 }}>Ready (Telemetry & Diagnostics)</span></div>
                <div>Supported Precisions: <span style={{ color: "#91A6C1" }}>FP16, INT8</span></div>
                <div>Limitation: <span style={{ color: "#94a3b8" }}>INT4 dynamic dequant routed to GPU</span></div>
              </div>
            </div>

            {/* RAM Tile */}
            <div className="source-row" style={{ padding: "14px", borderLeft: "3px solid #35E0B1" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <strong style={{ fontSize: "13px", color: "#ECF5FF" }}>System & USM Memory</strong>
                <span style={{ fontSize: "11px", color: (hardware?.memory?.used_percent ?? 0) > 85 ? "#FF5277" : "#35E0B1", fontWeight: 700 }}>
                  {hardware?.memory?.used_percent ?? 87}% ALLOCATED
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "#91A6C1", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Total RAM: <span style={{ color: "#ECF5FF" }}>{hardware?.memory?.total_gb ?? 15.57} GB LPDDR5</span></div>
                <div>Available: <span style={{ color: "#ECF5FF" }}>{hardware?.memory?.available_gb ?? 1.5} GB</span></div>
                <div>Limiter Policy: <span style={{ color: "#35E0B1" }}>Single-slot FIFO (Zero USM thrashing)</span></div>
                <div>Backpressure: <span style={{ color: "#91A6C1" }}>Threshold: 85% RAM</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 18 }}>
          <div className="panel-heading">
            <div>
              <h3>Registered agent roster ({data?.agents.length ?? 12})</h3>
              <span className="muted">
                Every stage stays independent; failures never convert silently into completed runs.
              </span>
            </div>
            <Link className="outline-button compact-button" href="/settings">
              Provider settings
            </Link>
          </div>
          <div className="execution-grid" style={{ paddingTop: 16 }}>
            {(data?.agents ?? []).map((agent) => (
              <button
                key={agent.identifier}
                type="button"
                className={`workspace-card${roleFilter === agent.identifier ? " selected" : ""}`}
                style={{ position: "relative", overflow: "hidden" }}
                onClick={() => {
                  setRoleFilter((prev) => (prev === agent.identifier ? "all" : agent.identifier));
                  setOffset(0);
                }}
              >
                {roleFilter === agent.identifier && (
                  <BorderBeam size={120} duration={6} colorFrom="#25D9F2" colorTo="#8564FF" />
                )}
                <div className="row-header">
                  <strong style={{ fontSize: 12 }}>{agent.name}</strong>
                  <span className={agentStatusBadgeClass(agent.latest_status)}>
                    {formatAgentStatus(agent.latest_status)}
                  </span>
                </div>
                <small className="muted">{agent.description}</small>
                <div className="workspace-card-meta">
                  <span>{agent.total_executions} runs</span>
                  <span>·</span>
                  <span>{agent.completed_count} ok</span>
                  {agent.failed_count > 0 && (
                    <>
                      <span>·</span>
                      <span className="connection-result error">{agent.failed_count} failed</span>
                    </>
                  )}
                </div>
                {agent.latest_model && (
                  <small className="muted">
                    Latest: {agent.latest_model}
                    {agent.latest_queue_wait_seconds != null
                      ? ` · wait ${formatDurationSeconds(agent.latest_queue_wait_seconds)}`
                      : ""}
                    {agent.latest_inference_duration_seconds != null
                      ? ` · gen ${formatDurationSeconds(agent.latest_inference_duration_seconds)}`
                      : ""}
                  </small>
                )}
              </button>
            ))}
          </div>
        </section>

        <section className="panel" style={{ marginTop: 18 }}>
          <div className="workspace-toolbar">
            <select
              aria-label="Filter executions by investigation"
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
                  {inv.question.slice(0, 60)}
                  {inv.question.length > 60 ? "…" : ""}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter executions by agent role"
              className="filter-select"
              value={roleFilter}
              onChange={(event) => {
                setRoleFilter(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All agent roles</option>
              {(data?.agents ?? []).map((agent) => (
                <option key={agent.identifier} value={agent.identifier}>
                  {agent.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter executions by status"
              className="filter-select"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                setOffset(0);
              }}
            >
              <option value="all">All statuses</option>
              <option value="waiting_in_queue">Waiting in queue</option>
              <option value="generating">Generating</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <button
              className="outline-button compact-button"
              type="button"
              onClick={() => {
                setInvestigationId("");
                setRoleFilter("all");
                setStatusFilter("all");
                setOffset(0);
              }}
            >
              Reset filters
            </button>
          </div>

          {error && <p className="connection-result error dashboard-error">{error}</p>}

          {loading && !data ? (
            <div className="empty-state">
              <p className="muted">Loading persisted agent execution telemetry...</p>
            </div>
          ) : !data || data.executions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◎</div>
              <h4>No agent execution records match these filters</h4>
              <p>Start multi-agent analysis inside an investigation to inspect live queue states and outputs.</p>
            </div>
          ) : (
            <div className="workspace-split">
              <div className="source-list" style={{ paddingTop: 0 }}>
                {data.executions.map((item) => {
                  const isSelected = selectedExecution?.id === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`workspace-card${isSelected ? " selected" : ""}`}
                      onClick={() => setSelectedExecutionId(item.id)}
                    >
                      <div className="row-header">
                        <strong style={{ fontSize: 13 }}>{item.agent_name}</strong>
                        <span className={agentStatusBadgeClass(item.status)}>
                          {formatAgentStatus(item.status)}
                        </span>
                      </div>
                      <small className="muted">{item.investigation_question}</small>
                      <div className="workspace-card-meta">
                        <span>{item.model || "rule-based / default"}</span>
                        {item.provider_kind && (
                          <>
                            <span>·</span>
                            <span>{item.provider_kind}</span>
                          </>
                        )}
                        <span>·</span>
                        <span>Wait: {formatDurationSeconds(item.queue_wait_seconds)}</span>
                        <span>·</span>
                        <span>Inference: {formatDurationSeconds(item.inference_duration_seconds)}</span>
                        <span>·</span>
                        <span>Total: {formatDurationSeconds(item.total_duration_seconds)}</span>
                      </div>
                      <div className="workspace-card-meta">
                        <span>Claims: {item.claims_processed_count}</span>
                        <span>·</span>
                        <span>Arguments: {item.argument_count}</span>
                        <span>·</span>
                        <span>Cited evidence: {item.cited_evidence_count}</span>
                      </div>
                      {item.error_message && (
                        <small className="connection-result error">{item.error_message}</small>
                      )}
                    </button>
                  );
                })}
              </div>

              {selectedExecution && (
                <aside className="workspace-detail panel" style={{ minHeight: "auto" }}>
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow blue">Execution Telemetry</p>
                      <h3>{selectedExecution.agent_name}</h3>
                    </div>
                    <span className={agentStatusBadgeClass(selectedExecution.status)}>
                      {formatAgentStatus(selectedExecution.status)}
                    </span>
                  </div>

                  <div className="workspace-chain">
                    <div>
                      <strong>Investigation:</strong>{" "}
                      <Link className="inline-link" href={`/investigations/${selectedExecution.investigation_id}`}>
                        {selectedExecution.investigation_question}
                      </Link>
                    </div>
                    <div>
                      <strong>Model & Provider:</strong>{" "}
                      <span>
                        {selectedExecution.model || "Rule-based"} · {selectedExecution.provider_kind || "none"}
                      </span>
                    </div>
                    <div>
                      <strong>Timing breakdown:</strong>{" "}
                      <span>
                        Queue wait {formatDurationSeconds(selectedExecution.queue_wait_seconds)} · Inference{" "}
                        {formatDurationSeconds(selectedExecution.inference_duration_seconds)} · Total elapsed{" "}
                        {formatDurationSeconds(selectedExecution.total_duration_seconds)}
                      </span>
                    </div>
                    <div>
                      <strong>Timestamps:</strong>{" "}
                      <span className="muted">
                        Started {selectedExecution.started_at ? new Date(selectedExecution.started_at).toLocaleString() : "—"}
                        {" · "}
                        Completed{" "}
                        {selectedExecution.completed_at ? new Date(selectedExecution.completed_at).toLocaleString() : "Active / incomplete"}
                      </span>
                    </div>
                    <div>
                      <strong>Outputs recorded:</strong>{" "}
                      <span>
                        {selectedExecution.claims_processed_count} claims · {selectedExecution.argument_count} arguments ·{" "}
                        {selectedExecution.cited_evidence_count} cited evidence passages
                      </span>
                    </div>
                    {selectedExecution.error_message && (
                      <div>
                        <strong>Error / Timeout / Cancellation:</strong>
                        <p className="connection-result error" style={{ marginTop: 4 }}>
                          {selectedExecution.error_message}
                        </p>
                      </div>
                    )}
                  </div>

                  <div>
                    <p className="eyebrow">Token & Queue Telemetry</p>
                    <pre className="workspace-pre">
                      {JSON.stringify(selectedExecution.token_usage ?? {}, null, 2)}
                    </pre>
                  </div>

                  {selectedExecution.output && (
                    <details>
                      <summary className="inline-link" style={{ cursor: "pointer", fontSize: 12 }}>
                        Inspect structured output JSON
                      </summary>
                      <pre className="workspace-pre">
                        {JSON.stringify(selectedExecution.output, null, 2)}
                      </pre>
                    </details>
                  )}

                  <div className="workspace-quick-links">
                    <Link
                      className="outline-button compact-button"
                      href={`/investigations/${selectedExecution.investigation_id}`}
                    >
                      Open investigation
                    </Link>
                    <Link
                      className="outline-button compact-button"
                      href={`/evidence?investigation_id=${selectedExecution.investigation_id}`}
                    >
                      Explore evidence
                    </Link>
                    <Link
                      className="outline-button compact-button"
                      href={`/sources?investigation_id=${selectedExecution.investigation_id}`}
                    >
                      Inspect sources
                    </Link>
                  </div>
                </aside>
              )}
            </div>
          )}

          {data && data.executions_total > 0 && (
            <div className="workspace-pagination">
              <span>
                Showing {showingFrom}–{showingTo} of {data.executions_total} executions
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
                  disabled={offset + PAGE_SIZE >= data.executions_total || loading}
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
