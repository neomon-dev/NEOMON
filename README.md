# NEOMON

Neural Evidence Orchestration & Multi-Agent Observation Network.

NEOMON is being built incrementally as a research-intelligence platform. The current slice adds real public-source research, transparent relevance filtering, provenance-aware evidence extraction, quality indicators, and frontend source/evidence inspection.

## Development

### Frontend

```powershell
npm install
npm run dev
```

The dashboard runs at `http://localhost:3000`.

### Backend

Python 3.12+ is required. Python 3.14 is verified locally.

```powershell
python -m pip install -e ".\backend[test]"
Set-Location backend
python -m alembic upgrade head
Set-Location ..
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

The versioned API is available at `http://localhost:8000/api/v1`. The default development database is SQLite; configure PostgreSQL with `NEOMON_DATABASE_URL` for production-like environments.

Run backend tests:

```powershell
python -m pytest backend\tests -q
```

## Configuration

Copy [.env.example](./.env.example) values into the environment. `NEXT_PUBLIC_API_URL` is safe for the API base URL only. Provider API keys must never be placed in `NEXT_PUBLIC_*` variables.

The backend defaults to explicit demo mode. Demo agent responses are labeled as demo output and are not research findings.

## Current API surface

- `GET /api/v1/health` — backend status and demo mode.
- `GET /api/v1/agents` — the twelve registered agent foundations.
- `POST /api/v1/providers/test` — validate and test a provider configuration.
- `GET /api/v1/events` — typed Server-Sent Events stream.
- `POST /api/v1/research/investigations` — run a real quick/deep public-source investigation.
- `GET /api/v1/research/investigations/{id}/sources` — inspect preserved source metadata and URLs.
- `GET /api/v1/research/investigations/{id}/evidence` — inspect extracted passages.
- `POST /api/v1/providers/tavily/test` — verify Tavily connectivity and validate API key.
- `GET /api/v1/providers/tavily/status` — retrieve Tavily provider status, search depth, and live telemetry metrics.

Crossref, OpenAlex, and arXiv are available without keys. Tavily Search is supported as a first-class, optional general-web research provider (requires `TAVILY_API_KEY` or `NEOMON_TAVILY_API_KEY`). Tavily search executes concurrently with academic providers, producing 4-dimensional domain-isolated queries (causal mechanisms, counter-evidence, empirical data, and critical perspectives), preserving technical acronyms (AI, IT, ML, RAM, DDR5), and preventing semantic drift. Provider failures are recorded in telemetry without halting other providers, and snippet fallbacks are indexed as `abstract_only` documents when paywalled. Provider failures are returned as errors; the engine does not invent fallback sources or quotations.

OpenAlex locations and arXiv PDFs are checked for legitimate open-access copies. Unpaywall discovery is optional:
set `NEOMON_UNPAYWALL_EMAIL` (and, if supplied by Unpaywall, `NEOMON_UNPAYWALL_API_KEY`).
Candidate documents are metadata-matched before the existing SSRF-safe retriever downloads them. Access-restricted,
failed, abstract-only, and metadata-only sources remain visible; repository copies are document versions and are not
counted as independent studies.

Research quality is reported separately from technical execution. Sources expose relevance scores and inclusion reasons; documents are labeled metadata-only, abstract-only, or full-text; evidence retains exact text, page/section provenance, and classification. A completed investigation may still report `limited` or `insufficient_evidence`.

Milestone 4 adds bounded multi-agent analysis over a completed investigation:
`POST /api/v1/research/investigations/{id}/analysis` starts persisted
provider-backed planning, independent Advocate and Skeptic analysis, bounded
debate moderation, conflict adjudication, and report generation when a provider
is configured.
Inspect execution, claims, arguments, debates, decisions, and reports through
the corresponding `/api/v1/research/analysis/{job_id}/...` endpoints. Without
an optional provider configuration, the same stages use transparent,
explicitly `rule_based` selection from persisted evidence; they never create
citations or quotations. Provider output is schema-validated and evidence
references are checked against the investigation before persistence. Ollama,
LM Studio, and OpenAI-compatible models can be supplied per analysis request
with validated JSON output.

