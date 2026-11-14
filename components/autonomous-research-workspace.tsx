"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { requestJson } from "@/lib/api";

export type AutonomousWorkflowView = {
  id: string;
  investigation_id: string;
  title: string;
  research_objective: string;
  autonomy_mode: "assisted" | "supervised" | "bounded";
  status: string;
  current_cycle_number: number;
  max_cycles: number;
  max_searches_per_cycle: number;
  max_sources_total: number;
  max_documents_total: number;
  max_duration_seconds: number;
  stop_on_sufficient_evidence: boolean;
  stop_on_diminishing_returns: boolean;
  total_searches_executed: number;
  total_sources_acquired: number;
  total_documents_acquired: number;
  total_evidence_acquired: number;
  total_duration_seconds: number;
  stopping_reason?: string | null;
  stopping_explanation?: string | null;
  information_gain_history: number[];
  quality_score_history: number[];
  coverage_score_history: number[];
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
};

export type ResearchWorkflowCycleView = {
  id: string;
  workflow_id: string;
  cycle_number: number;
  state: string;
  cycle_goal: string;
  planned_actions_count: number;
  executed_actions_count: number;
  searches_executed_count: number;
  sources_acquired_count: number;
  documents_acquired_count: number;
  evidence_acquired_count: number;
  claims_reevaluated_count: number;
  hypotheses_updated_count: number;
  information_gain_score: number;
  quality_score_after: number;
  coverage_score_after: number;
  stopping_evaluated: boolean;
  stopping_reason?: string | null;
  checkpoint_notes?: string | null;
  duration_seconds?: number | null;
  created_at?: string | null;
  completed_at?: string | null;
};

export type ResearchActionView = {
  id: string;
  cycle_id: string;
  action_type: string;
  priority: number;
  status: string;
  target_entity_type?: string | null;
  target_entity_id?: string | null;
  target_provider?: string | null;
  planned_query?: string | null;
  action_rationale: string;
  expected_information_gain: number;
  prerequisite_action_ids: string[];
  approval_status: string;
  reviewed_by?: string | null;
  review_notes?: string | null;
  execution_error?: string | null;
  result_summary?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
};

export type ResearchWorkflowReportView = {
  id: string;
  workflow_id: string;
  investigation_id: string;
  title: string;
  executive_summary: string;
  research_objective: string;
  cycles_summary?: Array<{ cycle?: number; goal?: string; information_gain?: number }>;
  total_queries_executed?: number;
  total_sources_acquired?: number;
  total_evidence_extracted?: number;
  claims_reassessed_count?: number;
  contradictions_resolved_count?: number;
  remaining_uncertainties?: string[];
  recommended_next_actions?: string[];
  stopping_reason?: string;
  stopping_explanation?: string;
  calibrated_quality_tier?: string;
  calibrated_quality_score?: number;
  created_at?: string | null;
};

type InvestigationOption = {
  id: string;
  question: string;
  status: string;
  quality_status?: string | null;
};

