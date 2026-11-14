# NEOMON Backup & Disaster Recovery Guide

NEOMON provides an operational backup and disaster recovery utility (`app.ops.backup`) capable of snapshotting database state, computing cryptographic checksums, verifying integrity, restoring snapshots, and pruning aged archives.

---

## 1. Creating a Backup

### Using the CLI
```bash
python -m app.ops.backup create --dest /var/backups/neomon --db backend/neomon.db --label daily
```

### Output Artifacts
1. **Archive Tarball**: `/var/backups/neomon/neomon_backup_YYYYMMDD_HHMMSS_daily.tar.gz`
2. **SHA-256 Checksum**: `/var/backups/neomon/neomon_backup_YYYYMMDD_HHMMSS_daily.tar.gz.sha256`

Inside the archive:
- `database.sqlite3`: Consistent snapshot of the database file.
- `manifest.json`: Metadata with timestamp, software version, and record counts for all core entities (`users`, `workspaces`, `investigations`, `evidence`, `claims`, `background_jobs`).

---

## 2. Verifying Backup Integrity

Always verify backups after generation or transfer:
```bash
python -m app.ops.backup verify --archive /var/backups/neomon/neomon_backup_YYYYMMDD_HHMMSS_daily.tar.gz
```
Returns JSON verification payload with confirmation of matching checksum and manifest structure.

---

## 3. Restoring from a Backup

To restore an archive into a target database path:
```bash
python -m app.ops.backup restore \
  --archive /var/backups/neomon/neomon_backup_YYYYMMDD_HHMMSS_daily.tar.gz \
  --target-db backend/neomon.db
```

The restore process:
1. Re-verifies archive checksum and tar validity.
2. Extracts contents to a protected temporary directory.
3. Creates a timestamped safety backup of the existing target database (e.g. `neomon.db.pre_restore_<timestamp>`).
4. Atomically replaces target database with the snapshot.
5. Runs verification queries on the target database, returning validated table record counts.

---

## 4. Retention & Pruning

Automated cleanup of archives older than a specified retention policy:
```bash
python -m app.ops.backup prune --dest /var/backups/neomon --retention-days 30
```

---

## 5. Automated Backup Schedule (Cron Example)

Add to system crontab (`crontab -e`):
```cron
# Daily backup at 02:00 AM UTC
0 2 * * * cd /opt/neomon && /opt/neomon/venv/bin/python -m app.ops.backup create --dest /var/backups/neomon --label cron >> /var/log/neomon_backup.log 2>&1

# Prune archives older than 30 days every Sunday at 03:00 AM UTC
0 3 * * 0 cd /opt/neomon && /opt/neomon/venv/bin/python -m app.ops.backup prune --dest /var/backups/neomon --retention-days 30 >> /var/log/neomon_backup.log 2>&1
```