See [Architecture Documentation](docs/architecture/ARCHITECTURE.md), [Development Plan](docs/development/DEVELOPMENT_PLAN.md), [TODO](docs/development/TODO.md), and [Milestone Archive](docs/archive/milestones/) for system design and historical milestone scope.

## Milestone 5 MVP Highlights

- **Session-only provider configuration**: Configure Ollama, LM Studio, or OpenAI-compatible providers in `/settings` (or the provider context). API keys are kept strictly in React memory and are never written to `localStorage`, `sessionStorage`, URLs, logs, or database records; refreshing the page requires re-entering credentials.
- **Provider SSRF protection**: Provider endpoints are validated against SSRF rules, allowing configured local Ollama/LM Studio endpoints while blocking arbitrary private-network and cloud metadata targets.
- **Role-specific multi-agent prompts**: Advocate, Skeptic, and specialist agents use distinct role-specific system instructions when executing against a configured provider, while no-provider execution remains explicitly labeled `rule_based`.
- **Complete Investigation UI**:
  - `/` — Live dashboard with backend health, active provider status, and quick navigation.
  - `/history` — Persisted investigations list with status, mode, source counts, and links.
  - `/investigations/[id]` — Claims, visually separated Advocate/Skeptic/specialist assessments, clickable evidence references that scroll to and highlight exact persisted passages with source/document/access/page provenance, cancellation controls, and `Last-Event-ID` SSE replay with fallback polling.
- **Durable SSE replay & restart recovery**: `EventBroker` persists research and events to `research_events` for `Last-Event-ID` / `last_event_id` replay with investigation isolation, and `AnalysisManager.recover()` reconciles interrupted jobs on backend startup.

## Milestone 6 Intelligence Workspaces & Knowledge Graph

- **Evidence Intelligence Workspace**:
  - `/evidence` — Filterable passage explorer with relevance badges, source links, and claim tags.
  - `/sources` — Literature catalog with open access acquisition levels and document version counts.
  - `/agents` — Observatory displaying registered agents and real-time execution telemetry.
- **Interactive Knowledge Graph (`/graph`)**:
  - Full relational graph connecting Claims, Evidence, Sources, and Decisions with React Flow.
  - Interactive pan, zoom, node dragging, search query highlighting, and branch collapsing.
  - Side inspection drawer displaying passage provenance, relevance scores, and missing link warnings.

## Milestone 7 Reliability, Report Intelligence & Knowledge Export

- **Milestone 7A: Research Reliability & Concurrency Queue**:
  - Global `ProviderConcurrencyRegistry` with bounded queues and FIFO position tracking.
  - Enforced concurrency 1 and sequential scheduling for local providers (LM Studio & Ollama) to eliminate GPU/VRAM overload on consumer hardware.
  - Granular dual timeouts (`queue_timeout_seconds` vs `inference_timeout_seconds`) and 1800s overall analysis timeout.
  - Multi-tier argument grounding repair, adjudicator repair, and deterministic fallback report synthesis.
  - Automated analysis coverage tracking (`AnalysisCoverageSummary`).
- **Milestone 7B: 18-Section Report Intelligence**:
  - Standardized 18-section academic intelligence report schema.
  - Deterministic 5-dimension evidence strength scoring (`0.0` - `100.0`) categorized into 5 tiers (Very Strong, Strong, Moderate, Weak, Inconclusive).
  - Immutable report version snapshotting (`ReportVersion` table) with version switcher and regeneration endpoints (`/research/investigations/{id}/reports/*`).
  - Document-style report interface with Table of Contents jump navigation, score breakdown drawer, and print stylesheet (`@media print`).