export function AutonomousResearchWorkspace({
  initialInvestigationId,
}: {
  initialInvestigationId?: string;
}) {
  const [investigations, setInvestigations] = useState<InvestigationOption[]>([]);
  const [selectedInvId, setSelectedInvId] = useState<string>(initialInvestigationId || "");
  const [workflows, setWorkflows] = useState<AutonomousWorkflowView[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("");
  const [cycles, setCycles] = useState<ResearchWorkflowCycleView[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>("");
  const [actions, setActions] = useState<ResearchActionView[]>([]);
  const [report, setReport] = useState<ResearchWorkflowReportView | null>(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createObjective, setCreateObjective] = useState("");
  const [createMode, setCreateMode] = useState<"assisted" | "supervised" | "bounded">("bounded");
  const [createMaxCycles, setCreateMaxCycles] = useState(3);
  const [createMaxSearches, setCreateMaxSearches] = useState(5);
  const [createMaxSources, setCreateMaxSources] = useState(30);
  const [createMaxDuration, setCreateMaxDuration] = useState(30);

  // Continue modal states
  const [showContinueModal, setShowContinueModal] = useState(false);
  const [additionalCycles, setAdditionalCycles] = useState(2);
  const [continueNotes, setContinueNotes] = useState("");

  // Review modal states
  const [reviewAction, setReviewAction] = useState<ResearchActionView | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewType, setReviewType] = useState<"approve" | "reject">("approve");

  // Load investigations
  useEffect(() => {
    requestJson<InvestigationOption[]>("/research/investigations")
      .then((rows) => {
        setInvestigations(rows);
        if (!selectedInvId && rows.length > 0) {
          setSelectedInvId(rows[0].id);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load investigations");
      })
      .finally(() => setLoading(false));
  }, []);

  // Load workflows for selected investigation
  const loadWorkflows = async (invId: string) => {
    try {
      const url = invId
        ? `/research/autonomous/workflows?investigation_id=${invId}`
        : "/research/autonomous/workflows";
      const rows = await requestJson<AutonomousWorkflowView[]>(url);
      setWorkflows(rows);
      if (rows.length > 0) {
        if (!selectedWorkflowId || !rows.some((r) => r.id === selectedWorkflowId)) {
          setSelectedWorkflowId(rows[0].id);
        }
      } else {
        setSelectedWorkflowId("");
        setCycles([]);
        setActions([]);
        setReport(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflows");
    }
  };

  useEffect(() => {
    if (selectedInvId) {
      loadWorkflows(selectedInvId);
    }
  }, [selectedInvId]);

  // Load selected workflow details, cycles, actions, report
  const loadWorkflowDetails = async (wfId: string) => {
    if (!wfId) return;
    try {
      const [cycList, actList] = await Promise.all([
        requestJson<ResearchWorkflowCycleView[]>(`/research/autonomous/workflows/${wfId}/cycles`),
        requestJson<ResearchActionView[]>(`/research/autonomous/workflows/${wfId}/actions`),
      ]);
      setCycles(cycList);
      setActions(actList);
      if (cycList.length > 0 && !selectedCycleId) {
        setSelectedCycleId(cycList[cycList.length - 1].id);
      }

      // Try load report if completed
      try {
        const rep = await requestJson<ResearchWorkflowReportView>(
          `/research/autonomous/workflows/${wfId}/report`
        );
        setReport(rep);
      } catch {
        setReport(null);
      }
    } catch (err) {
      console.error("Error loading workflow details:", err);
    }
  };

  useEffect(() => {
    if (selectedWorkflowId) {
      loadWorkflowDetails(selectedWorkflowId);
    }
  }, [selectedWorkflowId]);

  // Periodic polling for active workflows
  useEffect(() => {
    const currentWf = workflows.find((w) => w.id === selectedWorkflowId);
    const isActive =
      currentWf &&
      ["created", "executing", "planning", "evaluating", "refining"].includes(currentWf.status);

    if (!isActive) return;

    const interval = setInterval(() => {
      if (selectedInvId) {
        loadWorkflows(selectedInvId);
      }
      if (selectedWorkflowId) {
        loadWorkflowDetails(selectedWorkflowId);
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [selectedWorkflowId, workflows, selectedInvId]);

  const activeWorkflow = useMemo(
    () => workflows.find((w) => w.id === selectedWorkflowId),
    [workflows, selectedWorkflowId]
  );

  const selectedCycle = useMemo(
    () => cycles.find((c) => c.id === selectedCycleId) || cycles[cycles.length - 1],
    [cycles, selectedCycleId]
  );

  const pendingReviewActions = useMemo(
    () => actions.filter((a) => a.approval_status === "awaiting_approval"),
    [actions]
  );

  // Actions
  const handleStartWorkflow = async (id: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/autonomous/workflows/${id}/start`, { method: "POST" });
      setSuccessMsg("Workflow engine started");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflows(selectedInvId);
      loadWorkflowDetails(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePauseWorkflow = async (id: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/autonomous/workflows/${id}/pause`, { method: "POST" });
      setSuccessMsg("Workflow safely paused");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflows(selectedInvId);
      loadWorkflowDetails(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pause workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResumeWorkflow = async (id: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/autonomous/workflows/${id}/resume`, { method: "POST" });
      setSuccessMsg("Workflow resumed");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflows(selectedInvId);
      loadWorkflowDetails(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelWorkflow = async (id: string) => {
    if (!confirm("Are you sure you want to cancel this workflow? Partial evidence will be preserved.")) return;
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/autonomous/workflows/${id}/cancel`, { method: "POST" });
      setSuccessMsg("Workflow cancelled");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflows(selectedInvId);
      loadWorkflowDetails(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvId) {
      setError("Please select an investigation first.");
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const created = await requestJson<AutonomousWorkflowView>("/research/autonomous/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          investigation_id: selectedInvId,
          title: createTitle || "Autonomous Evidence Deep-Dive",
          research_objective: createObjective || "Systematic exploration of primary research and resolving evidence gaps.",
          autonomy_mode: createMode,
          max_cycles: createMaxCycles,
          max_searches_per_cycle: createMaxSearches,
          max_sources_total: createMaxSources,
          max_duration_seconds: createMaxDuration * 60,
          stop_on_sufficient_evidence: true,
          stop_on_diminishing_returns: true,
        }),
      });
      setShowCreateModal(false);
      setSuccessMsg(`Workflow "${created.title}" created successfully.`);
      setTimeout(() => setSuccessMsg(null), 3000);
      await loadWorkflows(selectedInvId);
      setSelectedWorkflowId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handleContinueWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkflow) return;
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(`/research/autonomous/workflows/${activeWorkflow.id}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          additional_cycles: additionalCycles,
          reason: continueNotes || "Deepening exploration of open gaps.",
        }),
      });
      setShowContinueModal(false);
      setSuccessMsg(`Workflow extended by ${additionalCycles} cycles.`);
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflows(selectedInvId);
      loadWorkflowDetails(activeWorkflow.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extend workflow");
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveAction = async (action: ResearchActionView) => {
    if (!activeWorkflow) return;
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(
        `/research/autonomous/workflows/${activeWorkflow.id}/actions/${action.id}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reviewer: "Researcher",
            review_notes: reviewNotes || "Approved for execution.",
          }),
        }
      );
      setReviewAction(null);
      setReviewNotes("");
      setSuccessMsg("Action approved for execution.");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflowDetails(activeWorkflow.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve action");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectAction = async (action: ResearchActionView) => {
    if (!activeWorkflow) return;
    setActionLoading(true);
    setError(null);
    try {
      await requestJson(
        `/research/autonomous/workflows/${activeWorkflow.id}/actions/${action.id}/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reviewer: "Researcher",
            review_notes: reviewNotes || "Rejected by human supervisor.",
          }),
        }
      );
      setReviewAction(null);
      setReviewNotes("");
      setSuccessMsg("Action rejected.");
      setTimeout(() => setSuccessMsg(null), 3000);
      loadWorkflowDetails(activeWorkflow.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject action");
    } finally {
      setActionLoading(false);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "executing":
      case "planning":
      case "evaluating":
      case "refining":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse";
      case "paused":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "awaiting_approval":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      case "completed":
      case "stopping_condition_met":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
      case "cancelled":
      case "failed":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      default:
        return "bg-slate-700/40 text-slate-300 border-slate-600/40";
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-xl">⚡</span> Autonomous Research Workflow Engine
            </h1>
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/20">
              Milestone 9
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Multi-cycle autonomous research loops with deterministic action planning, adaptive query refinement, canonical evidence calibration, and scientific stopping criteria.
          </p>
        </div>

        {/* Investigation Selector & Create Workflow CTA */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedInvId}
            onChange={(e) => setSelectedInvId(e.target.value)}
            className="rounded-lg bg-surface border border-border px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500 max-w-xs"
          >
            {investigations.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.question.length > 50 ? `${inv.question.slice(0, 50)}...` : inv.question}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => {
              const current = investigations.find((i) => i.id === selectedInvId);
              setCreateTitle(`Autonomous Loop: ${current?.question.slice(0, 40) || "Research"}`);
              setCreateObjective(`Formulate targeted searches, re-evaluate contradictory claims, and close critical gaps.`);
              setShowCreateModal(true);
            }}
            className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 text-sm shadow-sm transition flex items-center gap-1.5"
          >
            <span>+</span> Launch Autonomous Workflow
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-4 text-sm text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}
      {successMsg && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-4 text-sm text-emerald-300 flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Pending Approval Alert Banner */}
      {pendingReviewActions.length > 0 && (
        <div className="rounded-xl bg-purple-500/10 border border-purple-500/30 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl animate-bounce">✋</span>
            <div>
              <h4 className="text-sm font-semibold text-purple-200">
                Human Review Required ({pendingReviewActions.length} action{pendingReviewActions.length > 1 ? "s" : ""})
              </h4>
              <p className="text-xs text-purple-300/80">
                This workflow is running in assisted mode and requires researcher authorization before executing next queries.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById("review-queue");
                el?.scrollIntoView({ behavior: "smooth" });
              }}
              className="rounded-lg bg-purple-600 hover:bg-purple-500 px-3 py-1.5 text-xs font-medium text-white transition"
            >
              Review Actions →
            </button>
          </div>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Workflows</div>
          <div className="text-2xl font-bold text-white mt-1">
            {workflows.filter((w) => ["executing", "planning", "evaluating"].includes(w.status)).length}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">{workflows.length} total defined</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Cycles Completed</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">
            {activeWorkflow ? `${activeWorkflow.current_cycle_number} / ${activeWorkflow.max_cycles}` : "0"}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">Iterative research loops</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Sources Acquired</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            +{activeWorkflow?.total_sources_acquired || 0}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">{activeWorkflow?.total_searches_executed || 0} searches executed</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Evidence Passages</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            +{activeWorkflow?.total_evidence_acquired || 0}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">8G calibrated & verified</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Engine State</div>
          <div className="text-lg font-bold text-white mt-1 capitalize flex items-center gap-1.5">
            {activeWorkflow ? (
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${
                activeWorkflow.status === "executing" ? "bg-emerald-400 animate-ping" : "bg-slate-400"
              }`} />
            ) : null}
            {activeWorkflow?.status.replace("_", " ") || "Idle"}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            {activeWorkflow?.autonomy_mode || "no"} mode
          </div>
        </div>
      </div>

      {/* Main Content: Workflow Selector & Live Monitor */}
      {workflows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface/50 p-12 text-center">
          <div className="text-4xl mb-3">⚡</div>
          <h3 className="text-lg font-medium text-white">No autonomous workflows created yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mt-1 mb-6">
            Launch an autonomous research loop to formulate hypotheses, probe evidence gaps, refine academic queries, and test claims automatically.
          </p>
          <button
            type="button"
            onClick={() => {
              const current = investigations.find((i) => i.id === selectedInvId);
              setCreateTitle(`Autonomous Loop: ${current?.question.slice(0, 40) || "Research"}`);
              setCreateObjective(`Formulate targeted searches, re-evaluate contradictory claims, and close critical gaps.`);
              setShowCreateModal(true);
            }}
            className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 text-sm transition"
          >
            Create First Autonomous Workflow
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Workflows List */}
          <div className="lg:col-span-1 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Workflows</h3>
              <span className="text-xs text-slate-500">{workflows.length} total</span>
            </div>

            <div className="space-y-3">
              {workflows.map((wf) => {
                const isSelected = wf.id === selectedWorkflowId;
                return (
                  <div
                    key={wf.id}
                    onClick={() => setSelectedWorkflowId(wf.id)}
                    className={`rounded-xl border p-4 cursor-pointer transition ${
                      isSelected
                        ? "border-amber-500/60 bg-amber-500/5 shadow-sm ring-1 ring-amber-500/30"
                        : "border-border bg-surface hover:border-border/80"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-sm font-semibold text-white line-clamp-1">{wf.title}</h4>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${statusBadge(wf.status)}`}>
                        {wf.status.replace("_", " ")}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">{wf.research_objective}</p>

                    <div className="mt-3 grid grid-cols-3 gap-2 border-t border-border/40 pt-2 text-[11px] text-slate-400">
                      <div>
                        <span className="text-slate-500 block">Cycle</span>
                        <span className="font-semibold text-slate-200">
                          {wf.current_cycle_number} / {wf.max_cycles}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Mode</span>
                        <span className="font-semibold text-slate-200 capitalize">{wf.autonomy_mode}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Gain</span>
                        <span className="font-semibold text-emerald-400">
                          +{wf.total_evidence_acquired} ev
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-2 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-amber-500 h-1.5 rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, Math.round((wf.current_cycle_number / wf.max_cycles) * 100))}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Workflow Details & Controls */}
          {activeWorkflow && (
            <div className="lg:col-span-2 space-y-6">
              {/* Workflow Control Header */}
              <div className="rounded-xl border border-border bg-surface p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-white">{activeWorkflow.title}</h2>
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold border ${statusBadge(activeWorkflow.status)}`}>
                        {activeWorkflow.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 max-w-xl">
                      {activeWorkflow.research_objective}
                    </p>
                  </div>

                  {/* Action Controls */}
                  <div className="flex flex-wrap items-center gap-2">
                    {activeWorkflow.status === "created" && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleStartWorkflow(activeWorkflow.id)}
                        className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-3.5 py-1.5 text-xs shadow-sm transition flex items-center gap-1.5"
                      >
                        <span>▶</span> Start Engine
                      </button>
                    )}

                    {["executing", "planning", "evaluating", "refining"].includes(activeWorkflow.status) && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handlePauseWorkflow(activeWorkflow.id)}
                        className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium px-3.5 py-1.5 text-xs shadow-sm transition flex items-center gap-1.5"
                      >
                        <span>⏸</span> Pause Engine
                      </button>
                    )}

                    {activeWorkflow.status === "paused" && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleResumeWorkflow(activeWorkflow.id)}
                        className="rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-3.5 py-1.5 text-xs shadow-sm transition flex items-center gap-1.5"
                      >
                        <span>▶</span> Resume Loop
                      </button>
                    )}

                    {["created", "executing", "paused", "awaiting_approval"].includes(activeWorkflow.status) && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleCancelWorkflow(activeWorkflow.id)}
                        className="rounded-lg border border-rose-500/30 text-rose-300 hover:bg-rose-500/10 px-3 py-1.5 text-xs font-medium transition"
                      >
                        Cancel
                      </button>
                    )}

                    {["completed", "stopping_condition_met"].includes(activeWorkflow.status) && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => setShowContinueModal(true)}
                        className="rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-3.5 py-1.5 text-xs shadow-sm transition flex items-center gap-1.5"
                      >
                        <span>↻</span> Request Additional Cycles
                      </button>
                    )}
                  </div>
                </div>

                {/* Stopping Reason Explanation if stopped */}
                {activeWorkflow.stopping_reason && (
                  <div className="mt-4 rounded-lg bg-slate-900/60 border border-border/80 p-3 text-xs">
                    <span className="font-semibold text-amber-300">
                      Stopping condition: {activeWorkflow.stopping_reason.replace("_", " ")}
                    </span>
                    {activeWorkflow.stopping_explanation && (
                      <p className="text-slate-400 mt-0.5">{activeWorkflow.stopping_explanation}</p>
                    )}
                  </div>
                )}
              </div>

              {/* Review Queue (if any) */}
              {pendingReviewActions.length > 0 && (
                <div id="review-queue" className="rounded-xl border border-purple-500/40 bg-surface p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-border pb-3">
                    <h3 className="text-sm font-semibold text-purple-300 flex items-center gap-2">
                      <span>✋</span> Actions Awaiting Approval ({pendingReviewActions.length})
                    </h3>
                    <span className="text-xs text-slate-400">Assisted Autonomy Mode</span>
                  </div>

                  <div className="space-y-3">
                    {pendingReviewActions.map((act) => (
                      <div key={act.id} className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-purple-200 uppercase tracking-wide">
                            {act.action_type.replace("_", " ")}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            Priority: {act.priority} · Exp. Gain: {act.expected_information_gain != null ? act.expected_information_gain.toFixed(1) : "0.5"}
                          </span>
                        </div>
                        {act.planned_query && (
                          <div className="text-xs font-mono bg-black/40 p-2 rounded text-cyan-300 border border-slate-700">
                            Query: &ldquo;{act.planned_query}&rdquo;
                            {act.target_provider && <span className="text-slate-500 ml-2">[{act.target_provider}]</span>}
                          </div>
                        )}
                        <p className="text-xs text-slate-300">{act.action_rationale}</p>
                        <div className="flex items-center gap-2 pt-2">
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={() => handleApproveAction(act)}
                            className="rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-3 py-1 text-xs transition"
                          >
                            ✓ Approve & Execute
                          </button>
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={() => {
                              setReviewAction(act);
                              setReviewType("reject");
                            }}
                            className="rounded border border-rose-500/40 text-rose-300 hover:bg-rose-500/10 px-3 py-1 text-xs font-medium transition"
                          >
                            ✕ Reject Action
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cycle Timeline & Details */}
              <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <h3 className="text-sm font-semibold text-slate-200">Research Cycles</h3>
                  <div className="flex items-center gap-2">
                    {cycles.map((cyc) => (
                      <button
                        key={cyc.id}
                        type="button"
                        onClick={() => setSelectedCycleId(cyc.id)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                          (selectedCycle?.id === cyc.id)
                            ? "bg-amber-600 text-white font-semibold"
                            : "bg-slate-800 text-slate-400 hover:text-white"
                        }`}
                      >
                        Cycle {cyc.cycle_number}
                      </button>
                    ))}
                  </div>
                </div>

                {selectedCycle ? (
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                      <div>
                        <span className="font-semibold text-white">Goal: </span>
                        <span className="text-slate-300">{selectedCycle.cycle_goal}</span>
                      </div>
                      <div className="text-slate-400">
                        Information Gain: <span className="font-semibold text-emerald-400">+{selectedCycle.information_gain_score != null ? selectedCycle.information_gain_score.toFixed(2) : "0.00"}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      <div className="rounded bg-slate-900/50 p-2 border border-border/40">
                        <span className="text-slate-500 block">Actions</span>
                        <span className="font-bold text-slate-200">
                          {selectedCycle.executed_actions_count} / {selectedCycle.planned_actions_count}
                        </span>
                      </div>
                      <div className="rounded bg-slate-900/50 p-2 border border-border/40">
                        <span className="text-slate-500 block">Searches</span>
                        <span className="font-bold text-slate-200">{selectedCycle.searches_executed_count}</span>
                      </div>
                      <div className="rounded bg-slate-900/50 p-2 border border-border/40">
                        <span className="text-slate-500 block">Sources Acquired</span>
                        <span className="font-bold text-emerald-400">+{selectedCycle.sources_acquired_count}</span>
                      </div>
                      <div className="rounded bg-slate-900/50 p-2 border border-border/40">
                        <span className="text-slate-500 block">Claims Reevaluated</span>
                        <span className="font-bold text-amber-400">{selectedCycle.claims_reevaluated_count}</span>
                      </div>
                    </div>

                    {/* Actions for this cycle */}
                    <div className="space-y-2 mt-4">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Planned Actions ({actions.filter((a) => a.cycle_id === selectedCycle.id).length})
                      </h4>

                      <div className="space-y-2">
                        {actions
                          .filter((a) => a.cycle_id === selectedCycle.id)
                          .map((act) => (
                            <div
                              key={act.id}
                              className="rounded-lg border border-border/60 bg-slate-900/40 p-3 text-xs space-y-1.5"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-white">
                                    {act.action_type.replace("_", " ")}
                                  </span>
                                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                                    Pri {act.priority}
                                  </span>
                                </div>
                                <span className={`rounded-full px-2 py-0.5 text-[10px] border ${statusBadge(act.status)}`}>
                                  {act.status}
                                </span>
                              </div>

                              {act.planned_query && (
                                <div className="font-mono text-cyan-300 text-[11px] bg-black/30 p-1.5 rounded">
                                  Query: &ldquo;{act.planned_query}&rdquo;
                                </div>
                              )}

                              <p className="text-slate-400">{act.action_rationale}</p>

                              {act.result_summary && (
                                <div className="text-emerald-400/90 text-[11px] mt-1 pt-1 border-t border-border/30">
                                  Result: {act.result_summary}
                                </div>
                              )}
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No cycles recorded yet.</p>
                )}
              </div>

              {/* Synthesized Final Report View (if available) */}
              {report && (
                <div className="rounded-xl border border-cyan-500/40 bg-surface p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-border pb-3">
                    <h3 className="text-sm font-semibold text-cyan-300 flex items-center gap-2">
                      <span>📄</span> Synthesized Autonomous Research Report
                    </h3>
                    <span className="text-xs text-slate-400">
                      Tier: {report.calibrated_quality_tier || "Calibrated"}
                      {report.calibrated_quality_score != null && ` · Score: ${report.calibrated_quality_score.toFixed(1)}`}
                    </span>
                  </div>

                  <div className="prose prose-invert prose-sm max-w-none space-y-3 text-xs text-slate-300">
                    <div>
                      <h4 className="font-semibold text-white uppercase text-[11px] tracking-wider mb-1">Executive Summary</h4>
                      <p className="bg-slate-900/60 p-3 rounded-lg border border-border/50 text-slate-300 leading-relaxed">
                        {report.executive_summary}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      <div className="rounded border border-border/60 bg-slate-900/40 p-2">
                        <span className="text-slate-500 block text-[10px]">Sources Acquired</span>
                        <span className="font-bold text-emerald-400">{report.total_sources_acquired ?? 0}</span>
                      </div>
                      <div className="rounded border border-border/60 bg-slate-900/40 p-2">
                        <span className="text-slate-500 block text-[10px]">Evidence Extracted</span>
                        <span className="font-bold text-amber-400">{report.total_evidence_extracted ?? 0}</span>
                      </div>
                      <div className="rounded border border-border/60 bg-slate-900/40 p-2">
                        <span className="text-slate-500 block text-[10px]">Claims Reassessed</span>
                        <span className="font-bold text-cyan-400">{report.claims_reassessed_count ?? 0}</span>
                      </div>
                      <div className="rounded border border-border/60 bg-slate-900/40 p-2">
                        <span className="text-slate-500 block text-[10px]">Contradictions Resolved</span>
                        <span className="font-bold text-purple-400">{report.contradictions_resolved_count ?? 0}</span>
                      </div>
                    </div>

                    {report.remaining_uncertainties && report.remaining_uncertainties.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-white uppercase text-[11px] tracking-wider mb-1">Persistent Uncertainties</h4>
                        <ul className="list-disc pl-4 space-y-1 text-slate-300">
                          {report.remaining_uncertainties.map((u, i) => (
                            <li key={i}>{u}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {report.recommended_next_actions && report.recommended_next_actions.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-white uppercase text-[11px] tracking-wider mb-1">Recommended Next Actions</h4>
                        <ul className="list-disc pl-4 space-y-1 text-slate-300">
                          {report.recommended_next_actions.map((rec, i) => (
                            <li key={i}>
                              <span className="font-medium text-amber-300">{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Create Workflow Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>⚡</span> Launch Autonomous Research Loop
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCreateWorkflow} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Workflow Title</label>
                <input
                  type="text"
                  required
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Research Objective</label>
                <textarea
                  rows={2}
                  value={createObjective}
                  onChange={(e) => setCreateObjective(e.target.value)}
                  className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Autonomy Mode</label>
                  <select
                    value={createMode}
                    onChange={(e) => setCreateMode(e.target.value as any)}
                    className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  >
                    <option value="bounded">Bounded (Autonomous)</option>
                    <option value="supervised">Supervised (Checkpoints)</option>
                    <option value="assisted">Assisted (Review Actions)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Max Cycles</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={createMaxCycles}
                    onChange={(e) => setCreateMaxCycles(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Searches/Cycle</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={createMaxSearches}
                    onChange={(e) => setCreateMaxSearches(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Max Sources Total</label>
                  <input
                    type="number"
                    min={5}
                    max={100}
                    value={createMaxSources}
                    onChange={(e) => setCreateMaxSources(parseInt(e.target.value) || 5)}
                    className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Max Duration (min)</label>
                  <input
                    type="number"
                    min={5}
                    max={180}
                    value={createMaxDuration}
                    onChange={(e) => setCreateMaxDuration(parseInt(e.target.value) || 5)}
                    className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-border px-4 py-2 text-slate-300 hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 transition shadow-sm"
                >
                  Create Workflow
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Continue Modal */}
      {showContinueModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>↻</span> Extend Autonomous Research Cycles
              </h3>
              <button onClick={() => setShowContinueModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleContinueWorkflow} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Additional Cycles to Execute</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={additionalCycles}
                  onChange={(e) => setAdditionalCycles(parseInt(e.target.value) || 1)}
                  className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Reason for Extension</label>
                <textarea
                  rows={2}
                  value={continueNotes}
                  onChange={(e) => setContinueNotes(e.target.value)}
                  placeholder="e.g. Further investigate newly emerged counter-evidence..."
                  className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowContinueModal(false)}
                  className="rounded-lg border border-border px-4 py-2 text-slate-300 hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-4 py-2 transition shadow-sm"
                >
                  Continue Workflow
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Action Modal */}
      {reviewAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-rose-500/40 bg-surface p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-rose-300 flex items-center gap-2">
                <span>✕</span> Reject Research Action
              </h3>
              <button onClick={() => setReviewAction(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="text-xs space-y-3">
              <p className="text-slate-300">
                Are you sure you want to reject action: <strong>{reviewAction.action_type}</strong>?
              </p>
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Rejection Reason</label>
                <textarea
                  rows={2}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Explain why this action should not be executed..."
                  className="w-full rounded-lg bg-slate-900 border border-border px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-rose-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setReviewAction(null)}
                  className="rounded-lg border border-border px-4 py-2 text-slate-300 hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleRejectAction(reviewAction)}
                  className="rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium px-4 py-2 transition shadow-sm"
                >
                  Confirm Rejection
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
