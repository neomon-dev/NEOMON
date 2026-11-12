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

## Upcoming

- [ ] Add richer provider-specific claim decomposition and tool-enabled follow-up searches.
- [ ] Add planner/explorer/collector agent orchestration around research tasks.
- [ ] Add provenance-aware evidence assessments, citation genealogy, and interactive knowledge graph.
- [ ] Add report exports.
- [ ] Add deployment files and end-to-end browser coverage.
