"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getWorkspace,
  getWorkspaceActivity,
  Workspace,
  WorkspaceActivity,
} from "@/lib/collaboration";

export default function WorkspaceActivityPage() {
  const params = useParams();
  const workspaceId = params.id as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [activities, setActivities] = useState<WorkspaceActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [ws, acts] = await Promise.all([
        getWorkspace(workspaceId),
        getWorkspaceActivity(workspaceId, 100),
      ]);
      setWorkspace(ws);
      setActivities(acts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load activity feed.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId) {
      loadData();
    }
  }, [workspaceId, loadData]);

  const filteredActivities = activities.filter((act) => {
    if (filterAction === "all") return true;
    return act.action_type.includes(filterAction) || act.entity_type === filterAction;
  });

  return (
    <div style={{ padding: "36px 40px", maxWidth: "1100px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <Link href={`/workspaces/${workspaceId}`} style={{ color: "#60a5fa", textDecoration: "none", fontSize: "13px" }}>
              ← {workspace?.name || "Workspace"}
            </Link>
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
            Workspace Activity & Scientific Audit Log
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: "4px 0 0" }}>
            Immutable chronological record of evidence, investigations, peer reviews, and membership actions.
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          style={{
            padding: "8px 14px",
            background: "#1e293b",
            color: "#cbd5e1",
            border: "1px solid #334155",
            borderRadius: "6px",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {loading ? "Refreshing..." : "↻ Refresh Feed"}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1a263d", marginBottom: "28px", paddingBottom: "8px" }}>
        <Link href={`/workspaces/${workspaceId}`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Overview
        </Link>
        <Link href={`/workspaces/${workspaceId}/members`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Members
        </Link>
        <Link href={`/workspaces/${workspaceId}/activity`} style={{ padding: "8px 16px", color: "#38bdf8", borderBottom: "2px solid #38bdf8", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
          Activity Feed
        </Link>
        <Link href={`/workspaces/${workspaceId}/settings`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Settings & Policies
        </Link>
      </div>

      {/* Filter Toolbar */}
      <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "20px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: 500 }}>Filter by category:</span>
        {[
          { label: "All Activities", value: "all" },
          { label: "Investigations", value: "investigation" },
          { label: "Reviews", value: "review" },
          { label: "Annotations", value: "annotation" },
          { label: "Discussions", value: "comment" },
          { label: "Membership", value: "member" },
        ].map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilterAction(f.value)}
            style={{
              padding: "5px 12px",
              background: filterAction === f.value ? "#2563eb" : "#0f172a",
              color: filterAction === f.value ? "#fff" : "#94a3b8",
              border: `1px solid ${filterAction === f.value ? "#3b82f6" : "#1e293b"}`,
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Activity List */}
      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {loading && activities.length === 0 ? (
        <div style={{ padding: "40px", color: "#94a3b8", textAlign: "center" }}>
          Loading audit feed...
        </div>
      ) : filteredActivities.length === 0 ? (
        <div style={{ background: "#0f172a", border: "1px dashed #1e293b", padding: "40px 20px", textAlign: "center", borderRadius: "10px", color: "#64748b", fontSize: "13px" }}>
          No activity recorded under this filter yet.
        </div>
      ) : (
        <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", overflow: "hidden" }}>
          {filteredActivities.map((act, index) => {
            const isLast = index === filteredActivities.length - 1;
            const actionBadgeColor = act.action_type.includes("review")
              ? "#8b5cf6"
              : act.action_type.includes("create")
              ? "#10b981"
              : act.action_type.includes("annotate")
              ? "#f59e0b"
              : act.action_type.includes("member")
              ? "#38bdf8"
              : "#64748b";

            return (
              <div
                key={act.id}
                style={{
                  padding: "16px 20px",
                  borderBottom: isLast ? "none" : "1px solid #1e293b",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: actionBadgeColor,
                    marginTop: "6px",
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, color: "#f8fafc", fontSize: "13px" }}>
                      {act.actor_name}
                    </span>
                    <span
                      style={{
                        background: "#1e293b",
                        color: actionBadgeColor,
                        borderRadius: "4px",
                        padding: "1px 6px",
                        fontSize: "11px",
                        fontWeight: 600,
                        fontFamily: "monospace",
                      }}
                    >
                      {act.action_type}
                    </span>
                    <span style={{ color: "#64748b", fontSize: "12px", marginLeft: "auto" }}>
                      {act.created_at ? new Date(act.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <p style={{ margin: "0 0 6px", color: "#cbd5e1", fontSize: "13px" }}>
                    {act.summary}
                  </p>
                  {act.metadata && Object.keys(act.metadata).length > 0 && (
                    <div style={{ background: "#080e1a", border: "1px solid #172554", borderRadius: "6px", padding: "8px 12px", fontSize: "11px", color: "#93c5fd", fontFamily: "monospace", overflowX: "auto" }}>
                      {JSON.stringify(act.metadata)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
