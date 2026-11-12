# NEOMON Milestone 3 Plan

## Current implementation assessment

Milestone 2 provides:

- A FastAPI application factory with `/api/v1` routing, validation/error envelopes, request IDs, and allowlisted CORS.
- Provider adapters for Ollama and OpenAI-compatible endpoints with timeout/retry behavior.
- Twelve independently importable agent foundations, currently limited to explicit demo execution.
- SQLAlchemy async session infrastructure and Alembic-managed UUID models for investigations, agents, executions, model configurations, and research events.
- An in-process SSE broker.
- A Next.js dashboard, backend connection indicator, and provider settings page.

There is no real source search, document retrieval, research persistence beyond the initial investigation table, evidence extraction, or investigation workflow yet.

## Research engine architecture

```text
Investigation request
  -> query planner (question + quick/deep mode + limits)
  -> concurrent provider adapters
  -> normalized source candidates
  -> canonical URL/DOI/title/hash deduplication
  -> SSRF-safe document retrieval
  -> deterministic passage extraction
  -> claim/evidence relationship matching
  -> persisted source/document/evidence records
  -> investigation-specific SSE events
```

Provider adapters are independent and return normalized records. Search ranking is retained as provider metadata, never treated as credibility. Retrieved content remains untrusted data and cannot modify agent instructions.

## Data flow

1. Validate and persist an investigation with mode, timeframe, provider preferences, and limits.
2. Generate broad, academic, primary-source, and counter-evidence queries with deterministic deduplication.
3. Execute enabled providers concurrently with per-provider errors isolated and reported.
4. Normalize and deduplicate candidates while preserving original URLs and retrieval timestamps.
5. Retrieve only public HTTP(S) documents after DNS/IP and redirect validation.
6. Extract bounded text and metadata; store exact text only when it was present in the retrieved document.
7. Match passages to claims using transparent lexical relevance in this milestone; leave uncertain relationships reviewable.
8. Publish investigation-scoped events and expose persisted sources, claims, and evidence through the API.

## New modules

- `backend/app/research/providers.py`: search provider protocol and normalized result types.
- `backend/app/research/academic.py`: arXiv, Crossref, and OpenAlex adapters.
- `backend/app/research/query_planner.py`: query generation and deduplication.
- `backend/app/research/normalization.py`: URL, DOI, title, and content-hash normalization.
- `backend/app/research/retrieval.py`: SSRF-safe HTTP retrieval and bounded HTML/PDF/text extraction.
- `backend/app/research/evidence.py`: passage extraction and claim relationship matching.
- `backend/app/research/service.py`: bounded quick/deep orchestration and persistence.
- `backend/app/routers/research.py`: investigation, search, source, evidence, claim, cancel, and refresh endpoints.

## Database changes

Add migration-safe tables:

- `research_queries`
- `research_tasks`
- `sources`
- `documents`
- `claims`
- `evidence`
- `claim_evidence_relationships`
- `search_provider_executions`
- `extraction_executions`

Use UUID foreign keys, uniqueness constraints for stable source identifiers, indexes for investigation/source lookups, and preserve existing tables/rows.

## API changes

- `POST /api/v1/research/investigations`
- `GET /api/v1/research/investigations/{id}`
- `POST /api/v1/research/investigations/{id}/search`
- `GET /api/v1/research/investigations/{id}/sources`
- `GET /api/v1/research/investigations/{id}/evidence`
- `GET /api/v1/research/investigations/{id}/claims`
- `POST /api/v1/research/investigations/{id}/cancel`
- `POST /api/v1/research/sources/{id}/refresh`
- `GET /api/v1/research/investigations/{id}/events`

The existing global SSE endpoint remains available; the investigation endpoint filters events by investigation ID.

## Testing strategy

- Unit tests for query generation, URL normalization, source deduplication, safe URL validation, HTML extraction, evidence extraction, claim matching, and citation preservation.
- Provider adapter tests using mocked HTTP responses; real-provider tests remain opt-in and never run as default CI.
- Database/API integration tests using the development SQLite database and isolated temporary files.
- SSE tests for investigation-specific event filtering.
- Frontend lint, TypeScript, production build, and a live API smoke test.

## Scope boundary

This milestone does not claim semantic truth classification, calibrated confidence, private-source access, CAPTCHA/paywall bypass, or fabricated fallback research. If no provider is configured or a provider fails, the API reports the failure and the UI shows an honest incomplete state.
