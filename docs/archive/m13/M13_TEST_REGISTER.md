# NEOMON M13 Test Register

| Area | Command / verification | Result | Notes |
|---|---|---|---|
| Frontend unit-style tests | `npm test` | PASS | 15 passed, 0 failed in 730ms |
| Frontend lint | `npm run lint` | PASS | **0 errors, 0 warnings** (all 9 React Hook exhaustive-deps resolved) |
| Frontend typecheck | `npx tsc --noEmit` | PASS | **0 type errors** |
| Frontend production build | `npm run build` | PASS | Turbopack build; all 27 static and dynamic routes compiled |
| Backend full test suite | `npm run backend:test` | PASS | **226 passed, 0 failed in 32.73s**; 0 SQLite lock errors (includes 3 new security regression tests) |
| Security Regression Suite | `backend/tests/test_security_audit.py` | PASS | **13/13 passed in 4.85s**: stream ticket single-use lifecycle, unauthed & cross-workspace export rejection, non-admin SSE subscription validation, RBAC, self-approval |
| PostgreSQL DDL Compilation | SQLAlchemy dialect compiler check | PASS | **100% ORM models compile cleanly to PostgreSQL DDL** (`UUID`, `JSONB`, `INET`, constraints, indexes) |
| Final Independent Release Audit | 7-part comprehensive technical audit | PASS | **CONDITIONALLY READY**: Core application, security, scientific calibration, and DB recovery 100% verified; container staging smoke test condition noted |
| E2E Product Completeness Suite | `scratch/test_product_completeness_e2e.py` | PASS | **13/13 steps passed**: Auth, Workspaces, Invites, Live Autonomous Ingestion, 8 Exports, Threads, Reviews, Self-Approval Guard, Notifications, Workflows, Gaps, Hypotheses, Benchmarks |
| Scientific Benchmark Regressions | `scratch/test_benchmarks_regression.py` | PASS | **2/2 benchmarks passed**: `nvidia-ai-era` & `downfall-of-nokia`; Decoupled Retrieval, Evidence, and Synthesis metrics verified |
| Database Query Plans & Indexing | `scratch/check_query_plans.py` | PASS | **100% index scan coverage** on hot queries (`ix_investigations_workspace_id`, `ix_sources_investigation_id`, `ix_evidence_source_id`, `ix_claims_investigation_id`, etc.) |
| Synthetic test fixture isolation | Ephemeral copy of `test_database.db` | PASS | 3.8 MB clean DB, 0 FK violations, disposable per test session |
| Alembic head alignment | `python -m alembic check` | PASS | Reaches `20261114_0016`; **0 pending operations / 0 schema drift** |
| Original database preservation | SHA-256 baseline verification | PASS | `FDA90EFE4288A2A76BB9C1DF4E4E636E7D191A0546C71342ECFBCB895703C4F2` **untouched** |
| Recovered DB integrity | `PRAGMA integrity_check` on `neomon_recovered.db` | PASS | `[('ok',)]`; 1,576 investigations, 16,942 contradictions |
| Test fixture foreign keys | `PRAGMA foreign_key_check` on `test_database.db` | PASS | **0 violations** (100% clean relational integrity) |
| Multi-tenant security audit | `scratch/verify_security_tenancy.py` | PASS | **100% 401 unauthenticated enforcement**, 403 horizontal isolation, 5-role RBAC, vertical escalation prevention, query sanitization |
| Localhost runtime audit | FastAPI (8000) & Next.js (3000) | PASS | Both servers running and healthy (`/health` ok, `/` HTTP 200) |
| Investigation Workspace UI Redesign (M13 Phase 2) | Playwright Browser Subagent | PASS | **43-step interactive verification**: sticky persistent header, 8-tab workspace, immediate Multi-Agent Intelligence, rebuilt Evidence Explorer (search, 5 filters, sorting, single calibration callout, 12/page pagination, expandable provenance), Sources Library (view extracted passages), Knowledge Graph, 18-section Report, URL hash navigation sync, 768px tablet responsive layout verified |
| Final Live Browser Acceptance Test (NEOMON 1.0) | Chromium Browser Subagent Fleet | PASS | **Complete end-to-end acceptance**: 5 mandated research investigations fully executed through multi-agent debate, adjudication, and 18-section reports; 19 routes audited; 142 interactive controls verified; 8 export formats tested; responsive layouts (1920x1080 to 390x844) verified |
| Docker container deployment | `docker compose up` | NOT TESTED | Docker executable unavailable in current Windows host environment |
