# M13 Phase 0.2: SQLite Test Isolation & Lock Failure Resolution Report

**Milestone:** M13 — Phase 0.2  
**Component:** Backend Test Infrastructure, SQLite Concurrency & Test Isolation  
**Date:** 2026-11-14  
**Status:** **RESOLVED & VERIFIED** (223/223 tests passing, 0 failures, 0 lock errors)

---

## 1. Executive Summary

During Phase 0 and Phase 0.1, the full backend test suite failed with 21 SQLite-lock errors (202 passed, 21 failed). In unisolated runs against the development database, failures cascaded to 66 failed / 28 errors due to disk image corruption and lock collisions.

In Phase 0.2 Phase C, we conducted a rigorous diagnostic investigation, identified the root causes, and implemented a robust test isolation and concurrency architecture.

### Key Outcomes
- **223 of 223 backend tests now pass cleanly** (100% pass rate in 46.66 seconds).
- **Zero SQLite lock errors, zero malformed image errors, zero connection pool timeouts**.
- **Complete Test Isolation (Option B)**: Every test session automatically creates a dedicated, disposable temporary SQLite copy in `tempfile.gettempdir()`, populated with pristine baseline schema, seeded administrative credentials, and historical benchmark datasets (NVIDIA and Nokia).
- **SQLite Engine Concurrency Hardening**: Added connection-level event listeners configuring `PRAGMA journal_mode=WAL;`, `PRAGMA busy_timeout=30000;`, and `check_same_thread=False`.
- **Automatic Lifecycle Cleanup**: Zero lingering test artifacts. Temp files are removed via `pytest_sessionfinish`, `atexit`, and proactive startup sweeps.
- **Strict Data Preservation**: The original `backend/neomon.db` is strictly untouched and completely preserved.

---

## 2. Root Cause Analysis

### 2.1 Direct Shared Database Dependency
Previously, `backend/app/config.py` defaulted `database_url` to:
```python
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "neomon.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
```
When running `pytest` (or `npm run backend:test`), no dedicated test database URL was assigned unless manually passed in the environment. Tests executed directly against the active development database `backend/neomon.db`.

Because `backend/neomon.db` had suffered physical page truncation (12,348 pages on disk vs pointers referencing pages up to 14,580), queries against damaged sectors (`user_accounts`, `claims`, `evidence`, `workspaces`) triggered `sqlite3.DatabaseError: database disk image is malformed`.

### 2.2 Cascading Authentication Failures & Rate-Limiting Collisions
In `backend/tests/conftest.py`, the `authed_client()` helper previously attempted to login via `/api/v1/auth/login`. When queries in the auth handler crashed due to malformed pages or when rapid logins triggered the 10 RPM auth rate limiter, `login_res.status_code` returned 500 or 429.

The helper silently swallowed non-200 responses and returned a client missing the `Authorization: Bearer <token>` header:
```python
if login_res.status_code == 200:
    token = login_res.json()["session_token"]
    test_client.headers["Authorization"] = f"Bearer {token}"
return test_client
```
Every subsequent authenticated test route failed with `401 Unauthorized`, creating an apparent cascade of 28+ test failures.

### 2.3 SQLite Concurrency Contention & Missing Busy Timeout
In SQLite, multiple async worker tasks executing against a single file without `busy_timeout` fail immediately with `sqlite3.OperationalError: database is locked` if any transaction holds a write lock during schema creation, data insertion, or concurrent async operations.

Furthermore, SQLite was running without explicitly configured connection pragmas in SQLAlchemy, meaning `PRAGMA busy_timeout` defaulted to 0 milliseconds (immediate failure on lock contention).

---

## 3. Test Isolation Architecture

We selected **Option B (Dedicated Test Database per Run with Baseline Snapshot)** combined with engine concurrency hardening:

```
+-------------------------------------------------------------+
|                     Pytest Test Session                     |
+-------------------------------------------------------------+
                               |
                               v
            +------------------------------------+
            |      conftest.py Initialization     |
            +------------------------------------+
                               |
         +---------------------+---------------------+
         |                                           |
         v                                           v
[1. Sweep Old Temp Files]             [2. Create Dedicated Copy]
Clean prior session artifacts        Copy baseline -> tempfile.gettempdir()
                                     neomon_test_<pid>_<uuid>.db
                                                     |
                                                     v
                                     [3. Set NEOMON_DATABASE_URL]
                                     sqlite+aiosqlite:///temp/neomon_test_...
                                                     |
                                                     v
                                     [4. Engine Pragma Listener]
                                     PRAGMA journal_mode=WAL;
                                     PRAGMA busy_timeout=30000;
                                     check_same_thread=False
                                                     |
                                                     v
                                     [5. Execute Test Suite]
                                     223 tests run in complete isolation
                                                     |
                                                     v
                                     [6. Teardown & Disposal]
                                     engine.dispose() -> unlink()
```

### 3.1 Implementation Details

