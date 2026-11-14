"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listThreads,
  createThread,
  addComment,
  resolveThread,
  reopenThread,
  listAnnotations,
  createAnnotation,
  listReviewRequests,
  createReviewRequest,
  submitReviewDecision,
  CommentThread,
  EvidenceAnnotation,
  ReviewRequest,
} from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

interface CollaborationPanelProps {
  investigationId: string;
}

export function CollaborationPanel({ investigationId }: CollaborationPanelProps) {
  const { user, activeWorkspace } = useAuth();
  const [activeTab, setActiveTab] = useState<"discussions" | "annotations" | "reviews">("discussions");

  // Discussions state
  const [threads, setThreads] = useState<CommentThread[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [newThreadTitle, setNewThreadTitle] = useState("");
  const [newThreadContent, setNewThreadContent] = useState("");
  const [showNewThreadModal, setShowNewThreadModal] = useState(false);
  const [submittingThread, setSubmittingThread] = useState(false);
  const [replyContent, setReplyContent] = useState<Record<string, string>>({});
  const [submittingReply, setSubmittingReply] = useState<Record<string, boolean>>({});

  // Annotations state
  const [annotations, setAnnotations] = useState<EvidenceAnnotation[]>([]);
  const [loadingAnnotations, setLoadingAnnotations] = useState(false);

  // Reviews state
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [showNewReviewModal, setShowNewReviewModal] = useState(false);
  const [reviewTitle, setReviewTitle] = useState("Formal Scientific Investigation Review");
  const [reviewDescription, setReviewDescription] = useState("");
  const [requiresIndependentReview, setRequiresIndependentReview] = useState(true);
  const [submittingReview, setSubmittingReview] = useState(false);

  // Decision state for review
  const [decisionModalReview, setDecisionModalReview] = useState<ReviewRequest | null>(null);
  const [decisionChoice, setDecisionChoice] = useState("approved");
  const [decisionRationale, setDecisionRationale] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const effectiveWorkspaceId = activeWorkspace?.id || "00000000000000000000000000000002";

  const loadThreads = useCallback(async () => {
    try {
      setLoadingThreads(true);
      const data = await listThreads({
        workspace_id: effectiveWorkspaceId,
        investigation_id: investigationId,
      });
      setThreads(data);
    } catch (err: unknown) {
      console.error("Failed to load threads", err);
    } finally {
      setLoadingThreads(false);
    }
  }, [effectiveWorkspaceId, investigationId]);

  const loadAnnotations = useCallback(async () => {
    try {
      setLoadingAnnotations(true);
      const data = await listAnnotations({
        workspace_id: effectiveWorkspaceId,
        investigation_id: investigationId,
      });
      setAnnotations(data);
    } catch (err: unknown) {
      console.error("Failed to load annotations", err);
    } finally {
      setLoadingAnnotations(false);
    }
  }, [effectiveWorkspaceId, investigationId]);

  const loadReviews = useCallback(async () => {
    try {
      setLoadingReviews(true);
      const data = await listReviewRequests({
        workspace_id: effectiveWorkspaceId,
        investigation_id: investigationId,
      });
      setReviews(data);
    } catch (err: unknown) {
      console.error("Failed to load reviews", err);
    } finally {
      setLoadingReviews(false);
    }
  }, [effectiveWorkspaceId, investigationId]);

  useEffect(() => {
    if (activeTab === "discussions") loadThreads();
    if (activeTab === "annotations") loadAnnotations();
    if (activeTab === "reviews") loadReviews();
  }, [activeTab, loadThreads, loadAnnotations, loadReviews]);

  // Handle Thread Submission
  const handleCreateThread = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newThreadContent.trim()) return;
    setSubmittingThread(true);
    setError(null);
    try {
      await createThread({
        workspace_id: effectiveWorkspaceId,
        investigation_id: investigationId,
        target_entity_type: "investigation",
        target_entity_id: investigationId,
        title: newThreadTitle.trim() || undefined,
        content: newThreadContent.trim(),
      });
      setNewThreadTitle("");
      setNewThreadContent("");
      setShowNewThreadModal(false);
      await loadThreads();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create discussion thread.");
    } finally {
      setSubmittingThread(false);
    }
  };

  // Handle Reply to Thread
  const handleAddReply = async (threadId: string) => {
    const content = replyContent[threadId]?.trim();
    if (!content) return;
    setSubmittingReply((prev) => ({ ...prev, [threadId]: true }));
    try {
      await addComment(threadId, content);
      setReplyContent((prev) => ({ ...prev, [threadId]: "" }));
      await loadThreads();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to post comment.");
    } finally {
      setSubmittingReply((prev) => ({ ...prev, [threadId]: false }));
    }
  };

  const handleToggleResolve = async (thread: CommentThread) => {
    try {
      if (thread.status === "resolved") {
        await reopenThread(thread.id);
      } else {
        await resolveThread(thread.id);
      }
      await loadThreads();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update thread status.");
    }
  };

  // Handle Review Request Submission
  const handleCreateReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingReview(true);
    setError(null);
    try {
      await createReviewRequest({
        workspace_id: effectiveWorkspaceId,
        investigation_id: investigationId,
        target_type: "investigation",
        target_id: investigationId,
        title: reviewTitle,
        description: reviewDescription,
        requires_independent_review: requiresIndependentReview,
      });
      setShowNewReviewModal(false);
      await loadReviews();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create review request.");
    } finally {
      setSubmittingReview(false);
    }
  };

  // Handle Review Decision
  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decisionModalReview) return;
    setSubmittingDecision(true);
    setError(null);
    try {
      await submitReviewDecision(decisionModalReview.id, decisionChoice, decisionRationale);
      setDecisionModalReview(null);
      setDecisionRationale("");
      await loadReviews();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit review decision.");
    } finally {
      setSubmittingDecision(false);
    }
  };

  return (
    <section
      style={{
        background: "#080e1a",
        border: "1px solid #1e293b",
        borderRadius: "10px",
        padding: "24px",
        marginTop: "32px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <span style={{ fontSize: "11px", textTransform: "uppercase", fontWeight: 700, color: "#38bdf8", letterSpacing: "0.05em" }}>
            COLLABORATION & GOVERNANCE
          </span>
          <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", margin: "2px 0 0" }}>
            Scientific Peer Review & Collaborative Dialogue
          </h2>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          {activeTab === "discussions" && (
            <button
              type="button"
              onClick={() => setShowNewThreadModal(true)}
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
              + New Discussion Thread
            </button>
          )}

          {activeTab === "reviews" && (
            <button
              type="button"
              onClick={() => setShowNewReviewModal(true)}
              style={{
                padding: "6px 14px",
                background: "#7c3aed",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              🛡️ Request Peer Review
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1e293b", marginBottom: "20px", paddingBottom: "6px" }}>
        <button
          type="button"
          onClick={() => setActiveTab("discussions")}
          style={{
            padding: "6px 14px",
            background: activeTab === "discussions" ? "#1e293b" : "transparent",
            color: activeTab === "discussions" ? "#38bdf8" : "#94a3b8",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Discussions ({threads.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("annotations")}
          style={{
            padding: "6px 14px",
            background: activeTab === "annotations" ? "#1e293b" : "transparent",
            color: activeTab === "annotations" ? "#38bdf8" : "#94a3b8",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Evidence Annotations ({annotations.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("reviews")}
          style={{
            padding: "6px 14px",
            background: activeTab === "reviews" ? "#1e293b" : "transparent",
            color: activeTab === "reviews" ? "#38bdf8" : "#94a3b8",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Peer Reviews ({reviews.length})
        </button>
      </div>

      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
          {error}
        </div>
      )}

      {/* TAB 1: DISCUSSIONS */}
      {activeTab === "discussions" && (
        <div>
          {loadingThreads && threads.length === 0 ? (
            <div style={{ padding: "30px", color: "#94a3b8", textAlign: "center" }}>Loading discussion threads...</div>
          ) : threads.length === 0 ? (
            <div style={{ background: "#0b1220", border: "1px dashed #1e293b", padding: "32px", textAlign: "center", borderRadius: "8px" }}>
              <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 10px" }}>
                No discussion threads created yet. Start a discussion to collaborate with other researchers on this investigation.
              </p>
              <button
                type="button"
                onClick={() => setShowNewThreadModal(true)}
                style={{ padding: "6px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
              >
                Start First Thread
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {threads.map((t) => (
                <div
                  key={t.id}
                  style={{
                    background: "#0b1220",
                    border: `1px solid ${t.status === "resolved" ? "#1e293b" : "#1e3a5f"}`,
                    borderRadius: "8px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc" }}>
                          {t.title || `Thread #${t.id.slice(0, 6)}`}
                        </span>
                        <span
                          style={{
                            background: t.status === "resolved" ? "#064e3b" : "#1e3a5f",
                            color: t.status === "resolved" ? "#34d399" : "#93c5fd",
                            padding: "1px 6px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            textTransform: "uppercase",
                            fontWeight: 600,
                          }}
                        >
                          {t.status}
                        </span>
                      </div>
                      <span style={{ color: "#64748b", fontSize: "11px" }}>
                        Opened by {t.creator_name} · {t.created_at ? new Date(t.created_at).toLocaleDateString() : ""}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleToggleResolve(t)}
                      style={{
                        padding: "4px 10px",
                        background: "#1e293b",
                        color: t.status === "resolved" ? "#93c5fd" : "#34d399",
                        border: "1px solid #334155",
                        borderRadius: "4px",
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      {t.status === "resolved" ? "Reopen Thread" : "✓ Mark Resolved"}
                    </button>
                  </div>

                  {/* Comments */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
                    {t.comments.map((c) => (
                      <div key={c.id} style={{ background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", padding: "10px 12px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                          <strong style={{ color: "#e2e8f0", fontSize: "12px" }}>{c.author_name}</strong>
                          <span style={{ color: "#64748b", fontSize: "11px" }}>
                            {c.created_at ? new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                          </span>
                        </div>
                        <p style={{ margin: 0, color: "#cbd5e1", fontSize: "13px", whiteSpace: "pre-wrap" }}>
                          {c.content}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Reply Input */}
                  {t.status !== "resolved" && (
                    <div style={{ display: "flex", gap: "8px" }}>
                      <input
                        type="text"
                        placeholder="Reply to thread... (use @username to mention)"
                        value={replyContent[t.id] || ""}
                        onChange={(e) => setReplyContent((prev) => ({ ...prev, [t.id]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            handleAddReply(t.id);
                          }
                        }}
                        style={{
                          flex: 1,
                          padding: "7px 12px",
                          background: "#080e1a",
                          border: "1px solid #1e293b",
                          borderRadius: "6px",
                          color: "#f8fafc",
                          fontSize: "12px",
                        }}
                      />
                      <button
                        type="button"
                        disabled={submittingReply[t.id] || !replyContent[t.id]?.trim()}
                        onClick={() => handleAddReply(t.id)}
                        style={{
                          padding: "7px 14px",
                          background: "#2563eb",
                          color: "#fff",
                          border: "none",
                          borderRadius: "6px",
                          fontSize: "12px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Reply
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EVIDENCE ANNOTATIONS */}
      {activeTab === "annotations" && (
        <div>
          {loadingAnnotations && annotations.length === 0 ? (
            <div style={{ padding: "30px", color: "#94a3b8", textAlign: "center" }}>Loading annotations...</div>
          ) : annotations.length === 0 ? (
            <div style={{ background: "#0b1220", border: "1px dashed #1e293b", padding: "32px", textAlign: "center", borderRadius: "8px" }}>
              <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 10px" }}>
                No peer annotations added to evidence in this investigation yet. Annotate passages in the Evidence Explorer.
              </p>
              <Link
                href={`/evidence?investigation_id=${investigationId}`}
                style={{ padding: "6px 14px", background: "#2563eb", color: "#fff", borderRadius: "6px", fontSize: "12px", textDecoration: "none", display: "inline-block" }}
              >
                Go to Evidence Explorer →
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {annotations.map((ann) => {
                const badgeColor =
                  ann.annotation_type === "methodological_concern" || ann.annotation_type === "credibility_concern"
                    ? "#ef4444"
                    : ann.annotation_type === "supporting"
                    ? "#10b981"
                    : "#f59e0b";

                return (
                  <div key={ann.id} style={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: "8px", padding: "14px 16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            background: "#1e293b",
                            color: badgeColor,
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: 700,
                            textTransform: "uppercase",
                          }}
                        >
                          {ann.annotation_type.replace("_", " ")}
                        </span>
                        <span style={{ color: "#64748b", fontSize: "12px" }}>
                          Annotated by <strong style={{ color: "#94a3b8" }}>{ann.author_name}</strong>
                        </span>
                      </div>
                      <Link
                        href={`/evidence?investigation_id=${investigationId}&evidence_id=${ann.evidence_id}`}
                        style={{ color: "#38bdf8", fontSize: "11px", textDecoration: "none" }}
                      >
                        Inspect Evidence Passage →
                      </Link>
                    </div>
                    <p style={{ margin: "0 0 6px", color: "#f8fafc", fontSize: "13px" }}>{ann.comment}</p>
                    {ann.reviewer_rationale && (
                      <div style={{ color: "#94a3b8", fontSize: "12px", background: "#080e1a", padding: "6px 10px", borderRadius: "4px" }}>
                        Rationale: {ann.reviewer_rationale}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PEER REVIEWS */}
      {activeTab === "reviews" && (
        <div>
          {loadingReviews && reviews.length === 0 ? (
            <div style={{ padding: "30px", color: "#94a3b8", textAlign: "center" }}>Loading peer reviews...</div>
          ) : reviews.length === 0 ? (
            <div style={{ background: "#0b1220", border: "1px dashed #1e293b", padding: "32px", textAlign: "center", borderRadius: "8px" }}>
              <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 10px" }}>
                No formal peer review requests submitted for this investigation.
              </p>
              <button
                type="button"
                onClick={() => setShowNewReviewModal(true)}
                style={{ padding: "6px 14px", background: "#7c3aed", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
              >
                Submit for Peer Review
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {reviews.map((rev) => {
                const isAuthor = user?.id === rev.requester_id;
                const isSelfApprovalBlocked = isAuthor && rev.requires_independent_review;

                return (
                  <div key={rev.id} style={{ background: "#0b1220", border: "1px solid #1e293b", borderRadius: "8px", padding: "16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span
                            style={{
                              background: rev.status === "approved" ? "#064e3b" : rev.status === "pending" ? "#3b2803" : "#450a0a",
                              color: rev.status === "approved" ? "#34d399" : rev.status === "pending" ? "#fde047" : "#fca5a5",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              fontSize: "11px",
                              fontWeight: 700,
                              textTransform: "uppercase",
                            }}
                          >
                            {rev.status.replace("_", " ")}
                          </span>
                          <strong style={{ color: "#f8fafc", fontSize: "14px" }}>{rev.title}</strong>
                        </div>
                        <div style={{ color: "#64748b", fontSize: "12px" }}>
                          Requested by {rev.requester_name} · {rev.created_at ? new Date(rev.created_at).toLocaleDateString() : ""}
                        </div>
                      </div>

                      {rev.status === "pending" && (
                        <div>
                          {isSelfApprovalBlocked ? (
                            <span style={{ fontSize: "11px", color: "#a5b4fc", background: "#1e1b4b", padding: "4px 8px", borderRadius: "4px" }}>
                              🛡️ Awaiting independent reviewer
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionModalReview(rev);
                                setDecisionChoice("approved");
                                setDecisionRationale("");
                              }}
                              style={{ padding: "5px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                            >
                              Review & Decide
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    {rev.description && <p style={{ margin: "6px 0 10px", color: "#cbd5e1", fontSize: "13px" }}>{rev.description}</p>}

                    {/* Decisions history */}
                    {rev.decisions.length > 0 && (
                      <div style={{ marginTop: "10px", borderTop: "1px solid #1e293b", paddingTop: "8px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b" }}>Decisions:</span>
                        {rev.decisions.map((d) => (
                          <div key={d.id} style={{ marginTop: "4px", fontSize: "12px", color: "#94a3b8" }}>
                            <strong style={{ color: d.decision === "approved" ? "#34d399" : "#fca5a5" }}>
                              {d.decision.toUpperCase()}:
                            </strong>{" "}
                            {d.rationale} <span style={{ color: "#475569" }}>— {d.reviewer_name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modal: New Discussion Thread */}
      {showNewThreadModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "20px" }}>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", maxWidth: "500px", width: "100%", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc", margin: "0 0 14px" }}>
              Start Investigation Discussion
            </h3>
            <form onSubmit={handleCreateThread}>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "4px" }}>Topic Title (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Methodology inquiry on source sample..."
                  value={newThreadTitle}
                  onChange={(e) => setNewThreadTitle(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px" }}
                />
              </div>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "4px" }}>Initial Comment / Note *</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Share scientific observations or mention colleagues with @username..."
                  value={newThreadContent}
                  onChange={(e) => setNewThreadContent(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px", resize: "vertical" }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowNewThreadModal(false)}
                  style={{ padding: "6px 14px", background: "#1e293b", color: "#cbd5e1", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingThread}
                  style={{ padding: "6px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                >
                  {submittingThread ? "Creating..." : "Create Thread"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: New Review Request */}
      {showNewReviewModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "20px" }}>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", maxWidth: "520px", width: "100%", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc", margin: "0 0 14px" }}>
              Request Independent Peer Review
            </h3>
            <form onSubmit={handleCreateReview}>
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "4px" }}>Review Title</label>
                <input
                  type="text"
                  required
                  value={reviewTitle}
                  onChange={(e) => setReviewTitle(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px" }}
                />
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "4px" }}>Review Context / Brief</label>
                <textarea
                  rows={3}
                  placeholder="Outline key hypotheses, evidence gaps, or points requiring scientific verification..."
                  value={reviewDescription}
                  onChange={(e) => setReviewDescription(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px", resize: "vertical" }}
                />
              </div>
              <div style={{ marginBottom: "18px" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={requiresIndependentReview}
                    onChange={(e) => setRequiresIndependentReview(e.target.checked)}
                  />
                  <span style={{ color: "#cbd5e1", fontSize: "12px" }}>
                    Enforce Independent Review (Anti-Self-Approval Guard)
                  </span>
                </label>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowNewReviewModal(false)}
                  style={{ padding: "6px 14px", background: "#1e293b", color: "#cbd5e1", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReview}
                  style={{ padding: "6px 16px", background: "#7c3aed", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                >
                  {submittingReview ? "Submitting..." : "Submit Review Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Review Decision */}
      {decisionModalReview && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "20px" }}>
          <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", maxWidth: "500px", width: "100%", padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc", margin: "0 0 10px" }}>
              Submit Peer Review Decision
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "12px", margin: "0 0 14px" }}>
              {decisionModalReview.title}
            </p>
            <form onSubmit={handleSubmitDecision}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "6px" }}>Decision</label>
                <select
                  value={decisionChoice}
                  onChange={(e) => setDecisionChoice(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px" }}
                >
                  <option value="approved">Approve Investigation</option>
                  <option value="changes_requested">Request Changes</option>
                  <option value="rejected">Reject Findings</option>
                </select>
              </div>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", color: "#cbd5e1", fontSize: "12px", marginBottom: "4px" }}>Rationale & Feedback *</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Provide scientific reasoning for this decision..."
                  value={decisionRationale}
                  onChange={(e) => setDecisionRationale(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", background: "#080e1a", border: "1px solid #1e293b", borderRadius: "6px", color: "#f8fafc", fontSize: "13px", resize: "vertical" }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => setDecisionModalReview(null)}
                  style={{ padding: "6px 14px", background: "#1e293b", color: "#cbd5e1", border: "none", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDecision}
                  style={{ padding: "6px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                >
                  {submittingDecision ? "Saving..." : "Submit Decision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
