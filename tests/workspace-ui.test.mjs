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
      const targetPath = fs.existsSync(path.join(rootDir, `${target}.tsx`))
        ? `${target}.tsx`
        : fs.existsSync(path.join(rootDir, `${target}.ts`))
        ? `${target}.ts`
        : `${target}.ts`;
      return loadTsModule(targetPath, mocks);
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
    "@/lib/auth-context": { useAuth: () => ({ user: null, activeWorkspace: null, workspaces: [] }) },
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

test("Route entrypoints replace placeholder routes for /evidence, /sources, /agents, and /graph", () => {
  for (const route of ["evidence", "sources", "agents", "graph"]) {
    const filePath = path.join(rootDir, "app", route, "page.tsx");
    assert.equal(fs.existsSync(filePath), true, `Expected route file ${filePath}`);
    const content = fs.readFileSync(filePath, "utf8");
    assert.match(content, /Suspense/);
  }
});

test("Graph helpers support filtering, search highlighting, branch collapse, merging, and layout determinism", () => {
  const graphHelpers = loadTsModule("lib/graph.ts", {
    "@xyflow/react": {},
  });

  const invId = "11111111-1111-1111-1111-111111111111";
  const claimNode = {
    id: "claim:c1",
    entity_id: "c1",
    type: "claim",
    label: "Async review prevents escapes",
    description: "Asynchronous code review reduces escaped bugs.",
    investigation_id: invId,
    status: "moderately_supported",
    missing_provenance: [],
    has_hidden_neighbors: false,
    metadata: {},
  };
  const evSupp = {
    id: "evidence:e1",
    entity_id: "e1",
    type: "evidence",
    label: "34% defect reduction",
    description: "34% defect reduction in controlled teams.",
    investigation_id: invId,
    status: "supporting",
    missing_provenance: [],
    has_hidden_neighbors: false,
    metadata: {},
  };
  const evContra = {
    id: "evidence:e2",
    entity_id: "e2",
    type: "evidence",
    label: "No effect on 1-line diffs",
    description: "Null result on trivial edits.",
    investigation_id: invId,
    status: "contradicting",
    missing_provenance: ["missing_document"],
    has_hidden_neighbors: false,
    metadata: {},
  };
  const srcNode = {
    id: "source:s1",
    entity_id: "s1",
    type: "source",
    label: "PR Review Study",
    description: "ACM 2024",
    investigation_id: invId,
    status: "included",
    missing_provenance: [],
    has_hidden_neighbors: false,
    metadata: {},
  };
  const edges = [
    { id: "c1->e1", source: "claim:c1", target: "evidence:e1", relationship_type: "supports", label: "supports" },
    { id: "c1->e2", source: "claim:c1", target: "evidence:e2", relationship_type: "contradicts", label: "contradicts" },
    { id: "e1->s1", source: "evidence:e1", target: "source:s1", relationship_type: "extracted_from_source", label: "source" },
  ];

  // Collapse claim branch hides descendants without infinite loop
  const collapsed = graphHelpers.computeVisibleSubgraph([claimNode, evSupp, evContra, srcNode], edges, {
    activeNodeTypes: new Set(graphHelpers.NODE_TYPE_ORDER),
    relationshipFilter: "all",
    collapsedBranchIds: new Set(["claim:c1"]),
  });
  assert.deepEqual(
    collapsed.visibleNodes.map((n) => n.id),
    ["claim:c1"],
  );
  assert.equal(collapsed.hiddenDescendantCounts.get("claim:c1"), 3);

  // Relationship filter isolates contradicting edges cleanly
  const contraOnly = graphHelpers.computeVisibleSubgraph([claimNode, evSupp, evContra, srcNode], edges, {
    activeNodeTypes: new Set(graphHelpers.NODE_TYPE_ORDER),
    relationshipFilter: "contradicts",
    collapsedBranchIds: new Set(),
  });
  assert.deepEqual(
    contraOnly.visibleEdges.map((e) => e.id),
    ["c1->e2"],
  );

  // Search highlighting & deterministic positions
  const built = graphHelpers.buildFlowElements([claimNode, evSupp, evContra], edges.slice(0, 2), {
    searchQuery: "34%",
    collapsedBranchIds: new Set(),
    hiddenDescendantCounts: new Map(),
  });
  assert.deepEqual(built.matchedNodeIds, ["evidence:e1"]);
  const e1Flow = built.flowNodes.find((n) => n.id === "evidence:e1");
  const e2Flow = built.flowNodes.find((n) => n.id === "evidence:e2");
  assert.equal(e1Flow.data.isSearchMatch, true);
  assert.equal(e2Flow.data.isDimmed, true);

  // Merge graph responses deduplicates cleanly
  const merged = graphHelpers.mergeGraphResponses(
    {
      investigation_id: invId,
      nodes: [claimNode, evSupp],
      edges: [edges[0]],
      truncated: true,
      total_counts: { claims: 1, evidence: 2, documents: 0, sources: 1, arguments: 0, decisions: 0 },
      node_type_counts: {},
      relationship_type_counts: {},
    },
    {
      investigation_id: invId,
      nodes: [evSupp, evContra, srcNode],
      edges: [edges[1], edges[2]],
      truncated: false,
      total_counts: { claims: 1, evidence: 2, documents: 0, sources: 1, arguments: 0, decisions: 0 },
      node_type_counts: {},
      relationship_type_counts: {},
    },
  );
  assert.equal(merged.nodes.length, 4);
  assert.equal(merged.edges.length, 3);
});

