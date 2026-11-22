# NEOMON Architecture

## Current foundation

NEOMON contains a Next.js App Router application using React and TypeScript plus a standalone FastAPI backend in `backend/`. The dashboard keeps its original dark research-laboratory shell and now reads backend health and agent readiness. The backend provides versioned API contracts, provider adapters, SQLAlchemy models, migrations, and an in-process development event broker.

## Streamlined Navigation and Consolidation Architecture

In accordance with product simplification principles, NEOMON standardizes its interface on 6 primary routes, while consolidating specialist analytics inside the core Investigation Workspace:

```
  Primary Navigation:
  /                     Dashboard
  /investigations/new   New Investigation & Claim Formulation
  /history              Research History & Audit Trail
  /evidence             Evidence & Reports (Consolidated Explorer)
  /automation           n8n Automation & Monitoring Bridge
  /settings             Provider & Hardware Configuration

  Consolidated Workspaces (Mounted within /investigations/[id]):
  - Knowledge Graph (React Flow Entity Topology)
  - Dialectical Debate (Advocate / Skeptic / Methodologist)
  - Contradiction Intelligence & Tension Graph
  - Research Gaps & Autonomous Horizon
  - Scientific Reliability & Study Independence Clusters
  - 18-Section Research Synthesis & Multi-Format Exports
```

The first backend integration should be server-only and expose stable, typed contracts to the UI. A Python/FastAPI service remains the preferred home for long-running research orchestration once the project has real workflow requirements; the Next.js app is the initial product shell, not a reason to duplicate orchestration logic in the browser.

Research quality flows through one server-side pipeline:

```text
provider results -> normalization -> relevance assessment -> safe retrieval
                 -> semantic extraction -> evidence classification -> quality gate
```

Milestone 4 adds a bounded analysis pipeline over persisted research records:

```text
persisted evidence -> planner -> advocate/skeptic/methodology/source/temporal agents
                   -> bounded provider debate -> provider adjudication -> traceable report
```

Analysis jobs, agent executions, arguments, debate rounds, decisions, and
report sections are persisted separately from the original research execution.
Arguments can reference only evidence and sources belonging to the same
investigation, and evidence is associated to claims through persisted
claim/evidence relationships rather than copied indiscriminately. The default
execution permits two debate rounds; a provider configuration enables
validated JSON completion for planning, Advocate, Skeptic, moderation,
adjudication, and reporting. No-provider execution is explicitly marked
`rule_based` and remains evidence-grounded rather than pretending to be an LLM
result. Reports persist source URL, access level, document version, page, and
section provenance for every cited evidence record.

Relevance scores are explainable ranking signals, not truth or credibility probabilities. Filtered sources remain persisted with their reasons, while evidence is only created from relevant retrieved or explicitly abstract-only provider content. Every evidence record links to a source and document and preserves exact text plus page/section provenance where available.

## Milestone 7 Architecture Extensions

### 1. Concurrency Limiting & Queue Orchestration (Milestone 7A)
Local LLM endpoints (LM Studio, Ollama) running on consumer hardware (e.g. 16 GB RAM with integrated GPUs) cannot handle parallel inference requests without running out of memory or dropping sockets.

- **`ProviderConcurrencyRegistry`**: Manages global per-provider FIFO queues and asynchronous semaphores.
- **Sequential Agent Scheduling**: When `is_local_provider(provider_kind)` is true, agent evaluations are scheduled strictly sequentially (`concurrency = 1`), preventing simultaneous POST requests.
- **Dual Timeouts**: Separates `queue_timeout_seconds` (time spent awaiting concurrency lease) from `inference_timeout_seconds` (active generation deadline).
- **Bounded Queues**: Enforces `provider_queue_max_size` (default 50) and rejects overflow with `ProviderQueueFullError`.
- **Fault-Tolerant Synthesis**: Multi-tier argument repair, adjudicator fallback, and deterministic rule-based report synthesis guarantee reports are never abandoned on agent timeout.
- **Coverage Summary**: Computes `AnalysisCoverageSummary` measuring evaluated vs unaddressed claims.

### 2. Advanced Report Intelligence & Evidence Scoring (Milestone 7B)
- **18-Section Standardized Report**: Standardizes academic structure covering executive summary, research question, scope, search strategy, findings, claim-by-claim adjudication, supporting/contradicting evidence, advocate/skeptic perspectives, methodological rigor, source quality, citation genealogy, temporal drift, open questions, limitations, final verdict, and reference directory.
- **Deterministic 5-Dimension Evidence Strength Scoring (0–100)**: Evaluates Source Independence (25%), Source Quality (25%), Full-Text Coverage (20%), Methodological Rigor (15%), and Conflict Resolution (15%). Classifies into 5 qualitative tiers (Very Strong, Strong, Moderate, Weak, Inconclusive).
- **Immutable Report Versioning**: `ReportVersion` table captures snapshots of each synthesis, enabling historical audits and regeneration without re-executing data collection.

