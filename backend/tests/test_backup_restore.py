"""Tests for Backup, Disaster Recovery, Verification, and Pruning."""

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
import pytest

from app.ops.backup import (
    create_backup,
    verify_backup,
    restore_backup,
    prune_backups,
    calculate_sha256,
)


@pytest.fixture
def sample_sqlite_db():
    """Fixture providing a populated test SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT)")
    cur.execute("CREATE TABLE workspaces (id TEXT PRIMARY KEY, name TEXT)")
    cur.execute("CREATE TABLE investigations (id TEXT PRIMARY KEY, title TEXT)")
    cur.execute("CREATE TABLE sources (id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE evidence (id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE claims (id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE background_jobs (id TEXT PRIMARY KEY)")

    cur.execute("INSERT INTO users VALUES ('u1', 'test@neomon.ai')")
    cur.execute("INSERT INTO users VALUES ('u2', 'audit@neomon.ai')")
    cur.execute("INSERT INTO workspaces VALUES ('w1', 'Quantum Workspace')")
    cur.execute("INSERT INTO investigations VALUES ('inv1', 'Superconductivity Analysis')")
    conn.commit()
    conn.close()

    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_backup_creation_and_checksum(sample_sqlite_db):
    """Verify create_backup creates valid tarball and companion sha256 checksum."""
    with tempfile.TemporaryDirectory() as dest_dir:
        res = create_backup(dest_dir, sample_sqlite_db, custom_label="unit_test")
        assert res["status"] == "success"
        archive_file = Path(res["archive_file"])
        checksum_file = Path(res["checksum_file"])

        assert archive_file.exists()
        assert checksum_file.exists()
        assert res["manifest"]["record_counts"]["users"] == 2
        assert res["manifest"]["record_counts"]["workspaces"] == 1
        assert res["manifest"]["record_counts"]["investigations"] == 1

        # Checksum inside .sha256 matches actual archive hash
        with open(checksum_file, "r") as f:
            stored_hash = f.read().split()[0].strip()
        assert stored_hash == res["sha256"]
        assert calculate_sha256(archive_file) == stored_hash


def test_backup_verification_and_tamper_detection(sample_sqlite_db):
    """Verify that backup verification detects valid archives and flags tampered files."""
    with tempfile.TemporaryDirectory() as dest_dir:
        res = create_backup(dest_dir, sample_sqlite_db)
        archive_path = res["archive_file"]

        # Valid verification
        ver = verify_backup(archive_path)
        assert ver["status"] == "verified"
        assert ver["manifest"]["record_counts"]["users"] == 2

        # Tamper with archive
        with open(archive_path, "ab") as f:
            f.write(b"tamper_bytes_corruption")

        # Must raise ValueError on hash mismatch
        with pytest.raises(ValueError) as exc_info:
            verify_backup(archive_path)
        assert "Checksum mismatch" in str(exc_info.value)


def test_backup_restoration(sample_sqlite_db):
    """Verify restoring from archive creates a working database with matching records."""
    with tempfile.TemporaryDirectory() as dest_dir:
        res = create_backup(dest_dir, sample_sqlite_db)
        archive_path = res["archive_file"]

        target_restore = Path(dest_dir) / "restored_production.db"
        rest = restore_backup(archive_path, str(target_restore))
        assert rest["status"] == "restored"
        assert target_restore.exists()
        assert rest["verified_counts"]["users"] == 2
        assert rest["verified_counts"]["workspaces"] == 1
        assert rest["verified_counts"]["investigations"] == 1

        # Query restored database directly
        conn = sqlite3.connect(str(target_restore))
        cur = conn.cursor()
        cur.execute("SELECT email FROM users ORDER BY email")
        emails = [r[0] for r in cur.fetchall()]
        conn.close()
        assert emails == ["audit@neomon.ai", "test@neomon.ai"]


def test_backup_pruning():
    """Verify pruning removes archives older than retention threshold."""
    with tempfile.TemporaryDirectory() as dest_dir:
        dest_path = Path(dest_dir)
        old_archive = dest_path / "neomon_backup_20200101_000000.tar.gz"
        old_checksum = dest_path / "neomon_backup_20200101_000000.tar.gz.sha256"
        old_archive.write_bytes(b"old")
        old_checksum.write_text("old")

        # Set old mtime (e.g. 100 days ago)
        old_time = 1577836800  # 2020-01-01
        os.utime(old_archive, (old_time, old_time))
        os.utime(old_checksum, (old_time, old_time))

        new_archive = dest_path / "neomon_backup_20261114_120000.tar.gz"
        new_archive.write_bytes(b"new")

        pruned = prune_backups(dest_dir, retention_days=30)
        assert old_archive.name in pruned["deleted_files"]
        assert old_checksum.name in pruned["deleted_files"]
        assert new_archive.name in pruned["retained_files"]
        assert not old_archive.exists()
        assert new_archive.exists()
