"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { requestJson } from "../../../lib/api";
import { AtmosphericAurora } from "@/components/animated-neural-background";
import {
  BorderBeam,
  RadarScanning,
  DecryptedText,
  PulseIndicator,
  RevealSection,
} from "@/components/motion";

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
    <main className="settings-page" style={{ maxWidth: "900px", margin: "0 auto", padding: "40px 24px", position: "relative" }}>
      <AtmosphericAurora showGrid={true} showScanlines={true} />

      {/* Header Deck with Radar Sweep & Cyber Grid */}
      <RevealSection delay={0.05}>
        <div style={{ marginBottom: "28px", position: "relative", zIndex: 1, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
              <PulseIndicator status="active" />
              <DecryptedText text="MISSION INITIATOR // CONSOLE_v1" speed={25} />
              <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "monospace" }}>
                [PROTOCOL::MULTI_AGENT_RESEARCH]
              </span>
            </div>
            <h1 style={{ fontSize: "32px", fontWeight: 800, margin: "6px 0 10px", color: "#ECF5FF", letterSpacing: "-0.03em" }}>
              Launch Research Mission
            </h1>
            <p style={{ color: "#91A6C1", fontSize: "14px", lineHeight: "1.6", margin: 0, maxWidth: "600px" }}>
              Formulate an empirical inquiry. NEOMON orchestrates distributed research agents across preprint servers, academic repositories, and digital libraries to decompose claims, extract verbatim passages, and adjudicate contradictions.
            </p>
          </div>
          <div className="desktop-only" style={{ opacity: 0.85, flexShrink: 0 }}>
            <RadarScanning size={100} color="#25D9F2" />
          </div>
        </div>
      </RevealSection>

      {/* Suggested Questions Matrix */}
      <div style={{ marginBottom: "24px", position: "relative", zIndex: 1 }}>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: "10px" }}>
          Suggested Research Questions // Benchmark Corpus
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => applySuggestion(s)}
              className="hud-card"
              style={{
                padding: "8px 14px",
                color: "#e2e8f0",
                fontSize: "12px",
                fontWeight: 500,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ color: "#38bdf8" }}>✦</span>
              <span>{s.label}</span>
              <span style={{ fontSize: "10px", fontFamily: "monospace", color: s.mode === "deep" ? "#c084fc" : "#38bdf8" }}>
                [{s.mode.toUpperCase()}]
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Launch Console Form */}
      <form
        className="hud-card"
        onSubmit={submit}
        style={{
          padding: "32px",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div className="hud-corner-tl" />
        <div className="hud-corner-tr" />
        <div className="hud-corner-bl" />
        <div className="hud-corner-br" />

        {/* Step 1: Research Inquiry */}
        <div style={{ marginBottom: "26px" }}>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px", fontWeight: 700, fontSize: "13px", color: "#f8fafc" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>01 //</span>
              <span>Research Inquiry <span style={{ color: "#f43f5e" }}>*</span></span>
            </span>
            <span style={{ fontSize: "11px", fontFamily: "monospace", color: question.length > 9000 ? "#f87171" : "var(--muted)" }}>
              {question.length} / 10,000 CHARACTERS
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
            placeholder="Formulate an explicit, verifiable technological or scientific research inquiry (e.g., benchmark comparison, architecture evaluation, empirical mechanism)..."
            minLength={10}
            maxLength={10000}
            required
            rows={5}
            style={{
              width: "100%",
              background: "rgba(6, 10, 20, 0.8)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              borderRadius: "8px",
              padding: "14px 16px",
              color: "#f8fafc",
              fontSize: "14px",
              lineHeight: "1.6",
              resize: "vertical",
              outline: "none",
              boxShadow: "inset 0 2px 4px rgba(0,0,0,0.5)",
              fontFamily: "inherit",
            }}
          />
        </div>

        {/* Step 2: Protocol Selection */}
        <div style={{ marginBottom: "26px" }}>
          <label style={{ display: "block", marginBottom: "10px", fontWeight: 700, fontSize: "13px", color: "#f8fafc" }}>
            <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>02 //</span> Multi-Agent Research Protocol
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
            <button
              type="button"
              onClick={() => setMode("quick")}
              className="hud-card"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "18px",
                position: "relative",
                overflow: "hidden",
                background: mode === "quick" ? "linear-gradient(180deg, rgba(37, 217, 242, 0.14) 0%, rgba(8, 13, 26, 0.95) 100%)" : undefined,
                borderColor: mode === "quick" ? "#25D9F2" : undefined,
                boxShadow: mode === "quick" ? "0 0 20px rgba(37, 217, 242, 0.25)" : undefined,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {mode === "quick" && <BorderBeam size={160} duration={8} colorFrom="#25D9F2" colorTo="#2787FF" />}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px" }}>⚡</span>
                  <strong style={{ color: mode === "quick" ? "#25D9F2" : "#f1f5f9", fontSize: "14px", fontWeight: 700 }}>
                    Quick Dialectic Sweep
                  </strong>
                </div>
                {mode === "quick" && <span style={{ color: "#25D9F2", fontSize: "12px", fontWeight: 700 }}>● ACTIVE</span>}
              </div>
              <span style={{ fontSize: "12px", color: "#94a3b8", lineHeight: "1.5" }}>
                Targeted academic query generation, rapid source retrieval, high-relevance claim extraction, and instant synthesis.
              </span>
            </button>

            <button
              type="button"
              onClick={() => setMode("deep")}
              className="hud-card"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                padding: "18px",
                position: "relative",
                overflow: "hidden",
                background: mode === "deep" ? "linear-gradient(180deg, rgba(133, 100, 255, 0.16) 0%, rgba(8, 13, 26, 0.95) 100%)" : undefined,
                borderColor: mode === "deep" ? "#8564FF" : undefined,
                boxShadow: mode === "deep" ? "0 0 20px rgba(133, 100, 255, 0.25)" : undefined,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              {mode === "deep" && <BorderBeam size={160} duration={8} colorFrom="#8564FF" colorTo="#25D9F2" />}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px" }}>🔬</span>
                  <strong style={{ color: mode === "deep" ? "#8564FF" : "#f1f5f9", fontSize: "14px", fontWeight: 700 }}>
                    Deep Multi-Agent Synthesis
                  </strong>
                </div>
                {mode === "deep" && <span style={{ color: "#8564FF", fontSize: "12px", fontWeight: 700 }}>● ACTIVE</span>}
              </div>
              <span style={{ fontSize: "12px", color: "#94a3b8", lineHeight: "1.5" }}>
                Multi-round adversarial debate, full knowledge graph construction, study independence clustering, and calibrated evidence scoring.
              </span>
            </button>
          </div>
        </div>

        {/* Step 3: Temporal Scope */}
        <div style={{ marginBottom: "28px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: 700, fontSize: "13px", color: "#f8fafc" }}>
            <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>03 //</span> Temporal Boundary Filter (Optional)
          </label>
          <input
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            placeholder="e.g. 2021 to 2024, or since 2023"
            style={{
              width: "100%",
              background: "rgba(6, 10, 20, 0.8)",
              border: "1px solid rgba(56, 189, 248, 0.2)",
              borderRadius: "8px",
              padding: "11px 14px",
              color: "#f8fafc",
              fontSize: "13px",
              outline: "none",
            }}
          />
        </div>

        {/* Action Bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "14px", borderTop: "1px solid var(--border)", flexWrap: "wrap", gap: "12px" }}>
          <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "monospace" }}>
            PRESS <kbd style={{ background: "rgba(255,255,255,0.08)", padding: "2px 7px", borderRadius: "4px", color: "#e2e8f0" }}>CTRL + ENTER</kbd> TO LAUNCH MISSION
          </span>
          <button
            className="cyber-primary-btn"
            disabled={loading}
            type="submit"
            style={{
              cursor: loading ? "wait" : "pointer",
              position: "relative",
              overflow: "hidden",
              boxShadow: "0 0 25px rgba(37, 217, 242, 0.4)",
            }}
          >
            {loading ? (
              <>
                <span style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>◌</span>
                <span>INITIALIZING ORCHESTRATION...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>LAUNCH RESEARCH MISSION</span>
                <span style={{ marginLeft: "4px" }}>→</span>
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

