# NEOMON M13 SQLite Database Corruption & Recovery Report

**Date:** 2026-11-14  
**Investigator:** Google Antigravity  
**Database File:** `backend/neomon.db` (and `neomon.db-wal`, `neomon.db-shm`)  
**Safety Protocol:** Read-Only Original Inspection; All Recovery Experiments Conducted on Isolated Copies  
**Outcome Decision:** **Outcome B — Partially Recovered (Original Strictly Preserved)**

---

## 1. Executive Summary

During Phase 0.1, the development SQLite database (`backend/neomon.db`) failed Alembic migration upgrade due to reported malformed pages during batch alter operations.

In Phase 0.2, an exhaustive read-only diagnostic and experimental recovery investigation was conducted in strict adherence to data safety rules:
1. **Preservation**: The original database files (`neomon.db`, `neomon.db-wal`, `neomon.db-shm`) were preserved byte-for-byte in `backend/backups/raw_preservation_20261114_phase02/` and verified with matching SHA-256 hashes (`FDA90EFE4288A2A76...`).
2. **Diagnosis**: `PRAGMA quick_check` and `PRAGMA integrity_check` on the isolated experiment copy revealed that internal B-tree interior nodes reference page numbers ranging from 12,432 to 14,580, whereas the physical database file size is exactly 50,577,408 bytes ($12,348 \times 4096$ byte pages).
3. **Root Cause**: Structural page-level truncation. Uncheckpointed WAL frames from prior abrupt process terminations left B-tree pointers referencing pages beyond the physical file boundary.
4. **Recovery Outcome**: Reconstructed an isolated clean database (`neomon_recovered.db`) in `backend/backups/recovery_experiments/` by extracting all unaffected tables and recovering thousands of intact records from damaged tables via resilient rowid scanning. `neomon_recovered.db` passes `PRAGMA integrity_check` with `ok`.
5. **Preservation Guarantee**: In compliance with the Absolute Safety Rules, the original database `backend/neomon.db` has **NOT** been overwritten, dropped, stamped, or mutated.

---

## 2. Diagnostic Investigation (Without Altering Original)

### 2.1 File & Environment Metadata
- **Database Path**: `backend/neomon.db`
- **File Size**: 50,577,408 bytes (~50.5 MB)
- **Associated Files**:
  - `backend/neomon.db-wal`: 6,023,472 bytes (~6.0 MB)
  - `backend/neomon.db-shm`: 32,768 bytes (32 KB)
- **SQLite Library Version**: 3.50.4 (via Python 3.14.7 `sqlite3`)
- **Page Size**: 4,096 bytes
- **Page Count in Main DB Header**: 12,348 pages
- **Freelist Page Count**: 21 pages
- **Journal Mode**: `wal`

### 2.2 Integrity & Pragma Diagnostics
When inspected in read-only URI mode (`file:...?mode=ro`), `PRAGMA quick_check` and `PRAGMA integrity_check` returned errors:

```text
*** in database main ***
Tree 11526 page 11526 cell 0: invalid page number 13795
Tree 11526 page 11526 cell 3: invalid page number 12991
Tree 6707 page 6707 cell 0: invalid page number 14563
Tree 6707 page 6707 cell 41: invalid page number 13790
Tree 6707 page 6707 cell 40: invalid page number 13783
Tree 6707 page 6707 cell 39: invalid page number 13746
Tree 6707 page 6707 cell 38: invalid page number 13027
Tree 6711 page 6711 cell 0: invalid page number 13791
Tree 6710 page 6710 cell 3: invalid page number 13025
Tree 6708 page 6708 cell 3: invalid page number 13786
Tree 6681 page 6681 cell 0: invalid page number 13758
Tree 6664 page 6664 cell 0: invalid page number 14564
Tree 3705 page 3705 cell 0: invalid page number 13032
Tree 2167 page 2167 cell 0: invalid page number 14580
...
Tree 2154 page 12083 cell 12: invalid page number 12491
Tree 2154 page 12083 cell 408: invalid page number 12490
```

### 2.3 Diagnostic Root-Cause Classification
- **Classification**: **Structural Page-Level Truncation & WAL Desynchronization**.
- **Explanation**: The B-tree index and table nodes reference pages up to page 14,580. A database of 14,580 pages would measure $14,580 \times 4096 = 59,719,680$ bytes (~59.7 MB). The file on disk is only 50.5 MB.
- **Trigger**: Occurs when concurrent processes write to SQLite in WAL mode and an unexpected process termination (or test runner crash) prevents uncheckpointed WAL frames from merging back into the primary database file.

