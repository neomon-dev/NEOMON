"use client";

import React, { useState } from "react";
import Link from "next/link";
import { requestPasswordReset, confirmPasswordReset } from "@/lib/collaboration";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      const res = await requestPasswordReset(email);
      setMessage("Password reset token generated. In development mode, the token is provided below:");
      if (res.reset_token) {
        setResetToken(res.reset_token);
        setStep("confirm");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to generate password reset request.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      await confirmPasswordReset(resetToken, newPassword);
      setMessage("Your password has been successfully reset. You may now sign in.");
      setStep("request");
      setResetToken("");
      setNewPassword("");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to reset password. Please check token.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "80vh", display: "grid", placeItems: "center", padding: "40px 20px" }}>
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          background: "#0d1527",
          border: "1px solid #1e293b",
          borderRadius: "12px",
          padding: "36px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.4)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              margin: "0 auto 14px",
              filter: "drop-shadow(0 0 20px rgba(54, 197, 222, 0.4))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/neomon-symbol.png"
              alt="NEOMON"
              width={56}
              height={56}
              style={{ objectFit: "contain" }}
            />
          </div>
          <h1 style={{ fontSize: "20px", fontWeight: 800, letterSpacing: "0.08em", color: "#f8fafc", margin: "0 0 4px" }}>
            Reset Password
          </h1>
          <p style={{ color: "#36C5DE", fontSize: "10.5px", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", margin: "0 0 8px" }}>
            RESEARCH BEYOND THE SURFACE.
          </p>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            {step === "request"
              ? "Enter your account email to receive a password reset token."
              : "Enter your reset token and your new password."}
          </p>
        </div>

        {message && (
          <div
            style={{
              background: "#064e3b",
              border: "1px solid #059669",
              color: "#a7f3d0",
              padding: "10px 14px",
              borderRadius: "6px",
              fontSize: "13px",
              marginBottom: "20px",
            }}
          >
            {message}
          </div>
        )}

        {error && (
          <div
            style={{
              background: "#450a0a",
              border: "1px solid #991b1b",
              color: "#fca5a5",
              padding: "10px 14px",
              borderRadius: "6px",
              fontSize: "13px",
              marginBottom: "20px",
            }}
          >
            {error}
          </div>
        )}

        {step === "request" ? (
          <form onSubmit={handleRequest} style={{ display: "grid", gap: "16px" }}>
            <div>
              <label htmlFor="req-email-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}>
                Registered email address
              </label>
              <input
                id="req-email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="researcher@organization.org"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "#080d1a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                  fontSize: "13px",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                padding: "11px",
                background: loading ? "#1e3a5f" : "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Requesting..." : "Send Reset Token"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleConfirm} style={{ display: "grid", gap: "16px" }}>
            <div>
              <label htmlFor="token-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}>
                Reset Token
              </label>
              <input
                id="token-input"
                type="text"
                required
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "#080d1a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div>
              <label htmlFor="new-pass-input" style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}>
                New Password (min 8 chars)
              </label>
              <input
                id="new-pass-input"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "#080d1a",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  color: "#f8fafc",
                  fontSize: "13px",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                padding: "11px",
                background: loading ? "#1e3a5f" : "#059669",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Resetting..." : "Confirm New Password"}
            </button>
          </form>
        )}

        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "20px", borderTop: "1px solid #1e293b" }}>
          <Link href="/login" style={{ fontSize: "12px", color: "#60a5fa", textDecoration: "none" }}>
            ← Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
