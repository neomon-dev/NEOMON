"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { createWorkspace, Workspace } from "@/lib/collaboration";

export default function WorkspacesPage() {
  const { workspaces, activeWorkspace, switchWorkspace, refreshAuth, user, isLoading } = useAuth();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [requireReview, setRequireReview] = useState(true);
  const [maxBudget, setMaxBudget] = useState(50);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const ws = await createWorkspace(name, description, {
        require_independent_review: requireReview,
        max_autonomous_budget: maxBudget,
      });
      await refreshAuth();
      switchWorkspace(ws.id);
      setShowCreateModal(false);
      setName("");
      setDescription("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create workspace.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ padding: "36px 40px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: "0 0 6px" }}>
            Research Workspaces
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            Collaborative environments for shared evidence, multi-investigator reviews, and access governance.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          style={{
            padding: "9px 18px",
            background: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span>+</span> Create Workspace
        </button>
      </div>

      {!user && !isLoading && (
        <div
          style={{
            background: "rgba(14, 165, 233, 0.1)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            borderRadius: "8px",
            padding: "16px 20px",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <p style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: 600, color: "#f0f9ff" }}>
                Guest Session — Sign In to Access Workspaces
              </p>
              <p style={{ margin: 0, fontSize: "12px", color: "#93c5fd" }}>
                Workspaces are private collaborative environments. Sign in to manage investigations, invite collaborators, and access reviews.
              </p>
            </div>
            <Link
              href="/login"
              style={{
                padding: "8px 16px",
                background: "#0284c7",
                color: "#fff",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Sign In
            </Link>
          </div>
        </div>
      )}

      {/* Workspaces Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: "20px" }}>
        {workspaces.map((ws) => {
          const isActive = activeWorkspace?.id === ws.id;
          return (
            <div
              key={ws.id}
              style={{
                background: "#0d1527",
                border: `1px solid ${isActive ? "#3b82f6" : "#1e293b"}`,
                borderRadius: "10px",
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                boxShadow: isActive ? "0 0 0 1px #3b82f6" : "none",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div>
                  <h2 style={{ fontSize: "17px", fontWeight: 600, color: "#f8fafc", margin: "0 0 4px" }}>
                    <Link href={`/workspaces/${ws.id}`} style={{ color: "inherit", textDecoration: "none" }}>
                      {ws.name}
                    </Link>
                  </h2>
                  <span style={{ fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>{ws.slug}</span>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  {ws.user_role && (
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
                      {ws.user_role}
                    </span>
                  )}
                  {isActive && (
                    <span
                      style={{
                        background: "#064e3b",
                        color: "#34d399",
                        borderRadius: "4px",
                        padding: "2px 8px",
                        fontSize: "11px",
                        fontWeight: 600,
                      }}
                    >
                      ACTIVE
                    </span>
                  )}
                </div>
              </div>

              <p style={{ color: "#94a3b8", fontSize: "13px", lineHeight: 1.5, margin: "0 0 20px", flex: 1 }}>
                {ws.description || "No description provided."}
              </p>

              {/* Stats Bar */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  padding: "12px 0",
                  borderTop: "1px solid #1a263d",
                  borderBottom: "1px solid #1a263d",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>Investigators</div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>{ws.member_count}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>Investigations</div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>{ws.investigation_count}</div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                {!isActive ? (
                  <button
                    type="button"
                    onClick={() => switchWorkspace(ws.id)}
                    style={{
                      flex: 1,
                      padding: "8px",
                      background: "#1e293b",
                      color: "#cbd5e1",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Set Active
                  </button>
                ) : (
                  <div style={{ flex: 1, fontSize: "12px", color: "#38bdf8", fontWeight: 500 }}>
                    ✓ Current workspace
                  </div>
                )}
                <Link
                  href={`/workspaces/${ws.id}`}
                  style={{
                    padding: "8px 14px",
                    background: "#080d1a",
                    border: "1px solid #334155",
                    color: "#f8fafc",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 500,
                    textDecoration: "none",
                  }}
                >
                  Open Hub →
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Workspace Modal */}
      {showCreateModal && (
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
              maxWidth: "500px",
              background: "#0d1527",
              border: "1px solid #334155",
              borderRadius: "12px",
              padding: "32px",
              boxShadow: "0 25px 50px -12px rgba(0,0,0,0.6)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
                Create Research Workspace
              </h2>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                style={{ background: "transparent", border: "none", color: "#64748b", fontSize: "18px", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            {error && (
              <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "10px", borderRadius: "6px", fontSize: "12px", marginBottom: "16px" }}>
                {error}
              </div>
            )}

            <form onSubmit={handleCreate} style={{ display: "grid", gap: "16px" }}>
              <div>
                <label htmlFor="ws-name-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}>
                  Workspace Name
                </label>
                <input
                  id="ws-name-input"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Bioinformatics & Oncology Lab"
                  style={{ width: "100%", padding: "10px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label htmlFor="ws-desc-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}>
                  Description
                </label>
                <textarea
                  id="ws-desc-input"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Primary workspace for collaborative molecular dynamics investigations."
                  style={{ width: "100%", padding: "10px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", resize: "vertical", boxSizing: "border-box" }}
                />
              </div>

              <div style={{ display: "grid", gap: "12px", padding: "14px", background: "#080d1a", borderRadius: "8px", border: "1px solid #1a263d" }}>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase" }}>Governance Policies</div>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#cbd5e1", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={requireReview}
                    onChange={(e) => setRequireReview(e.target.checked)}
                  />
                  Require independent peer review before concluding investigations
                </label>
                <div>
                  <label htmlFor="ws-budget-input" style={{ display: "block", fontSize: "12px", color: "#94a3b8", marginBottom: "4px" }}>
                    Autonomous search budget limit (queries per workflow)
                  </label>
                  <input
                    id="ws-budget-input"
                    type="number"
                    min={10}
                    max={500}
                    value={maxBudget}
                    onChange={(e) => setMaxBudget(Number(e.target.value))}
                    style={{ width: "120px", padding: "6px 10px", background: "#101b2f", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "12px" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: "9px 16px", background: "#1e293b", color: "#cbd5e1", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  style={{ padding: "9px 18px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: creating ? "not-allowed" : "pointer" }}
                >
                  {creating ? "Creating..." : "Create Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
