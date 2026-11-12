"use client";

import { FormEvent, useState } from "react";
import { useProviderSession, type ProviderKind } from "@/components/provider-context";
import { requestJson } from "../../lib/api";

const DEFAULT_ENDPOINTS: Record<ProviderKind, string> = {
  ollama: "http://127.0.0.1:11434",
  lm_studio: "http://127.0.0.1:1234",
  openai_compatible: "https://api.openai.com",
};

export default function SettingsPage() {
  const { config, setConfig, clearConfig } = useProviderSession();
  const [provider, setProvider] = useState<ProviderKind>(config?.kind ?? "ollama");
  const [endpoint, setEndpoint] = useState(config?.endpoint ?? DEFAULT_ENDPOINTS.ollama);
  const [model, setModel] = useState(config?.model ?? "");
  const [apiKey, setApiKey] = useState(config?.apiKey ?? "");
  const [discoveredModels, setDiscoveredModels] = useState<string[]>(config?.discoveredModels ?? []);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(false);

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
    </main>
  );
}
