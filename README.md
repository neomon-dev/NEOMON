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

Crossref, OpenAlex, and arXiv are available without keys. Tavily is optional and requires `NEOMON_TAVILY_API_KEY`. Provider failures are returned as errors; the engine does not invent fallback sources or quotations.

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

See [MILESTONE_3_1_PLAN.md](./MILESTONE_3_1_PLAN.md), [MILESTONE_2_PLAN.md](./MILESTONE_2_PLAN.md), [ARCHITECTURE.md](./ARCHITECTURE.md), and [TODO.md](./TODO.md) for scope and next steps.

## Milestone 5 MVP Highlights

- **Session-only provider configuration**: Configure Ollama, LM Studio, or OpenAI-compatible providers in `/settings` (or the provider context). API keys are kept strictly in React memory and are never written to `localStorage`, `sessionStorage`, URLs, logs, or database records; refreshing the page requires re-entering credentials.
- **Provider SSRF protection**: Provider endpoints are validated against SSRF rules, allowing configured local Ollama/LM Studio endpoints while blocking arbitrary private-network and cloud metadata targets.
- **Role-specific multi-agent prompts**: Advocate, Skeptic, and specialist agents use distinct role-specific system instructions when executing against a configured provider, while no-provider execution remains explicitly labeled `rule_based`.
- **Complete Investigation UI**:
  - `/` — Live dashboard with backend health, active provider status, and quick navigation.
  - `/history` — Persisted investigations list with status, mode, source counts, and links.
  - `/investigations/[id]` — Claims, visually separated Advocate/Skeptic/specialist assessments, clickable evidence references that scroll to and highlight exact persisted passages with source/document/access/page provenance, cancellation controls, and `Last-Event-ID` SSE replay with fallback polling.
- **Durable SSE replay & restart recovery**: `EventBroker` persists research and analysis events to `research_events` for `Last-Event-ID` / `last_event_id` replay with investigation isolation, and `AnalysisManager.recover()` reconciles interrupted jobs on backend startup.
