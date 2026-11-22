"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { requestJson } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  SpotlightCard,
  PulseIndicator,
  DecryptedText,
  AnimatedCounter,
} from "@/components/motion";

interface N8nStatus {
  status: string;
  configured: boolean;
  webhook_url: string | null;
  version: string;
  active_monitors_count: number;
  total_runs_count: number;
}

interface MonitoringConfig {
  id: string;
  workspace_id: string;
  investigation_id: string;
  name: string;
  query_keywords: string;
  interval_minutes: number;
  is_active: boolean;
  max_new_sources_per_run: number;
  last_run_at: string | null;
  next_run_at: string | null;
  consecutive_failures: number;
  last_error: string | null;
  created_at: string;
}

interface InvestigationOption {
  id: string;
  question: string;
  status: string;
}

export default function AutomationDashboardPage() {
  const { activeWorkspace } = useAuth();
  const [n8nStatus, setN8nStatus] = useState<N8nStatus | null>(null);
  const [configs, setConfigs] = useState<MonitoringConfig[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPending, startTransition] = useTransition();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New monitor modal form state
  const [showModal, setShowModal] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKeywords, setFormKeywords] = useState("");
  const [formInvestigationId, setFormInvestigationId] = useState("");
  const [formInterval, setFormInterval] = useState(60);

  const workspaceId = activeWorkspace?.id;

  async function loadData() {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const [statusRes, configsRes, invsRes] = await Promise.all([
        requestJson<N8nStatus>("/integrations/n8n/status"),
        requestJson<MonitoringConfig[]>(`/monitoring?workspace_id=${workspaceId}`),
        requestJson<{ items?: InvestigationOption[]; investigations?: InvestigationOption[] }>(
          `/research/investigations?workspace_id=${workspaceId}&limit=20`
        ).catch(() => ({ items: [] as InvestigationOption[], investigations: [] as InvestigationOption[] })),
      ]);
      setN8nStatus(statusRes);
      setConfigs(configsRes);
      const invList = ("items" in invsRes && invsRes.items) || ("investigations" in invsRes && invsRes.investigations) || [];
      setInvestigations(invList);
      if (invList.length > 0 && !formInvestigationId) {
        setFormInvestigationId(invList[0].id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed loading automation telemetry");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  async function handleToggleActive(config: MonitoringConfig) {
    try {
      await requestJson(`/monitoring/${config.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !config.is_active }),
      });
      setActionMessage(`Monitor "${config.name}" ${!config.is_active ? "enabled" : "paused"}.`);
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed toggling monitor");
    }
  }

  async function handleTriggerRun(config: MonitoringConfig) {
    try {
      setActionMessage(`Triggering research monitoring run for "${config.name}"...`);
      const res = await requestJson<{ sources_discovered: number; status: string }>(
        `/monitoring/${config.id}/trigger`,
        {
          method: "POST",
          body: JSON.stringify({ idempotency_key: `ui_${Date.now()}` }),
        }
      );
      setActionMessage(
        `Monitoring run completed: ${res.sources_discovered} new source(s) discovered and evaluated.`
      );
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed executing monitoring cycle");
    }
  }

  async function handleDelete(configId: string) {
    if (!confirm("Are you sure you want to delete this monitoring configuration?")) return;
    try {
      await requestJson(`/monitoring/${configId}`, { method: "DELETE" });
      setActionMessage("Monitoring configuration deleted.");
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed deleting monitor");
    }
  }

  async function handleCreateMonitor(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId || !formInvestigationId) return;
    startTransition(async () => {
      try {
        await requestJson("/monitoring", {
          method: "POST",
          body: JSON.stringify({
            workspace_id: workspaceId,
            investigation_id: formInvestigationId,
            name: formName,
            query_keywords: formKeywords,
            interval_minutes: Number(formInterval),
            max_new_sources_per_run: 5,
          }),
        });
        setShowModal(false);
        setFormName("");
        setFormKeywords("");
        setActionMessage("Automated research monitoring configuration created successfully.");
        loadData();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed creating monitoring config");
      }
    });
  }

  async function handleSendTestPing() {
    try {
      setActionMessage("Sending test event to n8n webhook bridge...");
      const res = await requestJson<{ status: string; message: string; webhook_dispatched: boolean }>(
        "/integrations/n8n/test",
        {
          method: "POST",
          body: JSON.stringify({ event_type: "ping", payload: { ping: true } }),
        }
      );
      setActionMessage(
        res.webhook_dispatched
          ? "Ping delivered to live n8n instance successfully!"
          : `Validated locally: ${res.message}`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed testing n8n connection");
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <PulseIndicator status="cyan" size={8} />
            <p className="eyebrow">Enterprise Integrations & Workflow Orchestration</p>
          </div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <DecryptedText text="Automation & n8n Workflows" speed={25} />
          </h1>
        </div>
        <div className="analysis-actions">
          <button
            type="button"
            className="outline-button compact-button"
            onClick={handleSendTestPing}
          >
            ⚡ Test n8n Bridge
          </button>
          <button
            type="button"
            className="primary-button"
            onClick={() => setShowModal(true)}
          >
            + Create Research Monitor
          </button>
        </div>
      </header>

      <div className="content">
        {actionMessage && (
          <div className="connection-result success dashboard-error" style={{ marginBottom: 16 }}>
            {actionMessage}
          </div>
        )}
        {error && (
          <div className="connection-result error dashboard-error" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}

        {/* Telemetry Metrics */}
        <div className="metric-grid">
          <SpotlightCard className="metric-card" spotlightColor="rgba(54, 197, 222, 0.15)">
            <span className="metric-label">n8n Bridge Status</span>
            <strong style={{ color: n8nStatus?.configured ? "var(--cyan)" : "#38bdf8", display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: n8nStatus?.configured ? "#35E0B1" : "#38bdf8",
                  boxShadow: n8nStatus?.configured ? "0 0 10px #35E0B1" : "0 0 10px #38bdf8",
                }}
              />
              {n8nStatus?.configured ? "Configured & Live" : "Ready for Bridge"}
            </strong>
            <span className="metric-detail">
              {n8nStatus?.webhook_url ? `Webhook: ${n8nStatus.webhook_url.slice(0, 32)}...` : "Service endpoints authenticated"}
            </span>
          </SpotlightCard>

          <SpotlightCard className="metric-card" spotlightColor="rgba(100, 123, 255, 0.15)">
            <span className="metric-label">Active Research Monitors</span>
            <strong style={{ color: "var(--color-electric-violet)" }}>
              <AnimatedCounter value={configs.filter((c) => c.is_active).length} />
            </strong>
            <span className="metric-detail">Scheduled background query workers</span>
          </SpotlightCard>

          <SpotlightCard className="metric-card" spotlightColor="rgba(53, 224, 177, 0.15)">
            <span className="metric-label">Integrated Workflows</span>
            <strong style={{ color: "var(--mint)" }}>
              <AnimatedCounter value={3} />
            </strong>
            <span className="metric-detail">Monitoring, Completion & Approval</span>
          </SpotlightCard>

          <SpotlightCard className="metric-card" spotlightColor="rgba(39, 135, 255, 0.15)">
            <span className="metric-label">Total Execution Runs</span>
            <strong style={{ color: "var(--electric-blue)" }}>
              <AnimatedCounter value={n8nStatus?.total_runs_count || configs.length} />
            </strong>
            <span className="metric-detail">Incremental discovery & evaluation cycles</span>
          </SpotlightCard>
        </div>

        {/* Three Core Workflows Architecture Panel */}
        <section className="panel" style={{ marginTop: 24 }}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow blue">Production Workflows</p>
              <h3>Importable n8n Automation Workflows</h3>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16, marginTop: 16 }}>
            <div className="hud-card" style={{ padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong style={{ color: "#36C5DE", fontSize: 14 }}>1. Automated Research Monitoring</strong>
                <span className="workspace-badge-role">Core Pipeline</span>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                Runs on configurable intervals via n8n Schedule Trigger. Queries NEOMON S2S endpoints to perform incremental academic discovery, deduplicates existing literature, and alerts researchers.
              </p>
              <div style={{ marginTop: 12, fontSize: 11, color: "var(--muted)" }}>
                Workflow file: <code>automation/n8n/research_monitoring.json</code>
              </div>
            </div>

            <div className="hud-card" style={{ padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong style={{ color: "#647BFF", fontSize: 14 }}>2. Investigation Completion</strong>
                <span className="workspace-badge-role">Event Trigger</span>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                Triggered automatically when dialectical analysis completes. Extracts calibrated quality metrics, contradictions, and report summaries to dispatch notifications.
              </p>
              <div style={{ marginTop: 12, fontSize: 11, color: "var(--muted)" }}>
                Workflow file: <code>automation/n8n/investigation_completion.json</code>
              </div>
            </div>

            <div className="hud-card" style={{ padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong style={{ color: "#35E0B1", fontSize: 14 }}>3. Human Approval & Delivery</strong>
                <span className="workspace-badge-role">HITL Protocol</span>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                Enforces formal review board sign-off. Integrates with NEOMON RBAC permissions and self-approval guards before releasing validated scientific findings.
              </p>
              <div style={{ marginTop: 12, fontSize: 11, color: "var(--muted)" }}>
                Workflow file: <code>automation/n8n/report_approval_delivery.json</code>
              </div>
            </div>
          </div>
        </section>

        {/* Scheduled Research Monitors Table */}
        <section className="panel" style={{ marginTop: 24 }}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow blue">Active Scheduled Monitors</p>
              <h3>Workspace Research Monitors</h3>
            </div>
          </div>

          {loading ? (
            <div className="empty-state">
              <p className="muted">Loading scheduled research monitors...</p>
            </div>
          ) : configs.length === 0 ? (
            <div className="empty-state">
              <p>No active research monitors configured in this workspace.</p>
              <button
                type="button"
                className="primary-button"
                style={{ marginTop: 12 }}
                onClick={() => setShowModal(true)}
              >
                + Create First Monitor
              </button>
            </div>
          ) : (
            <div className="table-responsive" style={{ marginTop: 16 }}>
              <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left", fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>
                    <th style={{ padding: "10px 12px" }}>Monitor Name</th>
                    <th style={{ padding: "10px 12px" }}>Query Keywords</th>
                    <th style={{ padding: "10px 12px" }}>Frequency</th>
                    <th style={{ padding: "10px 12px" }}>Status</th>
                    <th style={{ padding: "10px 12px" }}>Last Run</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {configs.map((c) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)", fontSize: 13 }}>
                      <td style={{ padding: "12px" }}>
                        <strong style={{ color: "#f8fafc" }}>{c.name}</strong>
                      </td>
                      <td style={{ padding: "12px", color: "var(--text-secondary)", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.query_keywords}
                      </td>
                      <td style={{ padding: "12px", color: "var(--muted-light)" }}>
                        Every {c.interval_minutes}m
                      </td>
                      <td style={{ padding: "12px" }}>
                        <span
                          className={`badge ${c.is_active ? "status-generating" : "status-queued"}`}
                          style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4 }}
                        >
                          {c.is_active ? "ACTIVE" : "PAUSED"}
                        </span>
                      </td>
                      <td style={{ padding: "12px", color: "var(--muted)", fontSize: 12 }}>
                        {c.last_run_at ? new Date(c.last_run_at).toLocaleString() : "Never"}
                      </td>
                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: 6 }}>
                          <button
                            type="button"
                            className="outline-button compact-button"
                            onClick={() => handleTriggerRun(c)}
                            title="Run monitor now"
                          >
                            ▶ Run
                          </button>
                          <button
                            type="button"
                            className="outline-button compact-button"
                            onClick={() => handleToggleActive(c)}
                          >
                            {c.is_active ? "Pause" : "Enable"}
                          </button>
                          <Link
                            href={`/investigations/${c.investigation_id}`}
                            className="outline-button compact-button"
                            title="Open associated investigation"
                          >
                            View
                          </Link>
                          <button
                            type="button"
                            className="outline-button compact-button"
                            style={{ color: "var(--error-red)", borderColor: "rgba(255, 82, 119, 0.3)" }}
                            onClick={() => handleDelete(c.id)}
                          >
                            ✕
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* Create Monitor Modal Dialog */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(8px)",
            zIndex: 100,
            display: "grid",
            placeItems: "center",
            padding: 16,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            className="panel"
            style={{ width: "100%", maxWidth: 520, background: "rgba(10, 20, 36, 0.95)", border: "1px solid rgba(54, 197, 222, 0.3)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-heading">
              <div>
                <p className="eyebrow blue">New Automation</p>
                <h3>Configure Automated Research Monitor</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 16 }}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateMonitor} style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  Monitor Name
                </label>
                <input
                  required
                  className="filter-input"
                  style={{ width: "100%" }}
                  placeholder="e.g., Solid-State Electrolyte Breakthroughs"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  Associated Investigation
                </label>
                <select
                  required
                  className="filter-select"
                  style={{ width: "100%" }}
                  value={formInvestigationId}
                  onChange={(e) => setFormInvestigationId(e.target.value)}
                >
                  {investigations.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.question.slice(0, 60)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  Search Keywords (comma separated)
                </label>
                <input
                  required
                  className="filter-input"
                  style={{ width: "100%" }}
                  placeholder="e.g. sodium battery, solid electrolyte, ionic conductivity"
                  value={formKeywords}
                  onChange={(e) => setFormKeywords(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                  Execution Interval (Minutes)
                </label>
                <select
                  className="filter-select"
                  style={{ width: "100%" }}
                  value={formInterval}
                  onChange={(e) => setFormInterval(Number(e.target.value))}
                >
                  <option value={15}>Every 15 minutes</option>
                  <option value={60}>Every 1 hour (Recommended)</option>
                  <option value={360}>Every 6 hours</option>
                  <option value={1440}>Every 24 hours (Daily)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 10 }}>
                <button
                  type="button"
                  className="outline-button compact-button"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={isPending}
                >
                  {isPending ? "Creating..." : "Save Monitor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
