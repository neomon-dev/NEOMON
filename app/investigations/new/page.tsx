"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { requestJson } from "../../../lib/api";

export default function NewInvestigationPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("quick");
  const [timeframe, setTimeframe] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = await requestJson<{ investigation: { id: string } }>("/research/investigations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, mode, timeframe: timeframe || undefined }),
      });
      router.push(`/investigations/${payload.investigation.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Research could not start.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="settings-page">
      <p className="eyebrow blue">NEW INVESTIGATION</p>
      <h1>Ask a research question</h1>
      <p className="settings-intro">NEOMON will search configured public research providers and preserve the returned source URLs.</p>
      <form className="settings-form" onSubmit={submit}>
        <label>
          Research question
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} minLength={10} maxLength={10000} required rows={6} />
        </label>
        <label>
          Research mode
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="quick">Quick research</option>
            <option value="deep">Deep research</option>
          </select>
        </label>
        <label>
          Timeframe (optional)
          <input value={timeframe} onChange={(event) => setTimeframe(event.target.value)} placeholder="e.g. since 2020" />
        </label>
        <button className="primary-button" disabled={loading} type="submit">{loading ? "Researching..." : "Start research"}</button>
        {error && <p className="connection-result error">{error}</p>}
      </form>
    </main>
  );
}
