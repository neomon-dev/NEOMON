import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();

test("Milestone 12 Benchmark route and ScientificReliabilityWorkspace components exist", () => {
  const benchmarkPage = path.join(rootDir, "app", "benchmarks", "page.tsx");
  assert.ok(fs.existsSync(benchmarkPage), "app/benchmarks/page.tsx must exist");
  const benchmarkContent = fs.readFileSync(benchmarkPage, "utf8");
  assert.match(benchmarkContent, /Scientific Benchmark/);
  assert.match(benchmarkContent, /runHistoricalRegression/);
  assert.match(benchmarkContent, /nvidia-ai-era/);
  assert.match(benchmarkContent, /downfall-of-nokia/);

  const workspaceComp = path.join(rootDir, "components", "scientific-reliability-workspace.tsx");
  assert.ok(fs.existsSync(workspaceComp), "components/scientific-reliability-workspace.tsx must exist");
  const compContent = fs.readFileSync(workspaceComp, "utf8");
  assert.match(compContent, /Claim Evidence & Synthesis/);
  assert.match(compContent, /Study Independence Clusters/);
  assert.match(compContent, /Methodology Audit/);
  assert.match(compContent, /Execution Manifest & Provenance/);
  assert.match(compContent, /Reviewer Challenge/);
});

test("AppShell navigation includes Scientific Benchmarks link", () => {
  const shellPath = path.join(rootDir, "components", "app-shell.tsx");
  const shellContent = fs.readFileSync(shellPath, "utf8");
  assert.match(shellContent, /Scientific benchmarks/);
  assert.match(shellContent, /\/benchmarks/);
});

test("Investigation Detail UI includes ScientificReliabilityWorkspace mount", () => {
  const invPagePath = path.join(rootDir, "app", "investigations", "[id]", "page.tsx");
  const invContent = fs.readFileSync(invPagePath, "utf8");
  assert.match(invContent, /ScientificReliabilityWorkspace/);
  assert.match(invContent, /<ScientificReliabilityWorkspace/);
});
