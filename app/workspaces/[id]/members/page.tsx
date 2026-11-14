"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getWorkspace,
  listWorkspaceMembers,
  updateMemberRole,
  removeMember,
  inviteMember,
  listWorkspaceInvitations,
  revokeInvitation,
  Workspace,
  WorkspaceMember,
  WorkspaceInvitation,
} from "@/lib/collaboration";

export default function WorkspaceMembersPage() {
  const params = useParams();
  const workspaceId = params.id as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [loading, setLoading] = useState(true);

  // Invite modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("researcher");
  const [inviting, setInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{ link?: string | null; token?: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [ws, mems, invites] = await Promise.all([
        getWorkspace(workspaceId),
        listWorkspaceMembers(workspaceId),
        listWorkspaceInvitations(workspaceId).catch(() => []),
      ]);
      setWorkspace(ws);
      setMembers(mems);
      setInvitations(invites);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load members.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId) {
      loadData();
    }
  }, [workspaceId, loadData]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateMemberRole(workspaceId, userId, newRole);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update role.");
    }
  };

  const handleRemoveMember = async (userId: string, name: string) => {
    if (!confirm(`Are you sure you want to remove ${name} from this workspace?`)) return;
    try {
      await removeMember(workspaceId, userId);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to remove member.");
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    setError(null);
    try {
      const res = await inviteMember(workspaceId, inviteEmail, inviteRole);
      setInviteResult({ link: res.invite_link, token: res.invite_token });
      setInviteEmail("");
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to invite member.");
    } finally {
      setInviting(false);
    }
  };

  const handleRevokeInvite = async (invitationId: string) => {
    try {
      await revokeInvitation(workspaceId, invitationId);
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to revoke invitation.");
    }
  };

  const canManage = workspace?.user_role === "owner" || workspace?.user_role === "admin";

  return (
    <div style={{ padding: "36px 40px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>
            <Link href={`/workspaces/${workspaceId}`} style={{ color: "inherit", textDecoration: "none" }}>
              ← {workspace?.name || "Workspace"}
            </Link>
          </div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
            Team & Access Governance
          </h1>
        </div>

        {canManage && (
          <button
            type="button"
            onClick={() => {
              setInviteResult(null);
              setError(null);
              setShowInviteModal(true);
            }}
            style={{
              padding: "8px 16px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Invite Member
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading members...</div>
      ) : (
        <div style={{ display: "grid", gap: "32px" }}>
          {/* Members Table */}
          <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e293b", fontWeight: 600, color: "#f8fafc", fontSize: "14px" }}>
              Active Members ({members.length})
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "#080d1a", color: "#64748b", borderBottom: "1px solid #1e293b" }}>
                  <th style={{ padding: "12px 20px" }}>Researcher</th>
                  <th style={{ padding: "12px 20px" }}>Email</th>
                  <th style={{ padding: "12px 20px" }}>Role</th>
                  <th style={{ padding: "12px 20px" }}>Joined</th>
                  {canManage && <th style={{ padding: "12px 20px", textAlign: "right" }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id} style={{ borderBottom: "1px solid #141f33" }}>
                    <td style={{ padding: "14px 20px", color: "#f8fafc", fontWeight: 500 }}>
                      {m.display_name}
                    </td>
                    <td style={{ padding: "14px 20px", color: "#94a3b8" }}>{m.email}</td>
                    <td style={{ padding: "14px 20px" }}>
                      {canManage && m.role !== "owner" ? (
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                          style={{
                            background: "#080d1a",
                            border: "1px solid #334155",
                            color: "#93c5fd",
                            padding: "4px 8px",
                            borderRadius: "4px",
                            fontSize: "12px",
                            textTransform: "uppercase",
                          }}
                        >
                          <option value="researcher">Researcher</option>
                          <option value="reviewer">Reviewer</option>
                          <option value="viewer">Viewer</option>
                          {workspace?.user_role === "owner" && <option value="admin">Admin</option>}
                        </select>
                      ) : (
                        <span
                          style={{
                            background: "#1e3a5f",
                            color: "#93c5fd",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            textTransform: "uppercase",
                            fontWeight: 600,
                          }}
                        >
                          {m.role}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "14px 20px", color: "#64748b" }}>
                      {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"}
                    </td>
                    {canManage && (
                      <td style={{ padding: "14px 20px", textAlign: "right" }}>
                        {m.role !== "owner" && (
                          <button
                            type="button"
                            onClick={() => handleRemoveMember(m.user_id, m.display_name)}
                            style={{
                              background: "transparent",
                              border: "1px solid #7f1d1d",
                              color: "#f87171",
                              padding: "4px 10px",
                              borderRadius: "4px",
                              fontSize: "11px",
                              cursor: "pointer",
                            }}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pending Invitations Table */}
          {invitations.length > 0 && (
            <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", overflow: "hidden" }}>
              <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e293b", fontWeight: 600, color: "#f8fafc", fontSize: "14px" }}>
                Pending Invitations ({invitations.filter((i) => i.status === "pending").length})
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#080d1a", color: "#64748b", borderBottom: "1px solid #1e293b" }}>
                    <th style={{ padding: "12px 20px" }}>Invited Email</th>
                    <th style={{ padding: "12px 20px" }}>Role</th>
                    <th style={{ padding: "12px 20px" }}>Invited By</th>
                    <th style={{ padding: "12px 20px" }}>Status</th>
                    {canManage && <th style={{ padding: "12px 20px", textAlign: "right" }}>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((inv) => (
                    <tr key={inv.id} style={{ borderBottom: "1px solid #141f33" }}>
                      <td style={{ padding: "12px 20px", color: "#f8fafc" }}>{inv.email}</td>
                      <td style={{ padding: "12px 20px", textTransform: "uppercase", color: "#93c5fd", fontSize: "11px", fontWeight: 600 }}>
                        {inv.role}
                      </td>
                      <td style={{ padding: "12px 20px", color: "#94a3b8" }}>{inv.inviter_name || "Admin"}</td>
                      <td style={{ padding: "12px 20px" }}>
                        <span
                          style={{
                            background: inv.status === "pending" ? "#78350f" : "#1e293b",
                            color: inv.status === "pending" ? "#fcd34d" : "#94a3b8",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            textTransform: "uppercase",
                          }}
                        >
                          {inv.status}
                        </span>
                      </td>
                      {canManage && (
                        <td style={{ padding: "12px 20px", textAlign: "right" }}>
                          {inv.status === "pending" && (
                            <button
                              type="button"
                              onClick={() => handleRevokeInvite(inv.id)}
                              style={{
                                background: "transparent",
                                border: "1px solid #7f1d1d",
                                color: "#f87171",
                                padding: "4px 8px",
                                borderRadius: "4px",
                                fontSize: "11px",
                                cursor: "pointer",
                              }}
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(4px)",
            display: "grid",
            placeItems: "center",
            padding: "20px",
            zIndex: 100,
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "480px",
              background: "#0d1527",
              border: "1px solid #334155",
              borderRadius: "12px",
              padding: "28px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
                Invite Researcher to Workspace
              </h2>
              <button
                type="button"
                onClick={() => setShowInviteModal(false)}
                style={{ background: "transparent", border: "none", color: "#64748b", fontSize: "18px", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            {error && (
              <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "10px", borderRadius: "6px", fontSize: "12px", marginBottom: "14px" }}>
                {error}
              </div>
            )}

            {inviteResult ? (
              <div style={{ display: "grid", gap: "14px" }}>
                <div style={{ background: "#064e3b", border: "1px solid #059669", color: "#a7f3d0", padding: "12px", borderRadius: "6px", fontSize: "13px" }}>
                  Invitation successfully generated! Share this link or token with the invitee:
                </div>
                <div>
                  <label htmlFor="inv-link-display" style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Invitation Link</label>
                  <input
                    id="inv-link-display"
                    type="text"
                    readOnly
                    value={`${typeof window !== "undefined" ? window.location.origin : ""}${inviteResult.link}`}
                    style={{ width: "100%", padding: "8px", background: "#080d1a", border: "1px solid #334155", color: "#38bdf8", borderRadius: "6px", fontSize: "12px", fontFamily: "monospace", boxSizing: "border-box" }}
                  />
                </div>
                <div>
                  <label htmlFor="inv-token-display" style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Invitation Token</label>
                  <input
                    id="inv-token-display"
                    type="text"
                    readOnly
                    value={inviteResult.token || ""}
                    style={{ width: "100%", padding: "8px", background: "#080d1a", border: "1px solid #334155", color: "#cbd5e1", borderRadius: "6px", fontSize: "12px", fontFamily: "monospace", boxSizing: "border-box" }}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  style={{ padding: "9px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer", marginTop: "8px" }}
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleInvite} style={{ display: "grid", gap: "14px" }}>
                <div>
                  <label htmlFor="inv-email-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "4px" }}>
                    Colleague's Email
                  </label>
                  <input
                    id="inv-email-input"
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="peer.reviewer@university.edu"
                    style={{ width: "100%", padding: "9px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label htmlFor="inv-role-select" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "4px" }}>
                    Assigned Workspace Role
                  </label>
                  <select
                    id="inv-role-select"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    style={{ width: "100%", padding: "9px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
                  >
                    <option value="researcher">Researcher (can formulate queries, add evidence, discuss)</option>
                    <option value="reviewer">Reviewer (can inspect, annotate, evaluate & approve peer reviews)</option>
                    <option value="viewer">Viewer (read-only observer access)</option>
                    {workspace?.user_role === "owner" && <option value="admin">Admin (co-manage members and workspace settings)</option>}
                  </select>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                  <button
                    type="button"
                    onClick={() => setShowInviteModal(false)}
                    style={{ padding: "8px 14px", background: "#1e293b", color: "#cbd5e1", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={inviting}
                    style={{ padding: "8px 18px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: inviting ? "not-allowed" : "pointer" }}
                  >
                    {inviting ? "Sending..." : "Send Invitation"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
