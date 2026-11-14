"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { lookupInvitation, acceptInvitation, declineInvitation } from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

function InvitationContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const { user, refreshAuth, switchWorkspace } = useAuth();

  const [invitation, setInvitation] = useState<{
    id: string;
    workspace_id: string;
    workspace_name: string;
    email: string;
    role: string;
    status: string;
    expires_at?: string | null;
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [declined, setDeclined] = useState(false);

  useEffect(() => {
    async function fetchInvitation() {
      if (!token) {
        setLoading(false);
        setError("Missing invitation token in query parameter.");
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const data = await lookupInvitation(token);
        setInvitation(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load invitation.");
      } finally {
        setLoading(false);
      }
    }
    fetchInvitation();
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await acceptInvitation(token);
      await refreshAuth();
      switchWorkspace(res.workspace_id);
      router.push(`/workspaces/${res.workspace_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to accept invitation.");
      setSubmitting(false);
    }
  };

  const handleDecline = async () => {
    if (!token) return;
    if (!confirm("Are you sure you want to decline this workspace invitation?")) return;
    setSubmitting(true);
    setError(null);
    try {
      await declineInvitation(token);
      setDeclined(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to decline invitation.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center", color: "#94a3b8" }}>
        Validating research workspace invitation...
      </div>
    );
  }

  if (declined) {
    return (
      <div style={{ maxWidth: "520px", margin: "60px auto", padding: "32px", background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", textAlign: "center" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#f8fafc", margin: "0 0 12px" }}>
          Invitation Declined
        </h2>
        <p style={{ color: "#94a3b8", fontSize: "14px", margin: "0 0 24px" }}>
          You have declined the invitation to join this workspace.
        </p>
        <Link href="/workspaces" style={{ display: "inline-block", padding: "10px 20px", background: "#2563eb", color: "#fff", borderRadius: "6px", textDecoration: "none", fontSize: "13px", fontWeight: 600 }}>
          Go to Your Workspaces
        </Link>
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div style={{ maxWidth: "520px", margin: "60px auto", padding: "32px", background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px" }}>
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "16px", borderRadius: "8px", marginBottom: "20px" }}>
          <h2 style={{ fontSize: "16px", margin: "0 0 6px" }}>Invitation Unavailable</h2>
          <p style={{ margin: 0, fontSize: "13px" }}>{error || "This invitation is invalid or has expired."}</p>
        </div>
        <div style={{ textAlign: "center" }}>
          <Link href="/workspaces" style={{ color: "#60a5fa", textDecoration: "none", fontSize: "13px" }}>
            Return to Workspaces
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "560px", margin: "60px auto", padding: "36px", background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px" }}>
      <div style={{ textAlign: "center", marginBottom: "28px" }}>
        <span style={{ fontSize: "36px", display: "block", marginBottom: "12px" }}>🔬</span>
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#f8fafc", margin: "0 0 8px" }}>
          Workspace Research Invitation
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
          You have been invited to collaborate on scientific research intelligence.
        </p>
      </div>

      <div style={{ background: "#080e1a", border: "1px solid #1e293b", borderRadius: "8px", padding: "20px", marginBottom: "28px" }}>
        <div style={{ marginBottom: "12px" }}>
          <span style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", fontWeight: 600 }}>Workspace</span>
          <div style={{ color: "#f8fafc", fontSize: "16px", fontWeight: 600 }}>{invitation.workspace_name}</div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div>
            <span style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", fontWeight: 600 }}>Invited Email</span>
            <div style={{ color: "#cbd5e1", fontSize: "13px" }}>{invitation.email}</div>
          </div>
          <div>
            <span style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", fontWeight: 600 }}>Assigned Role</span>
            <div>
              <span style={{ background: "#1e3a5f", color: "#93c5fd", padding: "2px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 600, textTransform: "uppercase" }}>
                {invitation.role}
              </span>
            </div>
          </div>
        </div>
      </div>

      {!user ? (
        <div style={{ background: "#1e293b", padding: "16px", borderRadius: "8px", marginBottom: "24px", textAlign: "center" }}>
          <p style={{ color: "#cbd5e1", fontSize: "13px", margin: "0 0 12px" }}>
            You need to be signed in to accept this invitation.
          </p>
          <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
            <Link
              href={`/login?redirect=/invitations?token=${token}`}
              style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", borderRadius: "6px", textDecoration: "none", fontSize: "12px", fontWeight: 600 }}
            >
              Log In
            </Link>
            <Link
              href={`/register?redirect=/invitations?token=${token}`}
              style={{ padding: "8px 16px", background: "#334155", color: "#fff", borderRadius: "6px", textDecoration: "none", fontSize: "12px", fontWeight: 600 }}
            >
              Create Account
            </Link>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            type="button"
            onClick={handleAccept}
            disabled={submitting}
            style={{
              flex: 1,
              padding: "11px 20px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Joining..." : "Accept & Join Workspace"}
          </button>
          <button
            type="button"
            onClick={handleDecline}
            disabled={submitting}
            style={{
              padding: "11px 20px",
              background: "#1e293b",
              color: "#94a3b8",
              border: "1px solid #334155",
              borderRadius: "6px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            Decline
          </button>
        </div>
      )}
    </div>
  );
}

export default function InvitationPage() {
  return (
    <Suspense fallback={<div style={{ padding: "60px 20px", textAlign: "center", color: "#94a3b8" }}>Loading...</div>}>
      <InvitationContent />
    </Suspense>
  );
}
