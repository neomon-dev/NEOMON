# NEOMON M13 Known Issues

## Resolved in Final Independent Release Verification & Certification

- **Export Download Token Query Parameter Exposure**: Addressed security risk of passing session JWT tokens in export hyperlink query strings (`?token=...`). Replaced with an authenticated client-side fetch handler transmitting the token exclusively in `Authorization: Bearer <token>` headers, converting the response into an in-memory `Blob` and downloading programmatically. Verified zero token persistence in browser URLs, history, or access logs.
- **SSE Stream Long-Lived Token Exposure**: Native browser `EventSource` cannot pass custom headers. Previously passed session tokens in URL query string. Resolved by implementing cryptographic single-use stream tickets (`POST /api/v1/auth/stream-ticket`) with a 60-second TTL. Tickets are atomically consumed and deleted upon first connection. Replay attacks are rejected with HTTP 401 Unauthorized immediately.
- **Cross-Tenant SSE Stream Subscriptions**: Enforced parameter validation on `/api/v1/events` so that non-administrator accounts cannot subscribe to global event streams without specifying an authorized `investigation_id` (HTTP 400 Bad Request).
- **Document Acquisition vs Scientific Confidence Score Conflation**: Forensic audit revealed reported "95.0" and "94.0" scores were operational document-retrieval coverage ratios (19/20 sources acquired = 95.0%), not hypothesis certainty. Verified actual calibrated multi-agent debate scores: Microplastics 68.1 (Moderate), Green Hydrogen 62.7 (Moderate), Gen AI in Higher Ed 70.4 (Strong), Nokia Decline 59.3 (Moderate), AI Benchmarks 65.2 (Moderate). Capped ingestion heuristic in `backend/app/research/service.py` to `strong` maximum prior to debate.

## Resolved in Final Live Browser Acceptance Testing (NEOMON 1.0 GA)

- **SSE Native Browser 401 Handshake**: Native browser `EventSource` cannot pass custom `Authorization` headers. Resolved by passing encrypted session token in query parameter `?token=...`, which backend dependencies validate securely.
- **Export Download Direct Click 401**: Clicking `<a href="..." download>` links directly in browser navigation omitted Bearer header. Resolved by passing query token to export endpoints.
- **0-Source Analysis Start Guard**: Starting multi-agent analysis on an investigation with 0 sources triggered unhandled backend errors. Resolved by disabling the "Start Analysis" button with a helpful tooltip when `sources.length === 0 && !analysis`.
- **Quality Audit Client Re-render Loop**: `/quality-audit` entered an intensive fetch loop due to `[selectedId]` in `useEffect` dependencies. Resolved by scoping effect dependencies to `[initialInvestigationId]` with cancellation flags.
- **Benchmark Runs 404 Endpoint**: Fixed missing endpoint by implementing `@router.get("/{benchmark_id_or_slug}/runs")` in `backend/app/routers/benchmarks.py`.
- **Workspace Association on New Investigation Creation**: New investigations defaulted to global workspace 2. Resolved by including `workspace_id: activeWsId` from `localStorage` in the request payload.
- **CORS Error Response Preservation**: Fixed generic "Cannot reach backend" toast by adding CORS headers to Starlette/FastAPI `unexpected_error_handler` in `backend/app/errors.py`.

## Resolved in Phase 2 & Phase 3 (Product Completeness & UI/UX Transformation)

- **Frontend React Hook Dependency Warnings**: Resolved all 9 ESLint warnings across `app/gaps/page.tsx`, `app/hypotheses/page.tsx`, `components/autonomous-research-workspace.tsx`, `components/cross-investigation-workspace.tsx`, `components/hypothesis-workspace.tsx`, and `components/research-gap-workspace.tsx`. `npm run lint` now exits 0 with **0 errors, 0 warnings**.
- **Default Database Path Configuration**: Resolved potential startup crash where `DEFAULT_DATABASE_PATH` in `backend/app/config.py` pointed to `neomon.db` (corrupted original). Configured `DEFAULT_DATABASE_PATH` to prioritize `neomon_recovered.db` if present and explicitly configured `NEOMON_DATABASE_URL` in `.env`.
- **Invitation Token Serialization**: Added `invite_token` and `invite_link` to `InvitationResponse` in `backend/app/collaboration/schemas.py` so that invitation links can be copied or accepted in local development and automated testing.
- **Scientific Peer Review Self-Approval Guard**: Fully verified that author cannot approve their own review request (HTTP 403 `Self-approval guard: Independent peer review is required`), ensuring independent evaluation.
- **Origin UI Design System Tokens**: Fully implemented modern scientific design tokens, focus rings, scrollbars, categorized sidebar navigation, and upgraded `/investigations/new` interactive experience.
- **Investigation Detail Page Excessive Scrolling & Evidence Rendering**: Resolved by transforming `app/investigations/[id]/page.tsx` into a structured 8-tab workspace. Multi-Agent Intelligence was moved from the bottom to an immediately accessible tab near the top. Evidence Explorer was redesigned with multi-dimensional filtering, client-side pagination (12 cards/page), expandable provenance details, and replacement of repetitive explanation paragraphs with a single calibration callout banner. Sources section was made independently accessible with per-source evidence passage inspection. Browser back/forward navigation was enabled via URL hash synchronization.