test("GraphDetailPanel renders Claim, Evidence, Source, and Edge details with missing provenance warnings", () => {
  const workspaceHelpers = loadTsModule("lib/workspace.ts");
  const graphHelpers = loadTsModule("lib/graph.ts", { "@xyflow/react": {} });
  const { GraphDetailPanel } = loadTsModule("components/graph-detail-panel.tsx", {
    "next/link": { default: mockLink, __esModule: true },
    "@/lib/graph": graphHelpers,
    "@/lib/workspace": workspaceHelpers,
  });

  const invId = "11111111-1111-1111-1111-111111111111";
  const claimNode = {
    id: "claim:c1",
    entity_id: "c1",
    type: "claim",
    label: "Claim label",
    description: "Full claim text",
    investigation_id: invId,
    status: "contradictory",
    missing_provenance: [],
    has_hidden_neighbors: false,
    metadata: {
      full_text: "Automated reviews cut escapes.",
      supporting_evidence: [{ id: "e1", text: "Supporting passage", relevance_score: 0.9 }],
      contradicting_evidence: [{ id: "e2", text: "Contradicting passage", relevance_score: 0.8 }],
      related_arguments: [{ id: "a1", agent_identifier: "advocate", argument_type: "supporting", confidence_level: "moderate", text: "Arg" }],
      adjudication_decision: { id: "d1", decision: "contradictory", explanation: "Mixed subgroup findings." },
    },
  };
  const claimHtml = renderToStaticMarkup(
    React.createElement(GraphDetailPanel, {
      selectedNode: claimNode,
      selectedEdge: null,
      nodeMap: new Map([["claim:c1", claimNode]]),
      isCollapsed: false,
      expandingNodeId: null,
      onExpandNode: () => {},
      onToggleCollapse: () => {},
      onSelectNodeById: () => {},
      onClearSelection: () => {},
    }),
  );
  assert.match(claimHtml, /Automated reviews cut escapes/);
  assert.match(claimHtml, /Supporting evidence \(1\)/);
  assert.match(claimHtml, /Contradicting evidence \(1\)/);
  assert.match(claimHtml, /Mixed subgroup findings/);
  assert.match(claimHtml, /Claim evidence in Explorer/);

  const evNode = {
    id: "evidence:e2",
    entity_id: "e2",
    type: "evidence",
    label: "Contradicting passage",
    description: "Exact contradicting text",
    investigation_id: invId,
    status: "contradicting",
    missing_provenance: ["missing_document"],
    has_hidden_neighbors: false,
    metadata: {
      exact_text: "Exact contradicting text",
      evidence_type: "contradicting",
      relevance_score: 0.8,
      page_number: 5,
      section_name: "Limitations",
      extraction_method: "pdf",
      associated_claims: [{ claim_id: "c1", text: "Automated reviews cut escapes.", status: "contradictory", type: "contradicting" }],
      document_id: null,
      source_id: "s1",
      source_title: "PR Study",
    },
  };
  const evHtml = renderToStaticMarkup(
    React.createElement(GraphDetailPanel, {
      selectedNode: evNode,
      selectedEdge: null,
      nodeMap: new Map([["evidence:e2", evNode]]),
      isCollapsed: false,
      expandingNodeId: null,
      onExpandNode: () => {},
      onToggleCollapse: () => {},
      onSelectNodeById: () => {},
      onClearSelection: () => {},
    }),
  );
  assert.match(evHtml, /Missing persisted provenance/);
  assert.match(evHtml, /Page 5/);
  assert.match(evHtml, /Limitations/);
  assert.match(evHtml, /Document record missing/);

  const srcNode = {
    id: "source:s1",
    entity_id: "s1",
    type: "source",
    label: "PR Study",
    description: "ACM 2024",
    investigation_id: invId,
    status: "included",
    missing_provenance: [],
    has_hidden_neighbors: false,
    metadata: {
      title: "PR Study",
      authors: ["Dr. E. Baker"],
      doi: "10.1145/review.2024",
      publication_date: "2024",
      original_url: "https://example.org/pr",
      document_versions: [{ document_id: "doc1", version_type: "publishedVersion", access_level: "full_text" }],
      related_evidence: [{ id: "e2", exact_text: "Exact contradicting text" }],
      evidence_count: 1,
    },
  };
  const srcHtml = renderToStaticMarkup(
    React.createElement(GraphDetailPanel, {
      selectedNode: srcNode,
      selectedEdge: null,
      nodeMap: new Map([["source:s1", srcNode]]),
      isCollapsed: false,
      expandingNodeId: null,
      onExpandNode: () => {},
      onToggleCollapse: () => {},
      onSelectNodeById: () => {},
      onClearSelection: () => {},
    }),
  );
  assert.match(srcHtml, /Dr\. E\. Baker/);
  assert.match(srcHtml, /10\.1145\/review\.2024/);
  assert.match(srcHtml, /Open in Source Intelligence/);
});