### 4. Research Quality Calibration & Scientific Evidence Validation (Milestone 8G)

Milestone 8G establishes scientific truthfulness, lineage tracking, and rigorous quality calibration:

- **Canonical Source Credibility (`source_credibility.py`)**:
  - Decouples Source Type from Verification Status and Evidence Quality Attributes.
  - Strictly prohibits equating DOI presence or declared type with peer review. Preprints (arXiv, bioRxiv) and open repositories (Zenodo, Figshare) have registered DOIs but are explicitly marked non-peer-reviewed (`is_peer_reviewed = False`).
  - Distinguishes authoritative institutional reports (e.g. NIST, WHO, CDC) as primary evidence from peer-reviewed academic literature.
- **Source Lineage & Explainable Independence (`source_lineage.py`)**:
  - Replaces naive URL/domain counts with graph-based lineage components.
  - Collapses syndicated wire stories (Reuters, AP), derivative news commentary, shared primary citations, and overlapping co-authorship into single lineage clusters.
  - Computes `effective_independent_count` and `independence_ratio` to eliminate domain-diversity illusions.
- **Evidence-to-Claim Entailment Validation (`entailment_service.py`)**:
  - Evaluates every evidence passage against specific claims to classify inferential relationship: `direct_support`, `contextual_support`, `direct_contradiction`, `mitigating`, `methodological_limitation`, `insufficient_evidence`.
  - Flags `correlation_vs_causation_flag` when statistical association or concurrent timeline is presented without counterfactual causality or mechanism.
  - Records explicit `missing_inferential_steps` bridging evidence to claim.
- **Calibrated Research Quality Scoring & Coverage Decoupling (`quality_calibration_service.py`)**:
  - Calibrates 5 dimensions: Empirical Depth (25), Source Credibility (25), Source Independence (20), Methodological Rigor (15), Consensus Stability (15).
  - Decouples research coverage from raw score: coverage < 70% caps tier at Moderate; coverage < 85% caps tier at Strong.
  - Enforces strict prerequisites for `Very Strong`: calibrated score >= 85, coverage >= 80%, verified peer-reviewed publications >= 1, zero critical retrieval failures.
  - Evaluates provider retrieval failures with severity tiers (`harmless_optional`, `partial_coverage`, `significant_coverage`, `critical_loss`) and applies calibrated point deductions.
- **Scientific Quality Audit Workspace (`/quality-audit`)**:
  - Full-featured dashboard with 5 KPI summary cards, 5D breakdown, lineage explorer, entailment validation matrix, and provider failure impact log.
- **Export Integration Across All 9 Formats**:
  - Updates Markdown, PDF, JSON, HTML graph, SVG, JSON-LD, Evidence CSV, Sources CSV, and Manifest to reflect calibrated tiers, lineage clusters, and entailment classifications.

- **Autonomous Research Workflow Engine (Milestone 9: 9A–9J)**:
  - Persistent 15-state state machine orchestrating iterative multi-cycle research execution (`AutonomousWorkflowService`).
  - Deterministic research planning (`research_planner.py`) constructing prioritized actions for unsupported claims, active contradictions, and critical gaps.
  - Adaptive query refinement (`adaptive_query_service.py`) with token overlap / Jaccard deduplication, provider-tailored syntax, and deliberate counter-evidence probes.
  - Iterative evidence routing through canonical 8G validation and mathematical information gain tracking (`research_cycle_service.py`).
  - Strict resource budget accounting and scientific stopping criteria distinguishing operational exhaustion from evidence saturation and persistent uncertainty (`research_stopping_service.py`).
  - Human oversight modes (`assisted`, `supervised`, `bounded`) with review queue and one-click action approval/rejection.
  - Durable execution and startup crash recovery via Alembic migration `20261114_0012` and automated lifespan recovery checkpoints.
  - Autonomous Research Workspace (`/autonomous`) with KPI overview, creation modal, live monitor, review queue, and synthesized final report viewer.
  - Knowledge graph integration with `autonomous_workflow`, `research_cycle`, and `research_action` nodes and grounded edges.

## Milestone 2 contracts

- API prefix: `/api/v1`.
- Provider adapters are selected by configuration and never return API keys.
- Ollama uses `/api/tags`; LM Studio and OpenAI-compatible providers use `/v1/models`.
- Demo mode is explicit and never represents mock output as research.
- SSE events are typed as `agent.*`, `model.connected`, `investigation.status_changed`, and bounded `analysis.*` events.
- PostgreSQL is the production target; SQLite is the safe development fallback.

## Target data flow

```text
Question -> planner -> claims -> independent research
         -> advocate + skeptic -> methodology audit
         -> provenance/conflict analysis -> transparent report
```

Every evidence and graph edge must carry provenance to a retrieved source or documented analysis. External pages are untrusted data and cannot modify agent instructions or authorize tools.

## Current non-goals

- No hardcoded research findings.
- No fake provider connection status.
- No database schema before persistence requirements are validated.
- No API keys in client code.
