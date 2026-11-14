"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  getWorkspace,
  updateWorkspace,
  archiveWorkspace,
  restoreWorkspace,
  transferOwnership,
  listWorkspaceMembers,
  Workspace,
  WorkspaceMember,
} from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

export default function WorkspaceSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const { user, refreshAuth } = useAuth();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [requireIndependentReview, setRequireIndependentReview] = useState(true);
  const [maxAutonomousBudget, setMaxAutonomousBudget] = useState(50);
  const [allowMemberInvitations, setAllowMemberInvitations] = useState(true);

  // Ownership transfer
  const [selectedNewOwner, setSelectedNewOwner] = useState("");
  const [transferring, setTransferring] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [ws, mems] = await Promise.all([
        getWorkspace(workspaceId),
        listWorkspaceMembers(workspaceId).catch(() => []),
      ]);
      setWorkspace(ws);
      setMembers(mems);
      setName(ws.name);
      setDescription(ws.description || "");
      setRequireIndependentReview(ws.settings?.require_independent_review ?? true);
      setMaxAutonomousBudget(Number(ws.settings?.max_autonomous_budget ?? 50));
      setAllowMemberInvitations(ws.settings?.allow_member_invitations ?? true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load workspace settings.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId) {
      loadData();
    }
  }, [workspaceId, loadData]);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateWorkspace(workspaceId, name, description, {
        require_independent_review: requireIndependentReview,
        max_autonomous_budget: maxAutonomousBudget,
        allow_member_invitations: allowMemberInvitations,
      });
      setWorkspace(updated);
      setSuccess("Workspace settings updated successfully.");
      await refreshAuth();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update workspace.");
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!confirm("Are you sure you want to archive this workspace? Active investigations will become read-only.")) return;
    setError(null);
    try {
      await archiveWorkspace(workspaceId);
      await loadData();
      await refreshAuth();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to archive workspace.");
    }
  };

  const handleRestore = async () => {
    setError(null);
    try {
      await restoreWorkspace(workspaceId);
      await loadData();
      await refreshAuth();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to restore workspace.");
    }
  };

  const handleTransferOwnership = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNewOwner) return;
    const target = members.find((m) => m.user_id === selectedNewOwner);
    if (!confirm(`Are you sure you want to transfer ownership of this workspace to ${target?.display_name || "this user"}? You will become an Admin.`)) return;

    setTransferring(true);
    setError(null);
    try {
      await transferOwnership(workspaceId, selectedNewOwner);
      setSuccess("Ownership transferred successfully.");
      await loadData();
      await refreshAuth();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to transfer ownership.");
    } finally {
      setTransferring(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "40px", color: "#94a3b8", textAlign: "center" }}>
        Loading workspace governance & settings...
      </div>
    );
  }

  if (error && !workspace) {
    return (
      <div style={{ padding: "40px 32px", maxWidth: "800px", margin: "0 auto" }}>
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "16px", borderRadius: "8px" }}>
          <h2 style={{ fontSize: "16px", margin: "0 0 6px" }}>Error Loading Settings</h2>
          <p style={{ margin: 0, fontSize: "13px" }}>{error}</p>
        </div>
      </div>
    );
  }

  const isOwnerOrAdmin = workspace?.user_role === "owner" || workspace?.user_role === "admin";
  const isOwner = workspace?.user_role === "owner";

  return (
    <div style={{ padding: "36px 40px", maxWidth: "900px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            <Link href={`/workspaces/${workspaceId}`} style={{ color: "#60a5fa", textDecoration: "none", fontSize: "13px" }}>
              ← {workspace?.name}
            </Link>
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
            Workspace Settings & Governance
          </h1>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1a263d", marginBottom: "28px", paddingBottom: "8px" }}>
        <Link href={`/workspaces/${workspaceId}`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Overview
        </Link>
        <Link href={`/workspaces/${workspaceId}/members`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Members ({members.length})
        </Link>
        <Link href={`/workspaces/${workspaceId}/activity`} style={{ padding: "8px 16px", color: "#94a3b8", fontSize: "13px", fontWeight: 500, textDecoration: "none" }}>
          Activity Feed
        </Link>
        <Link href={`/workspaces/${workspaceId}/settings`} style={{ padding: "8px 16px", color: "#38bdf8", borderBottom: "2px solid #38bdf8", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
          Settings & Policies
        </Link>
      </div>

      {/* Notifications */}
      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{ background: "#064e3b", border: "1px solid #059669", color: "#a7f3d0", padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {success}
        </div>
      )}

      {/* General Settings Form */}
      <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", padding: "24px", marginBottom: "28px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "0 0 16px" }}>
          General Information
        </h2>
        <form onSubmit={handleSaveGeneral}>
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", color: "#cbd5e1", fontSize: "13px", fontWeight: 500, marginBottom: "6px" }}>
              Workspace Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isOwnerOrAdmin}
              required
              style={{
                width: "100%",
                padding: "9px 12px",
                background: "#080e1a",
                border: "1px solid #1e293b",
                borderRadius: "6px",
                color: "#f8fafc",
                fontSize: "13px",
              }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", color: "#cbd5e1", fontSize: "13px", fontWeight: 500, marginBottom: "6px" }}>
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={!isOwnerOrAdmin}
              rows={3}
              style={{
                width: "100%",
                padding: "9px 12px",
                background: "#080e1a",
                border: "1px solid #1e293b",
                borderRadius: "6px",
                color: "#f8fafc",
                fontSize: "13px",
                resize: "vertical",
              }}
            />
          </div>

          <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#e2e8f0", margin: "20px 0 12px", borderTop: "1px solid #1e293b", paddingTop: "16px" }}>
            Scientific Governance & Review Policies
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginBottom: "20px" }}>
            <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: isOwnerOrAdmin ? "pointer" : "default" }}>
              <input
                type="checkbox"
                checked={requireIndependentReview}
                onChange={(e) => setRequireIndependentReview(e.target.checked)}
                disabled={!isOwnerOrAdmin}
                style={{ marginTop: "3px" }}
              />
              <div>
                <span style={{ color: "#f8fafc", fontSize: "13px", fontWeight: 600 }}>
                  Enforce Independent Peer Review (Anti-Self-Approval Guard)
                </span>
                <p style={{ margin: "2px 0 0", color: "#94a3b8", fontSize: "12px" }}>
                  When enabled, investigation authors cannot approve their own review requests. Approval requires an independent peer researcher or admin.
                </p>
              </div>
            </label>

            <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: isOwnerOrAdmin ? "pointer" : "default" }}>
              <input
                type="checkbox"
                checked={allowMemberInvitations}
                onChange={(e) => setAllowMemberInvitations(e.target.checked)}
                disabled={!isOwnerOrAdmin}
                style={{ marginTop: "3px" }}
              />
              <div>
                <span style={{ color: "#f8fafc", fontSize: "13px", fontWeight: 600 }}>
                  Allow Researchers to Invite Collaborators
                </span>
                <p style={{ margin: "2px 0 0", color: "#94a3b8", fontSize: "12px" }}>
                  Allow researchers to generate invitation tokens. If disabled, only workspace owners and admins can invite new members.
                </p>
              </div>
            </label>

            <div>
              <label style={{ display: "block", color: "#cbd5e1", fontSize: "13px", fontWeight: 500, marginBottom: "4px" }}>
                Maximum Autonomous Budget ($ or Cycles)
              </label>
              <input
                type="number"
                min="1"
                max="500"
                value={maxAutonomousBudget}
                onChange={(e) => setMaxAutonomousBudget(Number(e.target.value))}
                disabled={!isOwnerOrAdmin}
                style={{
                  width: "200px",
                  padding: "8px 12px",
                  background: "#080e1a",
                  border: "1px solid #1e293b",
                  borderRadius: "6px",
                  color: "#f8fafc",
                  fontSize: "13px",
                }}
              />
              <span style={{ marginLeft: "10px", color: "#64748b", fontSize: "12px" }}>Maximum limit for automated workflow executions.</span>
            </div>
          </div>

          {isOwnerOrAdmin && (
            <button
              type="submit"
              disabled={saving}
              style={{
                padding: "8px 18px",
                background: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: saving ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "Saving Changes..." : "Save Policies & Settings"}
            </button>
          )}
        </form>
      </div>

      {/* Lifecycle Actions */}
      <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", padding: "24px", marginBottom: "28px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "0 0 8px" }}>
          Workspace Lifecycle Status
        </h2>
        <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 16px" }}>
          Current status: <strong style={{ color: workspace?.status === "active" ? "#34d399" : "#fbbf24", textTransform: "uppercase" }}>{workspace?.status}</strong>
        </p>

        {isOwnerOrAdmin && (
          <div>
            {workspace?.status === "active" ? (
              <button
                type="button"
                onClick={handleArchive}
                style={{
                  padding: "8px 16px",
                  background: "#451a03",
                  color: "#fde68a",
                  border: "1px solid #b45309",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Archive Workspace
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRestore}
                style={{
                  padding: "8px 16px",
                  background: "#064e3b",
                  color: "#a7f3d0",
                  border: "1px solid #059669",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Restore Workspace
              </button>
            )}
          </div>
        )}
      </div>

      {/* Danger Zone: Ownership Transfer */}
      {isOwner && (
        <div style={{ background: "#1c1117", border: "1px solid #831843", borderRadius: "10px", padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f43f5e", margin: "0 0 8px" }}>
            Danger Zone: Transfer Workspace Ownership
          </h2>
          <p style={{ color: "#fda4af", fontSize: "13px", margin: "0 0 16px" }}>
            Transferring ownership to another team member is immediate and cannot be undone without the new owner re-transferring it back.
          </p>

          <form onSubmit={handleTransferOwnership} style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={selectedNewOwner}
              onChange={(e) => setSelectedNewOwner(e.target.value)}
              required
              style={{
                padding: "8px 12px",
                background: "#080e1a",
                border: "1px solid #831843",
                borderRadius: "6px",
                color: "#f8fafc",
                fontSize: "13px",
                minWidth: "250px",
              }}
            >
              <option value="">Select a member...</option>
              {members
                .filter((m) => m.user_id !== user?.id)
                .map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name} ({m.email}) - {m.role}
                  </option>
                ))}
            </select>
            <button
              type="submit"
              disabled={!selectedNewOwner || transferring}
              style={{
                padding: "8px 18px",
                background: "#e11d48",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: !selectedNewOwner || transferring ? "not-allowed" : "pointer",
              }}
            >
              {transferring ? "Transferring..." : "Transfer Ownership"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