test("KnowledgeGraphWorkspace renders interactive controls shell without placeholders", () => {
  const workspaceHelpers = loadTsModule("lib/workspace.ts");
  const graphHelpers = loadTsModule("lib/graph.ts", { "@xyflow/react": {} });
  const noop = () => null;
  const xyflowMock = {
    Background: noop,
    Controls: noop,
    MiniMap: noop,
    ReactFlow: ({ children }) => React.createElement("div", { "data-testid": "react-flow" }, children),
    ReactFlowProvider: ({ children }) => React.createElement("div", null, children),
    applyNodeChanges: (_c, nodes) => nodes,
    useReactFlow: () => ({ fitView: () => Promise.resolve(), setCenter: () => Promise.resolve() }),
    Handle: noop,
    Position: { Left: "left", Right: "right" },
  };
  const { KnowledgeGraphNode } = loadTsModule("components/knowledge-graph-node.tsx", {
    "@xyflow/react": xyflowMock,
    "@/lib/graph": graphHelpers,
  });
  const { GraphDetailPanel } = loadTsModule("components/graph-detail-panel.tsx", {
    "next/link": { default: mockLink, __esModule: true },
    "@/lib/graph": graphHelpers,
    "@/lib/workspace": workspaceHelpers,
  });
  const { KnowledgeGraphWorkspace } = loadTsModule("components/knowledge-graph-workspace.tsx", {
    "@xyflow/react": xyflowMock,
    "@xyflow/react/dist/style.css": {},
    "next/link": { default: mockLink, __esModule: true },
    "next/navigation": { useSearchParams: () => new URLSearchParams("") },
    "@/lib/api": { requestJson: () => new Promise(() => {}) },
    "@/lib/graph": graphHelpers,
    "@/lib/workspace": workspaceHelpers,
    "@/components/knowledge-graph-node": { KnowledgeGraphNode },
    "@/components/graph-detail-panel": { GraphDetailPanel },
  });

  const html = renderToStaticMarkup(React.createElement(KnowledgeGraphWorkspace));
  assert.match(html, /Knowledge Graph/);
  assert.match(html, /Search nodes/);
  assert.match(html, /Fit to screen/);
  assert.match(html, /Reset layout/);
  assert.match(html, /Loading persisted evidence knowledge graph/);
  assert.doesNotMatch(html, /reserved for the next NEOMON milestone/i);
});