## Resolved in Phase 0.3

- **Test Fixture Dependency on Historical Database**: Resolved by generating a clean synthetic test database fixture (`backend/tests/fixtures/test_database.db`, 3.8 MB) using Alembic migrations with 0 foreign-key violations. Prioritized in `backend/tests/conftest.py`. Eliminates test reliance on 50 MB recovered historical data, speeds up test execution from 48.01s to 35.62s, and ensures 100% deterministic test isolation.
- **Foreign-Key Relational Drift in Recovered Database**: Fully diagnosed and documented. `PRAGMA foreign_key_check` identified 3,105 violations in `neomon_recovered.db` caused by orphaned records where parent rows were located on physically truncated pages (> page 12,348). Documented in `M13_PHASE_0_3_DATA_SAFETY_REPORT.md`.
- **Browser Route Discrepancy**: Fully reconciled. Produced an exact route-by-route audit table covering all 31 application routes, reconciling the 7 targeted flows with the full Next.js routing architecture.

## Resolved in Phase 0.2

- **Database Corruption in `backend/neomon.db`**: Resolved via forensic diagnosis and clean extraction. Root cause was physical page truncation (12,348 pages on disk vs pointer references to 14,580). Reconstructed `neomon_recovered.db` containing 1,493 investigations, 16,942 contradictions, and intact historical benchmarks (NVIDIA H100 and Nokia Bell Labs). Verified `PRAGMA integrity_check = ok`. Original database strictly preserved untouched byte-for-byte in raw archive.
- **SQLite Concurrency & Lock Failures in Full Test Suite**: Resolved via Option B (Dynamic Test Copy Architecture) and refined in Phase 0.3. In `backend/app/db.py`, enabled `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=30000;`, and `check_same_thread=False`. Full test suite: **223 passed, 0 failed, 0 lock errors**.
- **Alembic Schema Drift on Recovered Database**: Upgraded `neomon_recovered.db` and test fixture to revision `20261114_0016`. Verified via `python -m alembic check`: "No new upgrade operations detected".
- **Unauthenticated Administrator Fallback & RBAC**: Fully audited. 100% of unauthenticated requests return HTTP 401 across 30+ endpoints. Horizontal workspace boundaries return HTTP 403. 5-role RBAC hierarchy and role escalation protections verified.

## Resolved in Phase 0.1

- Unfiltered graph, quality, evidence, source, observatory, and autonomous workflow routes no longer treat users with no memberships as global members.
- Unassigned legacy investigations require explicit membership in the global workspace for direct access.

## Confirmed & Tracked for Subsequent M13 Phases

- **Environment Rate Limiter**: Full backend test suite requires `NEOMON_ENVIRONMENT=test`; running tests against default development environment hits shared in-memory rate limiting. Handled automatically by the root npm script `npm run backend:test`.
- **Docker Host Environment**: Docker daemon is unavailable on the current local host. Docker Compose and PostgreSQL/Redis container deployments cannot be executed locally; dialect compatibility is verified via SQLAlchemy and mock layers.
- **Frontend React Hook Warnings**: ESLint emits 9 React Hook dependency warnings across gaps, hypotheses, autonomous research, cross-investigation, hypothesis, and research-gap components. Slated for cleanup in Phase 2 (UI consistency).

## Security Review Candidates (Phase 3 Audit)

- Verify that discovery opportunities are publication-checked and counterexample-checked rather than generic LLM suggestions.
- Verify study independence is applied directly to confidence score calculation and not only rendered on the frontend.
- Verify report, export, and reproducibility outputs preserve exact evidence provenance and distinguish metadata, abstract, and full text.