- **Milestone 7C: Knowledge Export & Reproducibility**:
  - Dedicated export router (`GET /api/v1/research/investigations/{id}/export/*`) supporting 8 standard formats:
    1. **Markdown (`.md`)**: Full 18-section report with YAML frontmatter and citation anchors.
    2. **Paginated PDF (`.pdf`)**: Pure Python PDF 1.4 document generator with running headers, footers, page numbering, and line-wrapping without paid APIs or headless browsers.
    3. **Research Snapshot JSON (`.json`)**: Machine-readable full investigation graph (`schema_version: 1.0.0`).
    4. **Standalone Interactive HTML Graph (`.html`)**: Zero-CDN interactive vector graph with pan, zoom, node drag, search, filtering, and side panel for offline air-gapped environments.
    5. **Vector Knowledge Graph (`.svg`)**: High-resolution vector graphic with color-coded nodes and relationship markers.
    6. **Semantic Linked Data (`.jsonld`)**: Schema.org `ScholarlyArticle` and `ClaimReview` metadata.
    7. **Evidence Dataset (`.csv`)**: RFC 4180 tabular evidence dataset with source provenance.
    8. **Sources Catalog (`.csv`)**: RFC 4180 tabular catalog of all discovered literature.
  - Integrated Knowledge Export panel in the web interface with direct download triggers.
  - Complete secret/credential sanitization and strict provenance tracking.

---

## Documentation Index

The complete NEOMON documentation suite is organized in the [`docs/`](docs/) directory:

- **[Release & Certification (`docs/release/`)](docs/release/)**:
  - [NEOMON 1.0 Release Certificate](docs/release/NEOMON_1_0_FINAL_RELEASE_CERTIFICATE.md)
  - [Independent Technical Audit Report](docs/release/NEOMON_1_0_FINAL_INDEPENDENT_AUDIT.md)
  - [NEOMON 1.0 Product Release Report](docs/release/NEOMON_1_0_RELEASE_REPORT.md)
  - [Production Infrastructure & Readiness Report](docs/release/NEOMON_1_0_PRODUCTION_READINESS_REPORT.md)
  - [Safe Root Directory Cleanup Report](docs/release/NEOMON_1_0_CLEANUP_REPORT.md)
- **[Security Architecture (`docs/security/`)](docs/security/)**:
  - [Final Security & Tenancy Audit Report](docs/security/NEOMON_1_0_SECURITY_FINAL_REPORT.md)
  - [Security Configuration & Hardening Guide](docs/security/SECURITY_CONFIGURATION_GUIDE.md)
- **[Scientific Integrity (`docs/scientific-integrity/`)](docs/scientific-integrity/)**:
  - [Scientific Validation & Benchmark Report](docs/scientific-integrity/NEOMON_1_0_SCIENTIFIC_VALIDATION_REPORT.md)
- **[Architecture & Operations (`docs/architecture/`)](docs/architecture/)**:
  - [System Architecture](docs/architecture/ARCHITECTURE.md)
  - [Database Migration Guide](docs/architecture/DATABASE_MIGRATION_GUIDE.md)
  - [Backup & Restoration Guide](docs/architecture/BACKUP_AND_RESTORATION_GUIDE.md)
  - [Production Deployment Guide](docs/architecture/PRODUCTION_DEPLOYMENT_GUIDE.md)
  - [Worker Operations Guide](docs/architecture/WORKER_OPERATIONS_GUIDE.md)
- **[Development & QA (`docs/development/`)](docs/development/)**:
  - [Development Plan](docs/development/DEVELOPMENT_PLAN.md)
  - [Quality Assurance Policy](docs/development/QA_POLICY.md)
  - [Environment Variables Guide](docs/development/ENVIRONMENT_VARIABLES.md)
  - [Troubleshooting Guide](docs/development/TROUBLESHOOTING_GUIDE.md)
  - [TODO & Backlog](docs/development/TODO.md)
- **[Testing & Benchmarks (`docs/testing/`)](docs/testing/)**:
  - [Final Test Register & Certification Report](docs/testing/M13_FINAL_TEST_REPORT.md)
  - [Interactive Control Test Matrix](docs/testing/M13_INTERACTION_TEST_MATRIX.md)
- **[Historical Archives (`docs/archive/`)](docs/archive/)**:
  - [Milestone 13 Execution Reports (`docs/archive/m13/`)](docs/archive/m13/)
  - [Historical Milestone Plans (`docs/archive/milestones/`)](docs/archive/milestones/)
