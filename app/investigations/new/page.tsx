"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { requestJson } from "../../../lib/api";

const SUGGESTIONS = [
  {
    label: "NVIDIA H100 SXM5 Benchmarks",
    text: "What are the verified power consumption, FP8 throughput, and architecture specifications for the NVIDIA H100 SXM5 GPU?",
    mode: "deep",
    timeframe: "since 2022",
  },
  {
    label: "Nokia Mobile Platform Shift",
    text: "What were the core organizational, architectural, and competitive factors that led to the decline of Nokia Symbian and MeeGo?",
    mode: "deep",
    timeframe: "2007 to 2014",
  },
  {
    label: "Quantum Error Correction (Surface Codes)",
    text: "What is the current experimental state of surface codes and threshold error rates in superconducting quantum processors?",
    mode: "quick",
    timeframe: "since 2023",
  },
];

export default function NewInvestigationPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"quick" | "deep">("quick");
  const [timeframe, setTimeframe] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || question.trim().length < 10) {
      setError("Please enter a research question with at least 10 characters.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const activeWsId = typeof window !== "undefined" ? localStorage.getItem("neomon_active_workspace_id") : null;
      const payload = await requestJson<{ investigation: { id: string } }>("/research/investigations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          mode,
          timeframe: timeframe.trim() || undefined,
          workspace_id: activeWsId || undefined,
        }),
      });
      router.push(`/investigations/${payload.investigation.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Research could not start.");
    } finally {
      setLoading(false);
    }
  }

  function applySuggestion(s: (typeof SUGGESTIONS)[0]) {
    setQuestion(s.text);
    setMode(s.mode as "quick" | "deep");
    setTimeframe(s.timeframe);
    setError("");
  }

  return (
    <main className="settings-page" style={{ maxWidth: "860px", margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: "28px" }}>
        <p className="eyebrow blue" style={{ letterSpacing: "0.08em", fontWeight: 700 }}>
          AUTONOMOUS INVESTIGATION INITIATOR
        </p>
        <h1 style={{ fontSize: "28px", fontWeight: 700, margin: "6px 0 10px", color: "#f8fafc" }}>
          Launch Research Investigation
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "14px", lineHeight: "1.6", margin: 0 }}>
          NEOMON orchestrates multi-agent research across academic repositories, preprint servers, and peer-reviewed journals,
          extracting traceable evidence passages and adjudicating claims through adversarial debate.
        </p>
      </div>

      {/* Suggested Questions */}
      <div style={{ marginBottom: "24px" }}>
        <span style={{ fontSize: "11px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "8px" }}>
          Suggested Research Questions
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => applySuggestion(s)}
              style={{
                background: "#0e1526",
                border: "1px solid #1e293b",
                borderRadius: "6px",
                padding: "6px 12px",
                color: "#93c5fd",
                fontSize: "12px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#3b82f6")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1e293b")}
            >
              ✦ {s.label}
            </button>
          ))}
        </div>
      </div>

      <form
        className="settings-form"
        onSubmit={submit}
        style={{
          background: "#0b101d",
          border: "1px solid #1e293b",
          borderRadius: "12px",
          padding: "28px",
          boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
        }}
      >
        {/* Research Question */}
        <div style={{ marginBottom: "20px" }}>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px", fontWeight: 600, fontSize: "13px", color: "#e2e8f0" }}>
            <span>Research Question <span style={{ color: "#ef4444" }}>*</span></span>
            <span style={{ fontSize: "11px", color: question.length > 9000 ? "#f87171" : "#64748b" }}>
              {question.length}/10000 characters
            </span>
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                const form = e.currentTarget.form;
                if (form) form.requestSubmit();
              }
            }}
            placeholder="Formulate an explicit, testable scientific or technological inquiry..."
            minLength={10}
            maxLength={10000}
            required
            rows={5}
            style={{
              width: "100%",
              background: "#080c15",
              border: "1px solid #233554",
              borderRadius: "8px",
              padding: "12px 14px",
              color: "#f8fafc",
              fontSize: "14px",
              lineHeight: "1.6",
              resize: "vertical",
              outline: "none",
            }}
          />
        </div>

        {/* Mode Selector */}
        <div style={{ marginBottom: "20px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: 600, fontSize: "13px", color: "#e2e8f0" }}>
            Investigation Mode
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <button
              type="button"
              onClick={() => setMode("quick")}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "14px",
                background: mode === "quick" ? "rgba(59, 130, 246, 0.12)" : "#080c15",
                border: mode === "quick" ? "1px solid #3b82f6" : "1px solid #1e293b",
                borderRadius: "8px",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ fontSize: "16px" }}>⚡</span>
                <strong style={{ color: mode === "quick" ? "#60a5fa" : "#f1f5f9", fontSize: "13px" }}>
                  Quick Research
                </strong>
              </div>
              <span style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.4" }}>
                Fast scan, primary source ingestion, targeted claim extraction, and instant synthesis.
              </span>
            </button>

            <button
              type="button"
              onClick={() => setMode("deep")}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "14px",
                background: mode === "deep" ? "rgba(139, 92, 246, 0.12)" : "#080c15",
                border: mode === "deep" ? "1px solid #8b5cf6" : "1px solid #1e293b",
                borderRadius: "8px",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ fontSize: "16px" }}>🔬</span>
                <strong style={{ color: mode === "deep" ? "#c084fc" : "#f1f5f9", fontSize: "13px" }}>
                  Deep Multi-Agent Debate
                </strong>
              </div>
              <span style={{ fontSize: "11px", color: "#94a3b8", lineHeight: "1.4" }}>
                Adversarial debate rounds, full knowledge graph construction, study independence clustering, and formal adjudication.
              </span>
            </button>
          </div>
        </div>

        {/* Timeframe */}
        <div style={{ marginBottom: "24px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: 600, fontSize: "13px", color: "#e2e8f0" }}>
            Temporal Boundary (Optional)
          </label>
          <input
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            placeholder="e.g. 2021 to 2024, or since 2023"
            style={{
              width: "100%",
              background: "#080c15",
              border: "1px solid #233554",
              borderRadius: "8px",
              padding: "10px 14px",
              color: "#f8fafc",
              fontSize: "13px",
              outline: "none",
            }}
          />
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "8px", borderTop: "1px solid #1e293b" }}>
          <span style={{ fontSize: "11px", color: "#64748b" }}>
            Press <kbd style={{ background: "#1e293b", padding: "2px 6px", borderRadius: "4px", color: "#cbd5e1" }}>Ctrl + Enter</kbd> to launch
          </span>
          <button
            className="primary-button"
            disabled={loading}
            type="submit"
            style={{
              padding: "10px 24px",
              fontSize: "13px",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? (
              <>
                <span style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>◌</span>
                Initializing Research...
              </>
            ) : (
              <>
                <span>▶</span> Launch Investigation
              </>
            )}
          </button>
        </div>

        {error && (
          <p className="connection-result error" style={{ marginTop: "16px" }}>
            {error}
          </p>
        )}
      </form>
    </main>
  );
}
