import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const rootDir = process.cwd();

function loadTsModule(relPath, mocks = {}) {
  const fullPath = path.join(rootDir, relPath);
  const source = fs.readFileSync(fullPath, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: fullPath,
  }).outputText;

  const mod = { exports: {} };
  const localRequire = (specifier) => {
    if (specifier in mocks) return mocks[specifier];
    if (specifier.startsWith("@/")) {
      const target = specifier.slice(2);
      if (target in mocks) return mocks[target];
      return loadTsModule(`${target}.ts`, mocks);
    }
    if (specifier === "react" || specifier.startsWith("react/")) {
      return require(specifier);
    }
    return require(specifier);
  };

  const fn = new Function("exports", "require", "module", "__filename", "__dirname", compiled);
  fn(mod.exports, localRequire, mod, fullPath, path.dirname(fullPath));
  return mod.exports;
}

const mockLink = ({ href, children, ...rest }) => React.createElement("a", { href, ...rest }, children);

test("workspace formatting helpers preserve queue, generation, failure, and null states", () => {
  const helpers = loadTsModule("lib/workspace.ts");
  assert.equal(helpers.formatDurationSeconds(null), "—");
  assert.equal(helpers.formatDurationSeconds(0.45), "450 ms");
  assert.equal(helpers.formatDurationSeconds(12.34), "12.3 s");
  assert.equal(helpers.formatDurationSeconds(125), "2m 5s");

  assert.equal(helpers.formatAgentStatus("waiting_in_queue"), "Waiting in queue");
  assert.equal(helpers.formatAgentStatus("generating"), "Generating");
  assert.equal(helpers.formatAgentStatus("failed"), "Failed");
  assert.equal(helpers.agentStatusBadgeClass("waiting_in_queue"), "exec-status-badge status-queued");
  assert.equal(helpers.agentStatusBadgeClass("generating"), "exec-status-badge status-generating");
  assert.equal(helpers.agentStatusBadgeClass("failed"), "exec-status-badge status-failed");
  assert.equal(helpers.formatLabel("insufficient_evidence"), "insufficient evidence");
});

test("requestJson surfaces backend validation errors and connection errors clearly", async () => {
  const { requestJson, ApiError } = loadTsModule("lib/api.ts");
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({
          error: "validation_error",
          details: [{ loc: ["query", "limit"], msg: "Input should be <= 100" }],
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      );

    await assert.rejects(
      () => requestJson("/research/evidence?limit=500"),
      (err) => err instanceof ApiError && err.status === 422 && err.message.includes("Input should be <= 100"),
    );

    globalThis.fetch = async () => {
      throw new TypeError("fetch failed");
    };
    await assert.rejects(
      () => requestJson("/research/evidence"),
      (err) => err instanceof Error && err.message.includes("Cannot reach the NEOMON backend"),
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("EvidenceExplorer, SourceIntelligence, and AgentObservatory render loading and filter shell without placeholders", () => {
  const workspaceHelpers = loadTsModule("lib/workspace.ts");
  const commonMocks = {
    "next/link": { default: mockLink, __esModule: true },
    "next/navigation": {
      useSearchParams: () => new URLSearchParams("investigation_id=inv-123&source_id=src-456"),
    },
    "@/lib/api": { requestJson: () => new Promise(() => {}) },
    "lib/api": { requestJson: () => new Promise(() => {}) },
    "@/lib/workspace": workspaceHelpers,
    "lib/workspace": workspaceHelpers,
  };

  const { EvidenceExplorer } = loadTsModule("components/evidence-explorer.tsx", commonMocks);
  const evidenceHtml = renderToStaticMarkup(React.createElement(EvidenceExplorer));
  assert.match(evidenceHtml, /Evidence Explorer/);
  assert.match(evidenceHtml, /Search passage text/);
  assert.match(evidenceHtml, /Scoped to source src-456/);
  assert.match(evidenceHtml, /Loading persisted evidence passages/);
  assert.doesNotMatch(evidenceHtml, /reserved for the next NEOMON milestone/i);

  const { SourceIntelligence } = loadTsModule("components/source-intelligence.tsx", commonMocks);
  const sourceHtml = renderToStaticMarkup(React.createElement(SourceIntelligence));
  assert.match(sourceHtml, /Source Intelligence/);
  assert.match(sourceHtml, /All OA statuses/);
  assert.match(sourceHtml, /Loading persisted source intelligence/);
  assert.doesNotMatch(sourceHtml, /reserved for the next NEOMON milestone/i);

  const { AgentObservatory } = loadTsModule("components/agent-observatory.tsx", commonMocks);
  const agentHtml = renderToStaticMarkup(React.createElement(AgentObservatory));
  assert.match(agentHtml, /Agent Observatory/);
  assert.match(agentHtml, /Registered agent roster/);
  assert.match(agentHtml, /Loading persisted agent execution telemetry/);
  assert.doesNotMatch(agentHtml, /reserved for the next NEOMON milestone/i);
});

test("Route entrypoints replace placeholder routes for /evidence, /sources, and /agents", () => {
  for (const route of ["evidence", "sources", "agents"]) {
    const filePath = path.join(rootDir, "app", route, "page.tsx");
    assert.equal(fs.existsSync(filePath), true, `Expected route file ${filePath}`);
    const content = fs.readFileSync(filePath, "utf8");
    assert.match(content, /Suspense/);
  }
});
