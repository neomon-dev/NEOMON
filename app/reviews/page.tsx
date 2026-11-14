"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listReviewRequests,
  submitReviewDecision,
  withdrawReviewRequest,
  ReviewRequest,
} from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

export default function ReviewsPage() {
  const { user, activeWorkspace } = useAuth();
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("all");
  const [error, setError] = useState<string | null>(null);

  // Review Decision Modal State
  const [activeReview, setActiveReview] = useState<ReviewRequest | null>(null);
  const [decision, setDecision] = useState<string>("approved");
  const [rationale, setRationale] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const loadReviews = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      setLoading(true);
      setError(null);
      const data = await listReviewRequests({
        workspace_id: activeWorkspace.id,
        status: filterStatus === "all" ? undefined : filterStatus,
      });
      setReviews(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load peer review queue.");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace, filterStatus]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const handleOpenDecisionModal = (req: ReviewRequest) => {
    setActiveReview(req);
    setDecision("approved");
    setRationale("");
    setDecisionError(null);
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeReview) return;
    if (!rationale.trim()) {
      setDecisionError("Please provide a scientific rationale or feedback for this decision.");
      return;
    }

    setSubmittingDecision(true);
    setDecisionError(null);
    try {
      await submitReviewDecision(activeReview.id, decision, rationale);
      setActiveReview(null);
      await loadReviews();
    } catch (err: unknown) {
      setDecisionError(err instanceof Error ? err.message : "Failed to submit review decision.");
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleWithdraw = async (requestId: string) => {
    if (!confirm("Are you sure you want to withdraw this review request?")) return;
    try {
      await withdrawReviewRequest(requestId);
      await loadReviews();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to withdraw review request.");
    }
  };

  return (
    <div style={{ padding: "36px 40px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: "0 0 6px" }}>
            Peer Review & Scientific Governance Queue
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            Formal verification requests for investigations, claims, hypotheses, and evidence findings in{" "}
            <strong style={{ color: "#38bdf8" }}>{activeWorkspace?.name || "current workspace"}</strong>.
          </p>
        </div>

        <button
          type="button"
          onClick={loadReviews}
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
          {loading ? "Refreshing..." : "↻ Refresh Queue"}
        </button>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1a263d", marginBottom: "24px", paddingBottom: "8px" }}>
        {[
          { label: "All Requests", value: "all" },
          { label: "Pending Review", value: "pending" },
          { label: "Approved", value: "approved" },
          { label: "Changes Requested", value: "changes_requested" },
          { label: "Rejected", value: "rejected" },
        ].map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setFilterStatus(tab.value)}
            style={{
              padding: "6px 14px",
              background: filterStatus === tab.value ? "#2563eb" : "transparent",
              color: filterStatus === tab.value ? "#fff" : "#94a3b8",
              border: "none",
              borderRadius: "6px",
              fontSize: "13px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Reviews Queue List */}
      {loading && reviews.length === 0 ? (
        <div style={{ padding: "40px", color: "#94a3b8", textAlign: "center" }}>
          Loading review queue...
        </div>
      ) : reviews.length === 0 ? (
        <div style={{ background: "#0f172a", border: "1px dashed #1e293b", padding: "48px 24px", textAlign: "center", borderRadius: "10px" }}>
          <h3 style={{ fontSize: "15px", color: "#94a3b8", margin: "0 0 6px" }}>No Review Requests</h3>
          <p style={{ color: "#64748b", fontSize: "13px", margin: 0 }}>
            There are currently no peer review requests matching this filter in this workspace.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {reviews.map((req) => {
            const isAuthor = user?.id === req.requester_id;
            const isSelfApprovalBlocked = isAuthor && req.requires_independent_review;
            const isPending = req.status === "pending";

            const statusColors: Record<string, { bg: string; text: string }> = {
              pending: { bg: "#3b2803", text: "#fde047" },
              approved: { bg: "#064e3b", text: "#34d399" },
              rejected: { bg: "#450a0a", text: "#fca5a5" },
              changes_requested: { bg: "#312e81", text: "#a5b4fc" },
              withdrawn: { bg: "#1e293b", text: "#94a3b8" },
            };

            const colors = statusColors[req.status] || { bg: "#1e293b", text: "#94a3b8" };

            return (
              <div
                key={req.id}
                style={{
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: "10px",
                  padding: "20px 24px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                      <span
                        style={{
                          background: colors.bg,
                          color: colors.text,
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          textTransform: "uppercase",
                        }}
                      >
                        {req.status.replace("_", " ")}
                      </span>
                      <span
                        style={{
                          background: "#1e293b",
                          color: "#93c5fd",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontFamily: "monospace",
                        }}
                      >
                        {req.target_type}: {req.target_id.slice(0, 8)}...
                      </span>
                      {req.requires_independent_review && (
                        <span
                          style={{
                            background: "#2e1065",
                            color: "#c084fc",
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: 600,
                          }}
                        >
                          🛡️ Independent Review Required
                        </span>
                      )}
                    </div>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "4px 0" }}>
                      {req.title}
                    </h3>
                  </div>

                  {/* Actions */}
                  <div style={{ display: "flex", gap: "10px" }}>
                    <Link
                      href={`/investigations/${req.investigation_id}`}
                      style={{
                        padding: "6px 12px",
                        background: "#1e293b",
                        color: "#60a5fa",
                        border: "1px solid #334155",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 600,
                        textDecoration: "none",
                      }}
                    >
                      View Investigation →
                    </Link>

                    {isPending && !isAuthor && (
                      <button
                        type="button"
                        onClick={() => handleOpenDecisionModal(req)}
                        style={{
                          padding: "6px 14px",
                          background: "#2563eb",
                          color: "#fff",
                          border: "none",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Review & Decide
                      </button>
                    )}

                    {isPending && isAuthor && isSelfApprovalBlocked && (
                      <div
                        style={{
                          padding: "6px 10px",
                          background: "#1e1b4b",
                          border: "1px solid #4338ca",
                          borderRadius: "6px",
                          color: "#a5b4fc",
                          fontSize: "11px",
                        }}
                      >
                        Awaiting independent peer review
                      </div>
                    )}

                    {isPending && isAuthor && !isSelfApprovalBlocked && (
                      <button
                        type="button"
                        onClick={() => handleOpenDecisionModal(req)}
                        style={{
                          padding: "6px 14px",
                          background: "#059669",
                          color: "#fff",
                          border: "none",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Review
                      </button>
                    )}

                    {isPending && isAuthor && (
                      <button
                        type="button"
                        onClick={() => handleWithdraw(req.id)}
                        style={{
                          padding: "6px 12px",
                          background: "transparent",
                          color: "#94a3b8",
                          border: "1px solid #334155",
                          borderRadius: "6px",
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        Withdraw
                      </button>
                    )}
                  </div>
                </div>

                {req.description && (
                  <p style={{ color: "#cbd5e1", fontSize: "13px", margin: "0 0 12px" }}>
                    {req.description}
                  </p>
                )}

                <div style={{ display: "flex", gap: "20px", fontSize: "12px", color: "#64748b" }}>
                  <span>Requested by: <strong style={{ color: "#94a3b8" }}>{req.requester_name}</strong></span>
                  <span>Submitted: {req.created_at ? new Date(req.created_at).toLocaleDateString() : ""}</span>
                  <span>Decisions: {req.decisions.length}</span>
                </div>

                {/* Prior Decisions List */}
                {req.decisions.length > 0 && (
                  <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid #1e293b" }}>
                    <div style={{ fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "8px" }}>
                      Decision History:
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {req.decisions.map((d) => (
                        <div key={d.id} style={{ background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", padding: "10px 14px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <strong style={{ color: "#f8fafc", fontSize: "12px" }}>{d.reviewer_name}</strong>
                              <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: d.decision === "approved" ? "#34d399" : d.decision === "rejected" ? "#fca5a5" : "#a5b4fc" }}>
                                {d.decision.replace("_", " ")}
                              </span>
                            </div>
                            <span style={{ color: "#64748b", fontSize: "11px" }}>
                              {d.created_at ? new Date(d.created_at).toLocaleString() : ""}
                            </span>
                          </div>
                          <p style={{ margin: 0, color: "#cbd5e1", fontSize: "12px" }}>{d.rationale}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Decision Modal */}
      {activeReview && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "20px" }}>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", maxWidth: "560px", width: "100%", padding: "28px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", margin: "0 0 6px" }}>
              Submit Peer Review Decision
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 16px" }}>
              Evaluating: <strong style={{ color: "#38bdf8" }}>{activeReview.title}</strong>
            </p>

            {/* Self-approval guard alert if user is author */}
            {user?.id === activeReview.requester_id && activeReview.requires_independent_review && (
              <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "12px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
                🛡️ <strong>Self-Approval Blocked:</strong> As the author of this research request, you cannot approve your own submission under workspace independent review policies.
              </div>
            )}

            {decisionError && (
              <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
                {decisionError}
              </div>
            )}

            <form onSubmit={handleSubmitDecision}>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "13px", fontWeight: 500, marginBottom: "8px" }}>
                  Scientific Decision
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
                  {[
                    { val: "approved", label: "Approve", color: "#064e3b", text: "#34d399", disabled: user?.id === activeReview.requester_id && activeReview.requires_independent_review },
                    { val: "changes_requested", label: "Request Changes", color: "#312e81", text: "#a5b4fc", disabled: false },
                    { val: "rejected", label: "Reject", color: "#450a0a", text: "#fca5a5", disabled: false },
                  ].map((opt) => (
                    <button
                      key={opt.val}
                      type="button"
                      disabled={opt.disabled}
                      onClick={() => setDecision(opt.val)}
                      style={{
                        padding: "10px",
                        background: decision === opt.val ? opt.color : "#080e1a",
                        color: decision === opt.val ? opt.text : "#94a3b8",
                        border: `1px solid ${decision === opt.val ? opt.text : "#1e293b"}`,
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 600,
                        cursor: opt.disabled ? "not-allowed" : "pointer",
                        opacity: opt.disabled ? 0.4 : 1,
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "13px", fontWeight: 500, marginBottom: "6px" }}>
                  Scientific Rationale & Reviewer Feedback (Required)
                </label>
                <textarea
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  placeholder="Provide rigorous scientific reasoning, evidence alignment analysis, or requested revisions..."
                  rows={4}
                  required
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    background: "#080e1a",
                    border: "1px solid #1e293b",
                    borderRadius: "6px",
                    color: "#f8fafc",
                    fontSize: "13px",
                    resize: "vertical",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setActiveReview(null)}
                  style={{
                    padding: "8px 16px",
                    background: "#1e293b",
                    color: "#cbd5e1",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDecision || (decision === "approved" && user?.id === activeReview.requester_id && activeReview.requires_independent_review)}
                  style={{
                    padding: "8px 18px",
                    background: "#2563eb",
                    color: "#fff",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: submittingDecision ? "not-allowed" : "pointer",
                  }}
                >
                  {submittingDecision ? "Submitting Decision..." : "Submit Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
