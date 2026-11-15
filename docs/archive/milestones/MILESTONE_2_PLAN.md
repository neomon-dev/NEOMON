# NEOMON Milestone 2 Plan

## Verified starting point

- The existing product shell is a Next.js 16 App Router application.
- The repository has no backend, persistence layer, provider integration, or test suite.
- Python 3.14.7 is available.
- FastAPI, Pydantic, HTTPX, and pytest are installed; SQLAlchemy and Alembic need to be added.
- The current dashboard is intentionally static and must remain visually intact.

## Deliverables

### Backend service

Create a standalone `backend/` Python package with:

- Application factory and `/api/v1` versioned routes.
- `/api/v1/health`, `/api/v1/providers`, and `/api/v1/events` endpoints.
- Strict Pydantic settings and request/response models.
- Explicit JSON error envelopes and request correlation IDs.
- Environment-controlled, allowlisted CORS origins.
- Async SQLAlchemy models and a development SQLite fallback; PostgreSQL remains the production URL.
- Alembic baseline migration without destructive schema operations.

### AI provider system

Define a provider protocol and independent adapters for:

- Ollama (`/api/tags`, `/api/chat`).
- LM Studio (OpenAI-compatible `/v1/models`, `/v1/chat/completions`).
- Generic OpenAI-compatible endpoints.

Provider configuration will accept endpoint, optional API key, model, timeout, and retry count. Credentials remain server-side and are never returned by API responses. Discovery and connection tests will report explicit failures rather than success-shaped fallbacks.

### Agent foundation

Create one reusable `BaseAgent` contract and twelve thin, independently importable agent modules. Each agent will expose identity, instructions, model configuration, execution status/history, and structured task output. Complex research behavior is explicitly deferred.

### Events and frontend integration

Use an in-process bounded event broker for development SSE. Events are typed and limited to agent lifecycle, model connectivity, and investigation status. Add a small client-side status panel that consumes real health/provider endpoints, displays loading/error states, and clearly labels demo mode.

## Validation strategy

- Backend unit tests for settings, CORS, provider URL validation, retry behavior, redacted errors, agent execution states, and event formatting.
- FastAPI integration tests for health, provider discovery/configuration, error envelopes, CORS, and SSE.
- Frontend lint, type-check, and production build.
- Production dependency audit and a documented demo-mode path.

## Explicit non-goals

- No real research retrieval, claim decomposition, LangGraph workflow, or fabricated research results.
- No authentication system in this milestone.
- No destructive migrations or automatic database resets.
- No API keys sent to the browser.
