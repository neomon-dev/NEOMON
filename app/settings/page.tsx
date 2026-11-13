"use client";

import { FormEvent, useEffect, useState } from "react";
import { useProviderSession, type ProviderKind } from "@/components/provider-context";
import { requestJson } from "../../lib/api";

const DEFAULT_ENDPOINTS: Record<ProviderKind, string> = {
  ollama: "http://127.0.0.1:11434",
  lm_studio: "http://127.0.0.1:1234",
  openai_compatible: "https://api.openai.com",
};

interface TavilyStatus {
  provider: string;
  enabled: boolean;
  api_key_configured: boolean;
  search_depth: string;
  max_results: number;
  include_domains: string[];
  exclude_domains: string[];
  telemetry: {
    queries_submitted: number;
    search_requests_completed: number;
    search_requests_failed: number;
    results_discovered: number;
    results_retained: number;
    sources_accepted: number;
    sources_rejected: number;
    full_text_successes: number;
    full_text_failures: number;
    evidence_passages_extracted: number;
    last_latency_ms: number;
    avg_latency_ms: number;
    error_categories: Record<string, number>;
  };
}

export default function SettingsPage() {
  const { config, setConfig, clearConfig } = useProviderSession();
  const [provider, setProvider] = useState<ProviderKind>(config?.kind ?? "ollama");
  const [endpoint, setEndpoint] = useState(config?.endpoint ?? DEFAULT_ENDPOINTS.ollama);
  const [model, setModel] = useState(config?.model ?? "");
  const [apiKey, setApiKey] = useState(config?.apiKey ?? "");
  const [discoveredModels, setDiscoveredModels] = useState<string[]>(config?.discoveredModels ?? []);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(false);

  // Tavily configuration & telemetry state
  const [tavilyStatus, setTavilyStatus] = useState<TavilyStatus | null>(null);
  const [tavilyTestKey, setTavilyTestKey] = useState("");
  const [tavilySearchDepth, setTavilySearchDepth] = useState("advanced");
  const [tavilyMaxResults, setTavilyMaxResults] = useState(10);
  const [tavilyTesting, setTavilyTesting] = useState(false);
  const [tavilyTestResult, setTavilyTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    requestJson<TavilyStatus>("/providers/tavily/status")
      .then((data) => {
        if (!active) return;
        setTavilyStatus(data);
        setTavilySearchDepth(data.search_depth || "advanced");
        setTavilyMaxResults(data.max_results || 10);
      })
      .catch(() => {
        // Fallback if backend is starting up
      });
    return () => {
      active = false;
    };
  }, []);

  function handleKindChange(nextKind: ProviderKind) {
    const wasDefault = Object.values(DEFAULT_ENDPOINTS).includes(endpoint);
    setProvider(nextKind);
    if (wasDefault) {
      setEndpoint(DEFAULT_ENDPOINTS[nextKind]);
    }
  }

  async function testAndActivateConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    const trimmedKey = apiKey.trim();
    if (provider === "openai_compatible" && !trimmedKey) {
      setLoading(false);
      setResult({
        ok: false,
        message: "An API key is required for OpenAI-compatible remote endpoints.",
      });
      return;
    }

    const isLocalRuntime = provider === "ollama" || provider === "lm_studio";

    try {
      const payload = await requestJson<{
        connected: boolean;
        models: string[];
        error?: string;
        api_key_configured: boolean;
      }>("/providers/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: provider,
          endpoint: endpoint.trim(),
          model: model.trim() || undefined,
          api_key: trimmedKey || undefined,
          allow_local_runtime: isLocalRuntime,
        }),
      });
      const models = payload.models ?? [];
      setDiscoveredModels(models);
      const selectedModel = model.trim() || models[0] || "";
      if (selectedModel && !model.trim()) {
        setModel(selectedModel);
      }

      if (payload.connected) {
        setConfig({
          kind: provider,
          endpoint: endpoint.trim(),
          model: selectedModel || undefined,
          apiKey: trimmedKey || undefined,
          allowLocalRuntime: isLocalRuntime,
          discoveredModels: models,
          connected: true,
        });
        setResult({
          ok: true,
          message: `Connected and activated for this session. Discovered ${models.length} model(s).`,
        });
      } else {
        setResult({
          ok: false,
          message: payload.error ?? "Provider did not respond.",
        });
      }
    } catch (error) {
      setResult({ ok: false, message: error instanceof Error ? error.message : "Connection failed." });
    } finally {
      setLoading(false);
    }
  }

  async function testTavilyConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTavilyTesting(true);
    setTavilyTestResult(null);
    try {
      const payload = await requestJson<{
        connected: boolean;
        api_key_configured: boolean;
        message?: string;
        error?: string;
      }>("/providers/tavily/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: tavilyTestKey.trim() || undefined,
          search_depth: tavilySearchDepth,
        }),
      });
      if (payload.connected) {
        setTavilyTestResult({
          ok: true,
          message: payload.message || "Tavily connection test succeeded.",
        });
        // Refresh status
        const updated = await requestJson<TavilyStatus>("/providers/tavily/status");
        setTavilyStatus(updated);
      } else {
        setTavilyTestResult({
          ok: false,
          message: payload.error || "Tavily connection test failed.",
        });
      }
    } catch (error) {
      setTavilyTestResult({
        ok: false,
        message: error instanceof Error ? error.message : "Tavily request failed.",
      });
    } finally {
      setTavilyTesting(false);
    }
  }

  function handleModelChange(nextModel: string) {
    setModel(nextModel);
    if (config && config.connected) {
      setConfig({
        ...config,
        model: nextModel.trim() || undefined,
      });
    }
  }

  function handleClearSession() {
    clearConfig();
    setApiKey("");
    setDiscoveredModels([]);
    setResult({ ok: true, message: "Cleared in-memory provider configuration. Analysis will use rule_based mode." });
  }

  return (
    <main className="settings-page">
      <p className="eyebrow blue">MODEL CONFIGURATION</p>
      <h1>AI provider settings</h1>
      <p className="settings-intro">
        Provider settings and API keys are held strictly in browser memory for the current tab session.
        They are never written to localStorage, sessionStorage, URLs, or database records. Refreshing the
        browser clears credentials, so you must re-enter them here to run authenticated provider-backed analysis.
      </p>

      <div className="session-banner">
        {config?.connected ? (
          <div className="row-header">
            <div>
              <strong>Session provider active: {config.kind}</strong>
              <p className="muted">
                Endpoint: {config.endpoint} · Model: {config.model ?? "provider default"} ·{" "}
                {config.apiKey ? "API key loaded in memory" : "No API key"}
              </p>
            </div>
            <button className="outline-button compact-button" type="button" onClick={handleClearSession}>
              Clear session provider
            </button>
          </div>
        ) : (
          <p className="muted">
            No active in-memory provider for this tab session. Analysis runs will use explicit{" "}
            <code>rule_based</code> mode until you test and activate a provider below.
          </p>
        )}
      </div>

      <form className="settings-form" onSubmit={testAndActivateConnection}>
        <label>
          Provider
          <select value={provider} onChange={(event) => handleKindChange(event.target.value as ProviderKind)}>
            <option value="ollama">Ollama (local)</option>
            <option value="lm_studio">LM Studio (local)</option>
            <option value="openai_compatible">OpenAI-compatible</option>
          </select>
        </label>
        <label>
          Endpoint
          <input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} required />
        </label>
        <label>
          Model (optional)
          {discoveredModels.length > 0 ? (
            <select value={model} onChange={(event) => handleModelChange(event.target.value)}>
              <option value="">Use provider default</option>
              {discoveredModels.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={model}
              onChange={(event) => handleModelChange(event.target.value)}
              placeholder="Discovered after connection test"
            />
          )}
        </label>
        <label>
          API key {provider === "openai_compatible" ? "(required for remote endpoints)" : "(optional)"}
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            autoComplete="off"
          />
        </label>
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? "Testing..." : "Test & activate for session"}
        </button>
        {result && <p className={result.ok ? "connection-result success" : "connection-result error"}>{result.message}</p>}
      </form>

      {/* RESEARCH & WEB SEARCH PROVIDERS SECTION */}
      <section style={{ marginTop: "48px" }}>
        <p className="eyebrow blue">RESEARCH INTELLIGENCE PROVIDERS</p>
        <h2 style={{ fontSize: "22px", margin: "8px 0 12px" }}>Research & search providers</h2>
        <p className="settings-intro">
          NEOMON queries multiple academic and web providers concurrently. Scholarly APIs (Crossref, OpenAlex, arXiv)
          are enabled by default. Tavily Web Search provides high-precision discovery across current industry,
          governmental, and news sources.
        </p>

        {/* ACADEMIC PROVIDERS SUMMARY CARD */}
        <div className="session-banner" style={{ marginTop: "16px" }}>
          <strong>Default scholarly providers (Active)</strong>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px", marginTop: "10px" }}>
            <div style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--background)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>Crossref</strong>
                <span style={{ fontSize: "10px", color: "var(--green)", fontWeight: 600 }}>READY</span>
              </div>
              <p className="muted" style={{ fontSize: "11px", margin: "4px 0 0" }}>Scholarly metadata & DOIs</p>
            </div>
            <div style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--background)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>OpenAlex</strong>
                <span style={{ fontSize: "10px", color: "var(--green)", fontWeight: 600 }}>READY</span>
              </div>
              <p className="muted" style={{ fontSize: "11px", margin: "4px 0 0" }}>Open scholarly knowledge graph</p>
            </div>
            <div style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--background)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>arXiv</strong>
                <span style={{ fontSize: "10px", color: "var(--green)", fontWeight: 600 }}>READY</span>
              </div>
              <p className="muted" style={{ fontSize: "11px", margin: "4px 0 0" }}>Physics, CS, math preprints</p>
            </div>
          </div>
        </div>

        {/* TAVILY SEARCH PROVIDER CARD */}
        <div className="session-banner" style={{ marginTop: "20px" }}>
          <div className="row-header" style={{ alignItems: "center", marginBottom: "12px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <strong style={{ fontSize: "15px" }}>Tavily Web Search Provider</strong>
                {tavilyStatus?.api_key_configured ? (
                  tavilyStatus.enabled ? (
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "10px", background: "rgba(46, 204, 113, 0.15)", color: "var(--green)", fontWeight: 600 }}>
                      CONFIGURED & ACTIVE
                    </span>
                  ) : (
                    <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "10px", background: "rgba(241, 196, 15, 0.15)", color: "#f39c12", fontWeight: 600 }}>
                      DISABLED
                    </span>
                  )
                ) : (
                  <span style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "10px", background: "rgba(231, 76, 60, 0.15)", color: "#e74c3c", fontWeight: 600 }}>
                    UNCONFIGURED (KEY MISSING)
                  </span>
                )}
              </div>
              <p className="muted" style={{ margin: "4px 0 0", fontSize: "12px" }}>
                Official Tavily Search API adapter. Generates dimensional queries, preserves acronyms, and performs domain-isolated retrieval.
              </p>
            </div>
          </div>

          <form className="settings-form" style={{ marginTop: "12px", border: "none", padding: 0 }} onSubmit={testTavilyConnection}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label>
                Search depth
                <select value={tavilySearchDepth} onChange={(e) => setTavilySearchDepth(e.target.value)}>
                  <option value="basic">Basic (Fast & lightweight)</option>
                  <option value="advanced">Advanced (Deep content extraction)</option>
                </select>
              </label>
              <label>
                Max results per query
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={tavilyMaxResults}
                  onChange={(e) => setTavilyMaxResults(parseInt(e.target.value, 10) || 10)}
                />
              </label>
            </div>

            <label>
              Test API Key (optional for verification; backend key used if blank)
              <input
                type="password"
                placeholder={tavilyStatus?.api_key_configured ? "Using TAVILY_API_KEY from environment" : "tvly-..."}
                value={tavilyTestKey}
                onChange={(e) => setTavilyTestKey(e.target.value)}
                autoComplete="off"
              />
            </label>

            <button className="primary-button" disabled={tavilyTesting} type="submit" style={{ marginTop: "4px" }}>
              {tavilyTesting ? "Testing Tavily..." : "Test Tavily connection"}
            </button>
            {tavilyTestResult && (
              <p className={tavilyTestResult.ok ? "connection-result success" : "connection-result error"}>
                {tavilyTestResult.message}
              </p>
            )}
          </form>

          {/* TELEMETRY METRICS PANEL */}
          {tavilyStatus?.telemetry && (
            <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
              <strong style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
                Tavily Live Telemetry & Observability
              </strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px", marginTop: "10px" }}>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Queries</div>
                  <strong style={{ fontSize: "16px" }}>{tavilyStatus.telemetry.queries_submitted}</strong>
                </div>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Requests OK</div>
                  <strong style={{ fontSize: "16px", color: "var(--green)" }}>{tavilyStatus.telemetry.search_requests_completed}</strong>
                </div>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Discovered</div>
                  <strong style={{ fontSize: "16px" }}>{tavilyStatus.telemetry.results_discovered}</strong>
                </div>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Accepted</div>
                  <strong style={{ fontSize: "16px" }}>{tavilyStatus.telemetry.sources_accepted}</strong>
                </div>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Passages</div>
                  <strong style={{ fontSize: "16px" }}>{tavilyStatus.telemetry.evidence_passages_extracted}</strong>
                </div>
                <div style={{ padding: "8px", background: "var(--background)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                  <div className="muted" style={{ fontSize: "10px" }}>Avg Latency</div>
                  <strong style={{ fontSize: "16px" }}>{tavilyStatus.telemetry.avg_latency_ms} ms</strong>
                </div>
              </div>

              {/* Error category breakdown */}
              {Object.values(tavilyStatus.telemetry.error_categories || {}).some((v) => v > 0) && (
                <div style={{ marginTop: "10px", fontSize: "11px", color: "#e27d8f" }}>
                  <strong>Error breakdown: </strong>
                  {Object.entries(tavilyStatus.telemetry.error_categories)
                    .filter(([, count]) => count > 0)
                    .map(([cat, count]) => `${cat}: ${count}`)
                    .join(" · ")}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

