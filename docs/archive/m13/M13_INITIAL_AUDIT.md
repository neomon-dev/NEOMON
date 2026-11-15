# NEOMON M13 Initial Audit

**Date:** 2026-11-14  
**Repository:** `neomon-dev/NEOMON`  
**Branch:** `main`  
**Audit mode:** Read-only inspection plus existing validation commands. No commit or push.

## 1. Architecture verified

NEOMON is a Next.js App Router frontend with React, TypeScript, CSS, and React
Flow. The backend is a standalone FastAPI application using async SQLAlchemy,
Alembic, SQLite for development, and PostgreSQL/Redis deployment configuration.
The backend includes provider adapters, research retrieval and evidence
extraction, persisted agent analysis, autonomous workflows, collaboration,
reproducibility, benchmarks, exports, background jobs, and operational backup
utilities.

The application has a versioned `/api/v1` surface for research and analysis,
while authentication, collaboration, jobs, reliability, and several M10–M12
routers expose their own `/api/v1` prefixes. The application lifespan creates
the schema, recovers analysis/workflow state, and optionally starts the worker.

## 2. Functionality verified in code

### Backend

- Authentication uses password hashing, session tokens, expiration, revocation,
  password changes, and reset-token persistence.
- `get_current_user` rejects missing, invalid, expired, revoked, and inactive
  sessions; no silent administrator fallback is present in that dependency.
- Workspaces and membership roles are modeled with a hierarchy from viewer to
  owner. Collaboration services consistently call the permission service for
  membership and role checks in the inspected paths.
- Research models persist investigations, sources, documents, claims, evidence,
  evidence relationships, provenance, quality signals, and provider/retrieval
  state.
- M13-relevant prior work is present: gap discovery, hypotheses, contradiction
  analysis, trends, autonomous workflows, scientific verification, methodology
  audit, study independence, reproducibility, benchmarks, and human corrections.
- Worker code includes polling, concurrency, heartbeat, startup recovery, and
  graceful shutdown paths. Redis cache support is optional and falls back to an
  in-process implementation.
- Docker Compose defines PostgreSQL, Redis, backend, worker, and frontend
  services with health checks and persistent volumes.
- Backup utilities create verified archives, validate manifests/checksums, and
  restore SQLite databases to a target path.

### Frontend

- The route inventory includes dashboard, new investigation, investigation
  detail, autonomous workflows, workspaces/members/settings/activity, reviews,
  notifications, history, intelligence, graph, gaps, hypotheses, synthesis,
  contradictions, trends, quality audit, benchmarks, evidence, agents,
  sources, settings, profile, login/register, and password recovery.
- Shared components exist for the application shell, agent observatory,
  evidence/source exploration, graph, collaboration, autonomous workflows,
  gaps, hypotheses, trends, and scientific reliability.
- Existing frontend tests cover collaboration API shape, route presence,
  reliability UI, graph helpers, evidence/source/agent shells, and report/
  knowledge-export mounts.

## 3. Verified incomplete or failing areas

### Build and test infrastructure

- The root backend test command fails before collection because the frontend
  `app` package shadows `backend\app`. Running pytest from `backend\` collects
  successfully, but the full suite is not green: 28 failed and 194 passed.
- The dominant backend failure is test-state contamination: the seeded login
  path receives HTTP 429 from the in-memory auth rate limiter, which then
  cascades into missing session-token assertions and protected-route 401s.
- Alembic `check` reports schema drift across indexes, foreign keys, nullable
  metadata, and defaults. This is a release blocker until reconciled with a
  reviewed additive migration or an explicitly verified baseline.
- Docker and container integration could not be executed because Docker is not
  installed in the current environment.

### Security and tenancy

- The code uses a `DEFAULT_GLOBAL_WORKSPACE_ID` for legacy/unassigned
  investigations and several list/query routes include `workspace_id IS NULL`
  when that workspace is available. This may be intentional compatibility
  behavior, but it requires adversarial verification before a 1.0 claim.
- Route-level authorization coverage is broad but must be tested endpoint by
  endpoint, especially exports, SSE, graph expansion, jobs, autonomous
  workflows, and resources addressed by generic target IDs.
- Provider and retrieval SSRF controls exist in the architecture, but no
  production browser/container run was possible in this audit.
- Password reset currently returns a reset token in the API response for
  development/testing. This must be confirmed as non-production behavior and
  prevented from leaking in production.

### Scientific integrity

- The code contains the foundations for evidence verification, source
  credibility, study independence, methodology audit, gaps, hypotheses, and
  contradiction intelligence. End-to-end M13 validation has not yet proven
  that discovery opportunities are publication-checked, counterexample-checked,
  independently corroborated, and clearly labeled as preliminary.
- Full-text, abstract-only, metadata-only, and document-version provenance
  exists, but report/export consistency across every route remains unverified.
- Benchmark datasets and services exist, but NVIDIA and Nokia comparison runs
  have not been executed and compared during this audit.

### UI/UX

- The application has broad route coverage and a coherent dark brand shell, but
  the shell uses substantial inline styling and emoji-like text icons rather
  than a documented shared design-token/component system.
- Nine frontend lint warnings identify missing React Hook dependencies. They are
  not build failures, but they can cause stale data or effects and must be
  resolved before release.
- Real browser interaction, responsive behavior, accessibility, console
  errors, network failures, and screenshots have not been verified.

## 4. Recommended implementation order

1. Fix test invocation and isolate/reset rate-limit state; record a green or
   precisely bounded backend baseline.
2. Reconcile Alembic drift without destructive schema changes and verify both
   SQLite and PostgreSQL metadata.
3. Complete an adversarial workspace/RBAC/SSE/export/provider security pass.
4. Run existing M8–M12 discovery, hypothesis, contradiction, reproducibility,
   and benchmark services with persisted fixtures; implement only verified gaps.
5. Establish a shared UI design system and remove route-level interaction,
   loading, error, and accessibility defects.
6. Measure before optimizing worker, database, SSE, graph, and frontend costs.
7. Validate Docker, PostgreSQL, Redis, backup/restore, restart recovery, and
   real localhost browser workflows.
8. Produce release documentation only from recorded PASS/PARTIAL/FAIL evidence.

## 5. M13 implementation plan

M13 should not be treated as a single rewrite. The next implementation phase is
blocker remediation and audit completion. After that, autonomous discovery will
be integrated around the existing gap/hypothesis/contradiction/workflow
services, then the UI will be standardized around shared components and actual
data. Security, scientific integrity, API completeness, performance,
deployment, browser validation, and release documentation will follow as
separate measured phases.

## 6. Initial release assessment

NEOMON is a substantial research-intelligence prototype with broad M10–M12
functionality, not yet a release-ready 1.0. The strongest existing foundations
are the evidence/provenance model, provider abstraction, research retrieval,
multi-agent analysis persistence, collaboration/RBAC services, reproducibility
models, and worker/backup scaffolding. They should be audited and hardened,
not rewritten.

Current M13 status: **BLOCKED for release work** until the backend test
baseline, migration drift, tenancy edge cases, deployment validation, and real
browser verification are addressed.
