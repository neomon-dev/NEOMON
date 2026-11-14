"""Backup and Disaster Recovery CLI and service for NEOMON."""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("neomon.ops.backup")


def calculate_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def count_sqlite_records(db_path: Path) -> Dict[str, int]:
    """Inspect and return record counts of critical tables in SQLite database."""
    counts = {}
    tables = [
        "users",
        "workspaces",
        "investigations",
        "sources",
        "evidence",
        "claims",
        "background_jobs",
    ]
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[t] = 0
        conn.close()
    except Exception as e:
        logger.warning(f"Could not read record counts from {db_path}: {e}")
    return counts


def create_backup(
    destination_dir: str,
    db_source_path: Optional[str] = None,
    custom_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a verified, timestamped tar.gz backup archive with sha256 checksum."""
    dest_path = Path(destination_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    if not db_source_path:
        # Default to local neomon.db
        candidates = [
            Path("backend/neomon.db"),
            Path("neomon.db"),
            Path("app.db"),
        ]
        db_source_path = next((str(c) for c in candidates if c.exists()), None)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    label_suffix = f"_{custom_label}" if custom_label else ""
    archive_name = f"neomon_backup_{timestamp}{label_suffix}.tar.gz"
    archive_path = dest_path / archive_name
    checksum_path = dest_path / f"{archive_name}.sha256"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        stage_dir = tmp_path / "stage"
        stage_dir.mkdir()

        # Database backup snapshot
        counts = {}
        db_snapshot_name = "database.sqlite3"
        if db_source_path and Path(db_source_path).exists():
            src = Path(db_source_path)
            dst = stage_dir / db_snapshot_name
            # Safe SQLite backup
            try:
                src_conn = sqlite3.connect(str(src))
                dst_conn = sqlite3.connect(str(dst))
                src_conn.backup(dst_conn)
                dst_conn.close()
                src_conn.close()
            except Exception:
                shutil.copy2(src, dst)
            counts = count_sqlite_records(dst)
        else:
            # Placeholder for PostgreSQL or empty state
            with open(stage_dir / "database.meta", "w") as f:
                f.write("Target PostgreSQL snapshot configuration")

        manifest = {
            "backup_id": f"backup-{timestamp}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "neomon_version": "0.1.0",
            "database_type": "sqlite3" if db_source_path else "postgresql",
            "record_counts": counts,
        }

        with open(stage_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create tar.gz
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in stage_dir.iterdir():
                tar.add(item, arcname=item.name)

    # Compute checksum
    checksum = calculate_sha256(archive_path)
    with open(checksum_path, "w") as f:
        f.write(f"{checksum}  {archive_name}\n")

    return {
        "status": "success",
        "archive_file": str(archive_path),
        "checksum_file": str(checksum_path),
        "sha256": checksum,
        "manifest": manifest,
    }


def verify_backup(archive_path_str: str) -> Dict[str, Any]:
    """Verify archive integrity and matching SHA-256 checksum."""
    archive_path = Path(archive_path_str)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    checksum_path = archive_path.parent / f"{archive_path.name}.sha256"
    actual_hash = calculate_sha256(archive_path)

    if checksum_path.exists():
        with open(checksum_path, "r") as f:
            expected_hash = f.read().split()[0].strip()
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(
                f"Checksum mismatch! Expected: {expected_hash}, Actual: {actual_hash}"
            )

    # Validate tar file and manifest
    manifest_data = {}
    with tarfile.open(archive_path, "r:gz") as tar:
        names = tar.getnames()
        if "manifest.json" not in names:
            raise ValueError("Invalid backup archive: manifest.json missing.")
        m_file = tar.extractfile("manifest.json")
        if m_file:
            manifest_data = json.load(m_file)

    return {
        "status": "verified",
        "archive": str(archive_path),
        "sha256": actual_hash,
        "manifest": manifest_data,
        "contents": names,
    }


def restore_backup(archive_path_str: str, target_db_path_str: str) -> Dict[str, Any]:
    """Restore database from verified backup into the target path."""
    verification = verify_backup(archive_path_str)
    archive_path = Path(archive_path_str)
    target_path = Path(target_db_path_str)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=tmp_path)

        db_file = tmp_path / "database.sqlite3"
        if not db_file.exists():
            raise ValueError("No database.sqlite3 found inside archive to restore.")

        # Atomic copy / replace into target
        temp_target = target_path.with_suffix(".tmp_restore")
        shutil.copy2(db_file, temp_target)
        if target_path.exists():
            backup_existing = target_path.with_suffix(f".pre_restore_{int(time.time())}")
            shutil.move(target_path, backup_existing)
        shutil.move(temp_target, target_path)

    # Validate restored database
    counts = count_sqlite_records(target_path)
    return {
        "status": "restored",
        "target_database": str(target_path),
        "verified_counts": counts,
        "manifest": verification["manifest"],
    }


def prune_backups(destination_dir: str, retention_days: int = 30) -> Dict[str, Any]:
    """Delete backups older than retention_days."""
    dest_path = Path(destination_dir)
    if not dest_path.exists():
        return {"deleted_files": [], "retained_files": []}

    now = time.time()
    cutoff_seconds = retention_days * 86400
    deleted = []
    retained = []

    for item in dest_path.iterdir():
        if item.name.startswith("neomon_backup_") and (
            item.name.endswith(".tar.gz") or item.name.endswith(".sha256")
        ):
            file_age = now - item.stat().st_mtime
            if file_age > cutoff_seconds:
                item.unlink()
                deleted.append(item.name)
            else:
                retained.append(item.name)

    return {"deleted_files": deleted, "retained_files": retained}


def main():
    parser = argparse.ArgumentParser(description="NEOMON Backup & Disaster Recovery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a backup archive")
    create_parser.add_argument("--dest", required=True, help="Backup destination directory")
    create_parser.add_argument("--db", default=None, help="Database source path")
    create_parser.add_argument("--label", default=None, help="Custom archive label")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify backup archive integrity")
    verify_parser.add_argument("--archive", required=True, help="Backup archive file path")

    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore database from archive")
    restore_parser.add_argument("--archive", required=True, help="Backup archive file path")
    restore_parser.add_argument("--target-db", required=True, help="Target database path")

    # prune
    prune_parser = subparsers.add_parser("prune", help="Prune old backups")
    prune_parser.add_argument("--dest", required=True, help="Backup destination directory")
    prune_parser.add_argument("--retention-days", type=int, default=30, help="Retention period in days")

    args = parser.parse_args()

    if args.command == "create":
        res = create_backup(args.dest, args.db, args.label)
        print(json.dumps(res, indent=2))
    elif args.command == "verify":
        res = verify_backup(args.archive)
        print(json.dumps(res, indent=2))
    elif args.command == "restore":
        res = restore_backup(args.archive, args.target_db)
        print(json.dumps(res, indent=2))
    elif args.command == "prune":
        res = prune_backups(args.dest, args.retention_days)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
