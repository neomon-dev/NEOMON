# NEOMON 1.0 — Production Backup & Disaster Recovery Guide

**Document Purpose:** Standard Operating Procedures (SOP) for Database Backup, Integrity Verification, and Disaster Recovery for NEOMON 1.0 Production Deployments.  
**Target Database:** Managed PostgreSQL 16+  
**Target Hosting:** Render Postgres (or AWS RDS / Neon / Supabase)  

---

## 1. Backup Strategy Overview

NEOMON relies on PostgreSQL as its authoritative state store. The production backup strategy operates at three distinct levels:

1. **Automated Cloud Provider Daily Backups:**  
   Managed PostgreSQL instances (e.g. Render Postgres, Neon, AWS RDS) perform continuous Write-Ahead Log (WAL) archiving and automatic daily snapshots with 7 to 30 days of retention.
2. **Logical Database Dumps (`pg_dump`):**  
   Scheduled logical exports of schema and data executed before every major software upgrade or schema migration.
3. **Application State Archival (`app/ops/backup.py`):**  
   Integrated snapshot and metadata export utility for research investigations and audit logs.

---

## 2. On-Demand Logical Backup Procedure (`pg_dump`)

Prior to performing manual database maintenance or deploying new major versions:

### Step 1: Capture Logical Dump
From an authorized administrative terminal with PostgreSQL client tools:
```bash
pg_dump "$DATABASE_URL" \
    --format=custom \
    --compress=9 \
    --file="neomon_backup_$(date +%Y%m%d_%H%M%S).dump"
```

* Flags explained:
  - `--format=custom` (`-Fc`): Produces a compressed, flexible binary archive compatible with `pg_restore`.
  - `--compress=9`: Maximum zlib compression to minimize storage and transfer time.
  - `--file=...`: Generates a timestamped archive file.

### Step 2: Generate Cryptographic Integrity Checksum
```bash
sha256sum "neomon_backup_"*.dump > "neomon_backup_"*.dump.sha256
```

---

## 3. Full Database Restoration Procedure (`pg_restore`)

In the event of data corruption, accidental deletion, or disaster recovery:

### Step 1: Verify Checksum
```bash
sha256sum -c "neomon_backup_YYYYMMDD_HHMMSS.dump.sha256"
```

### Step 2: Terminate Existing Application Connections
Ensure no web services or workers are holding active write transactions:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'neomon'
  AND pid <> pg_backend_pid();
```

### Step 3: Execute Restoration
To restore into a fresh database or overwrite existing tables:
```bash
pg_restore \
    --dbname="$DATABASE_URL" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --verbose \
    "neomon_backup_YYYYMMDD_HHMMSS.dump"
```

* Flags explained:
  - `--clean`: Drops existing database objects before recreating them.
  - `--if-exists`: Avoids errors when dropping objects that do not exist in the target database.
  - `--no-owner`: Prevents permission failures caused by differences in database role names across cloud environments.
  - `--no-privileges`: Skips restoring access privileges, preserving target database role configurations.

### Step 4: Run Post-Restore Migration & Integrity Checks
```bash
cd backend
python -m alembic check
python -m pytest tests/test_database_postgres.py -v
```

---

## 4. Disaster Recovery & Rollback Runbook

### Scenario A: Unsuccessful Schema Migration during Deployment
If `python -m alembic upgrade head` fails during the Render Pre-Deploy Command:
1. Render automatically halts the deployment and keeps the previous healthy version running.
2. Inspect the build log to identify the constraint or syntax issue.
3. If necessary, downgrade the schema:
   ```bash
   python -m alembic downgrade -1
   ```

### Scenario B: Database Instance Outage / Provider Failure
1. Provision a new PostgreSQL instance in an alternate region or provider.
2. Restore the latest verified `.dump` file using the Step 3 restoration command above.
3. Update `NEOMON_DATABASE_URL` in the Render Web Service dashboard with the new database URL.
4. Trigger a redeploy of `neomon-api`.
5. Verify health via `GET /api/v1/ready`.

---

## 5. Local Development SQLite to Production PostgreSQL Migration

* **Crucial Rule:** The local SQLite database (`backend/neomon.db`) must **never** be copied directly to production. SQLite and PostgreSQL have fundamentally different concurrency models, locking primitives, and data representations.
* **Production Initialization:** When initializing the production PostgreSQL database, always start with:
  ```bash
  cd backend && python -m alembic upgrade head
  ```
  This applies all 16 migrations in their exact canonical sequence, creating all 50+ tables, indexes, unique constraints, and foreign key cascades natively in PostgreSQL.