test("Investigation Detail UI includes Milestone 7B Report Intelligence and 7C Knowledge Export controls", () => {
  const filePath = path.join(rootDir, "app", "investigations", "[id]", "page.tsx");
  assert.equal(fs.existsSync(filePath), true, `Expected investigation page file ${filePath}`);
  const content = fs.readFileSync(filePath, "utf8");

  // Milestone 7B: 18 structured report sections, evidence strength score, and version switcher
  assert.match(content, /evidence_strength/);
  assert.match(content, /report-version-bar/);
  assert.match(content, /Versions:/);
  assert.match(content, /New Version/);
  assert.match(content, /report-toc-bar/);
  assert.match(content, /report-section-card/);
  assert.match(content, /executive_summary/);
  assert.match(content, /overall_assessment/);

  // Milestone 7C: Knowledge Export panel with 8 reproducible formats
  assert.match(content, /Knowledge Export & Reproducibility/);
  assert.match(content, /export\/\$\{f\.endpoint\}/);
  assert.match(content, /endpoint: "markdown"/);
  assert.match(content, /endpoint: "pdf"/);
  assert.match(content, /endpoint: "json"/);
  assert.match(content, /endpoint: "html-graph"/);
  assert.match(content, /endpoint: "svg"/);
  assert.match(content, /endpoint: "json-ld"/);
  assert.match(content, /endpoint: "evidence-csv"/);
  assert.match(content, /endpoint: "sources-csv"/);
});

test("Investigation Detail UI includes Milestone 8A Research Gap Discovery Workspace and entrypoints", () => {
  const invPagePath = path.join(rootDir, "app", "investigations", "[id]", "page.tsx");
  const invContent = fs.readFileSync(invPagePath, "utf8");
  assert.match(invContent, /ResearchGapWorkspace/);
  assert.match(invContent, /Research Gaps & Horizon/);

  const gapsPagePath = path.join(rootDir, "app", "gaps", "page.tsx");
  assert.equal(fs.existsSync(gapsPagePath), true, "app/gaps/page.tsx must exist");

  const componentPath = path.join(rootDir, "components", "research-gap-workspace.tsx");
  assert.equal(fs.existsSync(componentPath), true, "components/research-gap-workspace.tsx must exist");
  const compContent = fs.readFileSync(componentPath, "utf8");
  assert.match(compContent, /AUTONOMOUS GAP DISCOVERY · MILESTONE 8A/);
  assert.match(compContent, /Evidence Coverage/);
  assert.match(compContent, /Run Gap Discovery/);
  assert.match(compContent, /copy-query-button/);
  assert.match(compContent, /gap-missing-info-box/);
});

