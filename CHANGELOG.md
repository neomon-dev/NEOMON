# Changelog

## Unreleased

### Added

- Audited the empty local workspace and empty GitHub repository.
- Added the initial Next.js App Router and TypeScript project configuration.
- Added a responsive NEOMON dashboard shell with navigation and explicit foundation empty states.
- Added architecture, development plan, TODO, environment, and changelog documentation.
- Added TypeScript, ESLint, production build, and dependency audit scripts with a clean validation baseline.
- Added the Milestone 2 FastAPI backend with versioned health, provider, agent, and SSE endpoints.
- Added provider adapters for Ollama, LM Studio, and OpenAI-compatible APIs with timeout/retry handling.
- Added twelve explicit agent foundations, SQLAlchemy models, Alembic migrations, demo mode, and frontend backend-status/provider settings.
- Added Milestone 3 real research providers, query orchestration, safe document retrieval, PDF extraction, source normalization, evidence extraction, persistence, SSE research events, and investigation UI.
- Added Milestone 3.1 relevance scoring, filtered-source provenance, semantic HTML cleanup, abstract/full-text access levels, page-aware evidence, evidence classifications, investigation quality gates, and evidence explorer filters.
- Added Milestone 3.2 OpenAlex/arXiv open-access locations, optional Unpaywall discovery, metadata matching, acquisition status, and document-version provenance.
- Added Milestone 4 bounded multi-agent analysis, validated evidence-reference protocol, persistent debates/adjudication/reports, provider JSON completion, restart recovery, analysis APIs, SSE events, and investigation activity UI.
- Added MVP Phase 1 genuine provider-backed planning, independent Advocate/Skeptic execution, bounded debate moderation, conflict adjudication, report intelligence, claim-specific evidence association, and persisted evidence provenance. No-provider execution remains explicitly rule-based.
- Added Milestone 5 (Stages 5A–5D) MVP completion:
  - Backend bug fixes, distinct role-specific system instructions for Advocate, Skeptic, and specialist agents, and provider endpoint SSRF protection (allowing configured local Ollama/LM Studio endpoints while blocking arbitrary private networks and cloud metadata).
  - Live dashboard (`/`), investigation history (`/history`), and complete investigation detail (`/investigations/[id]`) with claims, separate Advocate/Skeptic/specialist panels, clickable evidence provenance highlighting, and duplicate-submission prevention.
  - Session-only in-memory provider configuration (API keys are never persisted to `localStorage`, `sessionStorage`, URLs, logs, or database records) wired into initial analysis and re-run requests.
  - Persisted SSE event replay (`Last-Event-ID` / `last_event_id`) with cross-investigation isolation, gapless replay-to-live transition, `AnalysisManager.recover()` restart handling, and frontend `EventSource` + terminal-state polling recovery.
