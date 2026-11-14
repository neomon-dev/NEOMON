"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  getWorkspace,
  listWorkspaceMembers,
  getWorkspaceActivity,
  listReviewRequests,
  Workspace,
  WorkspaceMember,
  WorkspaceActivity,
  ReviewRequest,
} from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

export default function WorkspaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const { switchWorkspace } = useAuth();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [activities, setActivities] = useState<WorkspaceActivity[]>([]);
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadWorkspaceData() {
      try {
        setLoading(true);
        const [ws, mems, acts, revs] = await Promise.all([
          getWorkspace(workspaceId),
          listWorkspaceMembers(workspaceId).catch(() => []),
          getWorkspaceActivity(workspaceId, 15).catch(() => []),
          listReviewRequests({ workspace_id: workspaceId }).catch(() => []),
        ]);
        setWorkspace(ws);
        setMembers(mems);
        setActivities(acts);
        setReviews(revs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load workspace.");
      } finally {
        setLoading(false);
      }
    }
    if (workspaceId) {
      loadWorkspaceData();
    }
  }, [workspaceId]);

  if (loading) {
    return (
      <div style={{ padding: "40px", color: "#94a3b8", textAlign: "center" }}>
        Loading research workspace...
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div style={{ padding: "40px 32px", maxWidth: "800px", margin: "0 auto" }}>
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "16px", borderRadius: "8px" }}>
          <h2 style={{ fontSize: "16px", margin: "0 0 6px" }}>Error Loading Workspace</h2>
          <p style={{ margin: 0, fontSize: "13px" }}>{error || "Workspace not found or access denied."}</p>
        </div>
        <div style={{ marginTop: "20px" }}>
          <Link href="/workspaces" style={{ color: "#60a5fa", textDecoration: "none", fontSize: "13px" }}>
            ← Back to all workspaces
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "36px 40px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Workspace Hub Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
              {workspace.name}
            </h1>
            {workspace.user_role && (
              <span
                style={{
                  background: "#1e3a5f",
                  color: "#93c5fd",
                  borderRadius: "4px",
                  padding: "2px 8px",
                  fontSize: "11px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                }}
              >
                {workspace.user_role}
              </span>
            )}
            <span
              style={{
                background: workspace.status === "active" ? "#064e3b" : "#451a03",
                color: workspace.status === "active" ? "#34d399" : "#fbbf24",
                borderRadius: "4px",
                padding: "2px 8px",
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              {workspace.status}
            </span>
          </div>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            {workspace.description || "Collaborative multi-user research workspace."}
          </p>
        </div>

        {/* Header Actions */}
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={() => {
              switchWorkspace(workspace.id);
            }}
            style={{
              padding: "8px 14px",
              background: "#1e293b",
              color: "#cbd5e1",
              border: "none",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Set as Active
          </button>
          <Link
            href="/investigations/new"
            style={{
              padding: "8px 16px",
              background: "#2563eb",
              color: "#fff",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            + New Investigation
          </Link>
        </div>
      </div>

      {/* Workspace Hub Navigation Tabs */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid #1a263d",
          marginBottom: "28px",
          paddingBottom: "8px",
        }}
      >
        <Link
          href={`/workspaces/${workspaceId}`}
          style={{
            padding: "8px 16px",
            color: "#38bdf8",
            borderBottom: "2px solid #38bdf8",
            fontSize: "13px",
            fontWeight: 600,
            textDecoration: "none",
          }}
        >
          Overview
        </Link>
        <Link
          href={`/workspaces/${workspaceId}/members`}
          style={{
            padding: "8px 16px",
            color: "#94a3b8",
            fontSize: "13px",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Members ({members.length})
        </Link>
        <Link
          href={`/workspaces/${workspaceId}/activity`}
          style={{
            padding: "8px 16px",
            color: "#94a3b8",
            fontSize: "13px",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Audit Stream
        </Link>
        <Link
          href="/reviews"
          style={{
            padding: "8px 16px",
            color: "#94a3b8",
            fontSize: "13px",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Peer Reviews ({reviews.length})
        </Link>
        <Link
          href={`/workspaces/${workspaceId}/settings`}
          style={{
            padding: "8px 16px",
            color: "#94a3b8",
            fontSize: "13px",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Settings
        </Link>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "8px", padding: "18px" }}>
          <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>Investigations</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", marginTop: "4px" }}>
            {workspace.investigation_count}
          </div>
        </div>
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "8px", padding: "18px" }}>
          <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>Investigators</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", marginTop: "4px" }}>
            {workspace.member_count}
          </div>
        </div>
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "8px", padding: "18px" }}>
          <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>Active Reviews</div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", marginTop: "4px" }}>
            {reviews.filter((r) => r.status === "submitted" || r.status === "under_review").length}
          </div>
        </div>
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "8px", padding: "18px" }}>
          <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase" }}>Governance Policy</div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "#38bdf8", marginTop: "8px" }}>
            {workspace.settings?.require_independent_review ? "Independent Review Enforced" : "Standard Review"}
          </div>
        </div>
      </div>

      {/* Two Column Layout: Team + Activity */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "start" }}>
        {/* Team Members Card */}
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: 0 }}>Team Members</h2>
            <Link href={`/workspaces/${workspaceId}/members`} style={{ fontSize: "12px", color: "#60a5fa", textDecoration: "none" }}>
              Manage →
            </Link>
          </div>
          <div style={{ display: "grid", gap: "10px" }}>
            {members.slice(0, 5).map((m) => (
              <div
                key={m.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 10px",
                  background: "#080d1a",
                  borderRadius: "6px",
                  border: "1px solid #1a263d",
                }}
              >
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 500, color: "#f8fafc" }}>{m.display_name}</div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>{m.email}</div>
                </div>
                <span
                  style={{
                    background: "#1e3a5f",
                    color: "#93c5fd",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    fontSize: "10px",
                    textTransform: "uppercase",
                    fontWeight: 600,
                  }}
                >
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity Audit Feed */}
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: 0 }}>Recent Activity Feed</h2>
            <Link href={`/workspaces/${workspaceId}/activity`} style={{ fontSize: "12px", color: "#60a5fa", textDecoration: "none" }}>
              Full Audit Stream →
            </Link>
          </div>
          <div style={{ display: "grid", gap: "10px" }}>
            {activities.length === 0 ? (
              <div style={{ fontSize: "12px", color: "#64748b", padding: "12px 0" }}>No recorded activities yet.</div>
            ) : (
              activities.slice(0, 6).map((a) => (
                <div
                  key={a.id}
                  style={{
                    padding: "8px 10px",
                    background: "#080d1a",
                    borderRadius: "6px",
                    border: "1px solid #1a263d",
                    fontSize: "12px",
                  }}
                >
                  <div style={{ color: "#cbd5e1", lineHeight: 1.4 }}>{a.summary}</div>
                  <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>
                    {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
