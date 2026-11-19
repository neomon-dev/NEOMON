"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { loginUser } from "@/lib/collaboration";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { refreshAuth } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await loginUser(email, password);
      await refreshAuth();
      router.push("/");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Login failed. Please check your credentials.");
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
          <h1 style={{ fontSize: "22px", fontWeight: 800, letterSpacing: "0.08em", color: "#f8fafc", margin: "0 0 4px" }}>
            Sign in to NEOMON
          </h1>
          <p style={{ color: "#36C5DE", fontSize: "10.5px", fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", margin: "0 0 8px" }}>
            RESEARCH BEYOND THE SURFACE.
          </p>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            Autonomous research intelligence & collaborative workspaces
          </p>
        </div>

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

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
          <div>
            <label
              htmlFor="email-input"
              style={{ display: "block", fontSize: "12px", fontWeight: 500, color: "#cbd5e1", marginBottom: "6px" }}
            >
              Email address
            </label>
            <input
              id="email-input"
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

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label htmlFor="password-input" style={{ fontSize: "12px", fontWeight: 500, color: "#cbd5e1" }}>
                Password
              </label>
              <Link href="/forgot-password" style={{ fontSize: "11px", color: "#60a5fa", textDecoration: "none" }}>
                Forgot password?
              </Link>
            </div>
            <input
              id="password-input"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
              background: loading ? "#1e3a5f" : "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              marginTop: "8px",
            }}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "20px", borderTop: "1px solid #1e293b" }}>
          <span style={{ fontSize: "12px", color: "#64748b" }}>Don't have an account? </span>
          <Link href="/register" style={{ fontSize: "12px", color: "#60a5fa", textDecoration: "none", fontWeight: 500 }}>
            Register here
          </Link>
        </div>
      </div>
    </div>
  );
}