---

## 3. Table-Level Impact Analysis

The database contains 68 application tables in `sqlite_master`.
Diagnostic inspection revealed two distinct categories:

### 3.1 Completely Intact Tables (60 Tables)
Tables whose B-trees are entirely within the first 12,348 pages:
- `investigations`: 1,669 records (including historical NVIDIA and Nokia benchmarks)
- `sources`: 1,286 records
- `documents`: 352 records
- `users`: 371 records
- `analysis_jobs`: 338 records
- `analysis_agent_executions`: 1,359 records
- `agent_arguments`: 1,356 records
- `debate_rounds`: 188 records
- `adjudication_decisions`: 239 records
- `research_events`: 2,935 records
- `research_gap_analyses`: 375 records
- `research_gaps`: 1,324 records
- `research_hypotheses`: 143 records
- `hypothesis_evaluations`: 73 records
- `research_trend_analyses`: 45 records
- `research_trend_topics`: 360 records
- `autonomous_research_workflows`: 94 records
- `research_workflow_cycles`: 54 records
- `research_workflow_checkpoints`: 140 records
- `evidence_verification_records`: 156 records
- `study_independence_clusters`: 76 records
- `methodology_audit_findings`: 57 records
- `research_execution_manifests`: 11 records
- `benchmark_datasets`: 10 records
- `benchmark_runs`: 16 records
- `human_evidence_corrections`: 14 records
- `report_versions`: 42 records
- `claim_evidence_relationships`: 1,054 records
- `open_access_locations`: 908 records
- `document_version_relationships`: 50 records
- `extraction_executions`: 52 records
- `cross_investigation_relationships`: 48 records
- `contradiction_resolution_logs`: 48 records
- `provider_failure_impacts`: 23 records
- `password_reset_tokens`: 31 records
- `comment_threads`: 29 records
- `review_requests`: 29 records
- `review_decisions`: 16 records
- `evidence_annotations`: 18 records
- `research_queries`: 138 records
- `research_query_histories`: 2 records
- `research_workflow_reports`: 3 records
- `alembic_version`: 1 record

### 3.2 Tables with Damaged Trailing B-Tree Pointers (8 Tables)
These tables have valid rowids in lower pages, but full sequential scans fail when attempting to read leaf or overflow pages beyond page 12,348:
- `claims`: 1,069 valid rows recovered.
- `evidence`: 1,458 valid rows recovered.
- `workspaces`: 462 valid rows recovered.
- `workspace_members`: 521 valid rows recovered.
- `user_sessions`: 517 valid rows recovered.
- `research_contradictions`: 16,942 valid rows recovered.
- `notification_preferences`: 319 valid rows recovered.
- `workspace_activities`: 446 valid rows recovered.

---

## 4. Experimental Recovery Results (On Copy)

In `backend/backups/recovery_experiments/neomon_recovered.db`:
- Extracted and recreated all 68 table DDL definitions.
- Recovered 100% of all intact records across all 68 tables.
- Recreated all 146 database indexes cleanly.
- Verified historical benchmarks:
  - NVIDIA AI Era (`97a2bf219f0944119e9e2ec925a5cb08`): Intact.
  - Downfall of Nokia (`9ab9477a33b84535b578eda03a64e254`): Intact.
- Integrity verification of recovered database:
  - `PRAGMA integrity_check` -> `[('ok',)]`
  - `PRAGMA quick_check` -> `[('ok',)]`

---

## 5. Safe Recovery Decision: Outcome B

**Decision: Outcome B — Partially Recovered (Original Preserved)**

### Rationale
- Under the Absolute Safety Rules, a recovery that skips unreadable overflow rows cannot be claimed as "Complete 100% Outcome A" without risk of losing uncommitted edge records.
- Therefore, the safest, most defensible decision is **Outcome B**:
  1. The original database file `backend/neomon.db` (50,577,408 bytes) and WAL files are preserved untouched.
  2. The byte-for-byte baseline backup is preserved in `backend/backups/raw_preservation_20261114_phase02/`.
  3. The verified clean recovered copy is maintained in `backend/backups/recovery_experiments/neomon_recovered.db`.
  4. At no point was the original database overwritten or deleted.
