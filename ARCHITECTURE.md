# NEOMON Architecture

## Current foundation

NEOMON contains a Next.js App Router application using React and TypeScript plus a standalone FastAPI backend in `backend/`. The dashboard keeps its original dark research-laboratory shell and now reads backend health and agent readiness. The backend provides versioned API contracts, provider adapters, SQLAlchemy models, migrations, and an in-process development event broker.

## Planned boundaries

```text
app/                 Route composition and UI entry points
components/          Reusable presentation and interactive panels
lib/                 Shared types, validation, and client-safe utilities
backend/app/         FastAPI routes, settings, providers, agents, events, and models
backend/migrations/  Alembic migrations; never reset production data
tests/                Focused unit, integration, and end-to-end coverage
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

### 3. Knowledge Export & Reproducibility Pipeline (Milestone 7C)
A dedicated, dependency-light export engine generates 8 distinct scientific and archival formats from persisted database relationships:
- **Markdown (`.md`)**: Complete 18-section report with YAML frontmatter and citation anchors.
- **Paginated PDF (`.pdf`)**: Pure Python PDF 1.4 document generator with running headers, footers, page numbering, and line-wrapping without paid APIs or headless browsers.
- **Research Snapshot JSON (`.json`)**: Machine-readable full investigation graph (`schema_version: 1.0.0`).
- **Standalone Interactive HTML Graph (`.html`)**: Zero-CDN interactive vector graph with pan, zoom, node drag, search, filtering, and side panel for offline air-gapped environments.
- **Vector Knowledge Graph (`.svg`)**: High-resolution vector graphic with color-coded nodes and relationship markers.
- **Semantic Linked Data (`.jsonld`)**: Schema.org `ScholarlyArticle` and `ClaimReview` metadata.
- **Evidence Dataset (`.csv`)**: RFC 4180 tabular evidence dataset with source provenance.
- **Sources Catalog (`.csv`)**: RFC 4180 tabular catalog of all discovered literature.

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