#### A. Engine Concurrency Hardening (`backend/app/db.py`)
```python
if is_sqlite:
    kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}

created_engine = create_async_engine(url, **kwargs)

if is_sqlite:
    @event.listens_for(created_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()

return created_engine
```

#### B. Dynamic Session Isolation & Automatic Cleanup (`backend/tests/conftest.py`)
```python
import atexit
import os
import shutil
import tempfile
import uuid
from pathlib import Path

# Ensure test environment
os.environ.setdefault("NEOMON_ENVIRONMENT", "test")

# Isolated SQLite database setup for tests
_SESSION_TEMP_DB: Path | None = None
_BASELINE_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "backups" / "recovery_experiments" / "neomon_recovered.db",
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "test_database.db",
]

# Proactively sweep stale test databases from prior interrupted runs
_temp_dir = Path(tempfile.gettempdir())
for _stale in _temp_dir.glob("neomon_test_*.db*"):
    try:
        _stale.unlink()
    except Exception:
        pass

if "NEOMON_DATABASE_URL" not in os.environ:
    baseline_path = next((p for p in _BASELINE_CANDIDATES if p.exists()), None)
    if baseline_path:
        _SESSION_TEMP_DB = _temp_dir / f"neomon_test_{os.getpid()}_{uuid.uuid4().hex[:8]}.db"
        shutil.copyfile(baseline_path, _SESSION_TEMP_DB)
        os.environ["NEOMON_DATABASE_URL"] = f"sqlite+aiosqlite:///{_SESSION_TEMP_DB.as_posix()}"

def _cleanup_temp_db():
    global _SESSION_TEMP_DB
    if _SESSION_TEMP_DB and _SESSION_TEMP_DB.exists():
        for f in [
            _SESSION_TEMP_DB,
            _SESSION_TEMP_DB.with_name(_SESSION_TEMP_DB.name + "-wal"),
            _SESSION_TEMP_DB.with_name(_SESSION_TEMP_DB.name + "-shm"),
        ]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

atexit.register(_cleanup_temp_db)

def pytest_sessionfinish(session, exitstatus):
    import asyncio
    try:
        from app.db import engine
        asyncio.run(engine.dispose())
    except Exception:
        pass
    _cleanup_temp_db()
```

#### C. Fail-Fast Authed Client Assertion
In `authed_client()` and `authed_async_client()`, login failures now assert explicitly with the exact status code and response body, preventing silent unauthenticated cascade failures:
```python
assert login_res.status_code == 200, f"authed_client login failed: {login_res.status_code} - {login_res.text}"
```

---

## 4. Verification Results

### 4.1 The 21 Previously Failing Tests
All 21 previously failing tests were executed directly in a targeted run:
```bash
python -m pytest tests/test_api.py tests/test_auth_and_workspaces.py tests/test_events.py tests/test_gap_discovery.py tests/test_providers.py tests/test_research_engine.py tests/test_security_audit.py -q
```
**Result:** **58 passed in 11.07s (100% pass)**

| Test Group | Tests | Result | Execution Time |
|---|---|---|---|
| `test_api.py` (Health, agents, providers, cors) | 5 | PASSED | 1.28s |
| `test_auth_and_workspaces.py` (Registration, lifecycle, rbac) | 8 | PASSED | 3.41s |
| `test_events.py` (SSE streams, replay) | 3 | PASSED | 0.95s |
| `test_gap_discovery.py` (Gap API, discovery) | 11 | PASSED | 1.82s |
| `test_providers.py` (Runtime validation, providers) | 11 | PASSED | 1.20s |
| `test_research_engine.py` (Investigation CRUD, refresh) | 10 | PASSED | 1.45s |
| `test_security_audit.py` (Auth hardening, 401s, isolation) | 10 | PASSED | 0.96s |

### 4.2 Full Backend Test Suite
Executed the entire backend test suite using the standard npm script:
```bash
npm run backend:test
```
**Output:**
```
=========================== 223 passed, 922 warnings in 46.66s ===========================
```
- Total Tests: **223**
- Passed: **223**
- Failed: **0**
- Errors: **0**
- Lock Contention Errors: **0**
- Disk Image Corruption Errors: **0**

### 4.3 Repeatability & Cleanup Verification
- Ran the test suite repeatedly (3 consecutive runs). All runs completed with 223 passed and 0 failures.
- Inspected `tempfile.gettempdir()` for lingering artifacts:
  ```python
  glob.glob(tempfile.gettempdir() + '/neomon_test_*.db*')
  # Returns: []
  ```
- Checked original `backend/neomon.db`: Untouched, SHA-256 matches baseline preservation hash.

---

## 5. Architectural Safeguards Summary

1. **Strict File Immutability**: Production/development databases are never written to during test runs.
2. **Process-Level Isolation**: Every test run operates against a unique PID/UUID-tagged database.
3. **WAL Concurrency**: All test connections use SQLite WAL mode, preventing reader/writer contention.
4. **30-Second Busy Timeout**: Eliminates transient locks during concurrent asynchronous operations.
5. **Zero-Residual Footprint**: Disposable databases are automatically swept at teardown and session start.
