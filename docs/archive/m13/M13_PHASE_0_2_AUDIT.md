# NEOMON M13 Phase 0.2 Audit & Handoff Report

**Date:** 2026-11-14  
**Auditor:** Google Antigravity  
**Branch:** `main` (uncommitted working tree preserved)  
**Status:** In Progress (Phase 0.2)

---

## 1. Current Repository State

- **Branch**: `main`
- **Working Tree**: No commits or pushes made.
- **Modified files**:
  - `backend/app/models.py`: Added explicit `nullable=False` to `ReportVersion.created_at`, `ResearchGapAnalysis.created_at`, and `ResearchGap.created_at`. Added `index=True` to `ReviewRequest.status`.
  - `backend/app/routers/autonomous_workflows.py`: Removed implicit global workspace fallback for unauthenticated/unassigned listings (`return []` if user has no workspaces).
  - `backend/app/routers/graph.py`: Removed implicit global fallback for unassigned users (`return InvestigationGraphResponse(nodes=[], edges=[])`).
  - `backend/app/routers/quality_audit.py`: Removed implicit global fallback (`return []` if user has no workspaces).
  - `backend/app/routers/workspace.py`: Removed implicit global fallback in `read_agent_observatory` (`return AgentObservatoryResponse(executions=[], executions_total=0)`).
  - `backend/tests/test_security_audit.py`: Added `test_users_without_global_membership_cannot_read_legacy_global_data`.
  - `package.json`: Updated `backend:test` script to execute from `backend/` directory with `NEOMON_ENVIRONMENT=test`.
- **Untracked files**:
  - `M13_INITIAL_AUDIT.md`, `M13_PROGRESS.md`, `M13_IMPLEMENTATION_LOG.md`, `M13_KNOWN_ISSUES.md`, `M13_DATABASE_REMEDIATION_REPORT.md`, `M13_SECURITY_TENANCY_AUDIT.md`, `M13_TEST_REGISTER.md`.
  - `backend/migrations/versions/20261114_0016_schema_alignment.py`.

---

## 2. Independent Review of Copilot's Changes (Phase 0.1)

### Migration `20261114_0016_schema_alignment.py`
- **Scope**: Reconciles ORM metadata with Alembic migration chain.
  - Adds `report_versions` table if absent (or normalizes `created_at` if already created by historical `create_all()`).
  - Adds foreign keys with `SET NULL` on `investigations`:
    - `fk_investigations_workspace_id_workspaces` -> `workspaces.id`
    - `fk_investigations_owner_id_users` -> `users.id`
  - Normalizes 23 legacy index names to match ORM convention.
  - Adds 15 missing indexes across collaboration, query history, notifications, and review requests.
  - Downgrade logic safely retains `report_versions` to prevent historical data loss.
- **Safety Assessment**:
  - The migration logic is sound and non-destructive for clean databases.
  - On the development SQLite database, however, executing `batch_alter_table("investigations", recreate="always")` failed because SQLite triggers full table copy into `_alembic_tmp_investigations`, which encountered pre-existing malformed pages in `neomon.db`.

### Tenancy and Security Fixes
- Copilot eliminated the silent global workspace fallback in unfiltered listing endpoints (`/research/autonomous/workflows`, `/research/graph`, `/research/quality/audits`, `/agents/observatory`).
- Users without explicit workspace memberships now receive empty lists rather than gaining accidental read access to legacy global investigations.
- Regression test `test_users_without_global_membership_cannot_read_legacy_global_data` verified this isolation.

---

## 3. Outstanding Defects & Critical Blockers

1. **Development SQLite Database (`backend/neomon.db`)**:
   - File size: 50,577,408 bytes (50.5 MB), WAL: 6,023,472 bytes (6 MB), SHM: 32,768 bytes.
   - Reports `malformed` pages upon integrity inspection.
   - Preserved byte-for-byte in `backend/backups/raw_preservation_20261114_phase02/` before any recovery actions.
2. **21 SQLite Database-Lock Failures in Full Test Suite**:
   - The test suite contains 222 tests total.
   - In clean runs without isolated test databases, 21 tests fail with `sqlite3.OperationalError: database is locked`.
   - Root cause must be investigated (connection leaks, long-lived sessions, uncheckpointed WAL, or shared file-backed database access).
3. **Security Closure**:
   - Complete horizontal and vertical RBAC verification across all 5 roles (`viewer`, `reviewer`, `researcher`, `admin`, `owner`).
   - Audit IDOR protection on direct resource identifiers and SSE channels.
4. **Environment Limitations**:
   - Docker daemon is not installed in the current environment; containerized PostgreSQL and Redis remain explicitly marked **NOT TESTED**.

---

## 4. Exact Next Actions

1. **Phase B**: Safely diagnose and investigate `backend\backups\recovery_experiments\neomon_experiment.db` using read-only SQLite pragma checks, attempt table-by-table extraction, and produce `M13_SQLITE_RECOVERY_REPORT.md` (Outcome A, B, or C).
2. **Phase C**: Diagnose and resolve the 21 SQLite-lock test failures through proper session lifecycle, connection disposal, and isolated test database fixtures; produce `M13_SQLITE_TEST_ISOLATION_REPORT.md`.
3. **Phase D**: Conduct complete security audit across authentication, workspace isolation, global workspace policy, role permissions, background jobs, and SSE; produce `M13_PHASE_0_2_SECURITY_REPORT.md`.
4. **Phase E & F**: Start actual backend/frontend on localhost, run browser verification, and execute full regression gates.
5. **Phase G**: Update all tracking documentation and evaluate Phase 0.2 Exit Gate.
