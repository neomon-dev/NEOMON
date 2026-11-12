# NEOMON TODO

## Completed

- [x] Audit local workspace and GitHub repository state.
- [x] Document the actual greenfield baseline.
- [x] Create a runnable Next.js TypeScript foundation.
- [x] Add responsive dashboard navigation and explicit empty states.
- [x] Add FastAPI `/api/v1` health, agents, provider test, and SSE endpoints.
- [x] Add provider-independent Ollama, LM Studio, and OpenAI-compatible adapters.
- [x] Add twelve agent foundation modules with explicit demo execution.
- [x] Add SQLAlchemy models and non-destructive Alembic migrations.
- [x] Connect dashboard status and provider settings to the backend.

## Milestone 3 completed

- [x] Add real Crossref, OpenAlex, arXiv, and optional Tavily research adapters.
- [x] Add query planning, normalization, deduplication, safe retrieval, PDF extraction, and evidence extraction.
- [x] Add persistent research queries, sources, documents, claims, evidence, and execution records.
- [x] Add versioned research API routes and investigation-filtered SSE events.
- [x] Add new-investigation and investigation evidence/source interfaces.
- [x] Add unit and integration coverage for the research engine.

## Milestone 3.1 completed

- [x] Add transparent domain and outcome relevance scoring with included/filtered source explanations.
- [x] Remove publisher navigation and boilerplate from semantic HTML extraction.
- [x] Preserve PDF page provenance and distinguish metadata-only, abstract-only, and full-text documents.
- [x] Add evidence classification, traceability, document IDs, page/section provenance, and quality gates.
- [x] Add frontend quality indicators and source/evidence filters.
- [x] Add regression fixtures for relevant, irrelevant, boilerplate, contradictory, limitation, and page-traceable evidence.

## Milestone 5 (MVP Completion) completed

- [x] Fix backend runtime bugs, enforce provider endpoint SSRF protection, and add role-specific system instructions for Advocate, Skeptic, and specialist agents.
- [x] Add live dashboard, investigation history (`/history`), and complete investigation detail (`/investigations/[id]`) with claims, Advocate/Skeptic/specialist panels, and clickable evidence provenance.
- [x] Add session-only in-memory provider configuration (no `localStorage`/`sessionStorage`/DB key persistence) wired into initial and re-run analysis requests.
- [x] Add persisted SSE event replay (`Last-Event-ID` / `last_event_id`), cross-investigation isolation, backend restart recovery, cancellation handling, and frontend reconnect/polling recovery.

## Milestone 6A & 6B completed

- [x] Add Evidence Intelligence Workspace routes (`/evidence`, `/sources`, `/agents`) backed by persisted database records.
- [x] Add interactive Knowledge Graph Workspace (`/graph`) with React Flow, pan, zoom, node drag, search highlighting, branch collapse, and metadata inspection panel.

## Milestone 7A completed — Research Reliability & Local LLM Orchestration

- [x] Implement shared bounded provider request queue with configurable limits (`provider_queue_max_size: 50`) and queue position telemetry.
- [x] Enforce concurrency 1 and sequential agent scheduling for local providers (LM Studio & Ollama) to eliminate simultaneous inference GPU/VRAM overload.
- [x] Implement dual timeout separation (`queue_timeout_seconds` vs `inference_timeout_seconds`) and overall analysis timeout protection (1800s).
- [x] Add multi-tier argument grounding repair and conflict adjudicator repair.
- [x] Add deterministic rule-based fallback report synthesis ensuring report generation never aborts on agent inference failure.
- [x] Add automated analysis coverage tracking (`AnalysisCoverageSummary`).

## Milestone 7B completed — Advanced Report Intelligence & Synthesis

- [x] Implement standardized 18-section research report schema covering executive summaries, methodologies, perspectives, citations, and limitation directories.
- [x] Implement deterministic 5-dimension evidence strength scoring (`0.0` - `100.0`) across source independence, quality, full-text coverage, methodological rigor, and conflict resolution.
- [x] Implement immutable report versioning (`ReportVersion` table) with version listing, snapshot retrieval, and new version regeneration endpoints.
- [x] Build document-style report interface with Table of Contents jump navigation, score breakdown drawer, version switcher pills, and print stylesheet (`@media print`).

## Milestone 7C completed — Knowledge Export & Reproducibility

- [x] Implement modular export service supporting 8 standard formats:
  - [x] Markdown report (`.md`) with YAML frontmatter, 18 sections, and references catalog.
  - [x] Paginated PDF document (`.pdf`) via pure Python PDF 1.4 byte generation without paid APIs or headless browsers.
  - [x] Machine-readable research snapshot (`.json`) with full database graph serialization.
  - [x] Standalone interactive knowledge graph (`.html`) with embedded vector canvas and zero external CDN dependencies.
  - [x] High-resolution vector knowledge graph (`.svg`) with relationship markers and visual legend.
  - [x] Schema.org `ScholarlyArticle` and `ClaimReview` semantic Linked Data (`.jsonld`).
  - [x] Tabular Evidence dataset (`.csv`) with full bibliographic provenance.
  - [x] Tabular Sources catalog (`.csv`) with publication metadata and open-access statuses.
- [x] Build dedicated REST export router (`/research/investigations/{id}/export/*`) with manifest endpoint.
- [x] Implement responsive Knowledge Export panel in investigation detail UI with direct download endpoints.
- [x] Enforce zero secret/credential leakage and complete provenance linking in exported artifacts.

## Upcoming

- [ ] Add deployment automation (Docker Compose / production containerization).
- [ ] Add automated periodic background re-evaluation of saved investigations against newly published literature.
