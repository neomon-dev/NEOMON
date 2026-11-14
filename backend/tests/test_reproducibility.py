"""Tests for Research Execution Manifest and Reproducibility Service (Milestone 12)."""

import hashlib
import json
import uuid
import pytest
from app.db import SessionFactory
from app.models import Investigation, Source, Evidence, User
from app.research.reproducibility_service import ReproducibilityService, sanitize_sensitive_config


def test_sanitize_sensitive_credentials():
    """Verify that API keys, secrets, tokens, and passwords are comprehensively redacted."""
    raw_config = {
        "model": "gpt-4o",
        "api_key": "sk-proj-verysecretkey123456789",
        "provider_token": "token_abc_xyz",
        "auth_header": "Bearer secret_jwt",
        "nested": {
            "password": "SuperSecretPassword!",
            "database_url": "postgresql://user:pass@localhost/db",
            "temperature": 0.2,
        },
    }
    sanitized = sanitize_sensitive_config(raw_config)
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["provider_token"] == "***REDACTED***"
    assert sanitized["auth_header"] == "***REDACTED***"
    assert sanitized["nested"]["password"] == "***REDACTED***"
    assert sanitized["nested"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_reproducibility_manifest_creation_and_integrity():
    """Verify manifest generation, cryptographic SHA-256 hash calculation, and tamper verification."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="What are the biochemical pathways of cellular senescence?",
            mode="deep",
            status="completed",
        )
        session.add(inv)
        src = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Cellular Aging Review",
            canonical_url="https://nature.com/articles/aging-1",
            original_url="https://nature.com/articles/aging-1",
            source_type="academic",
        )
        session.add(src)
        ev = Evidence(
            id=uuid.uuid4(),
            source_id=src.id,
            exact_text="p16INK4a activation initiates senescence growth arrest.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)
        await session.commit()

        service = ReproducibilityService(session)
        manifest = await service.generate_manifest(inv_id)
        assert manifest.manifest_hash is not None
        assert len(manifest.manifest_hash) == 64  # SHA-256 hex string

        # Verify integrity
        integrity = await service.verify_manifest_integrity(manifest.id)
        assert integrity["is_tamper_free"] is True
        assert integrity["status"] == "verified"

        # Tamper with stored manifest content
        manifest.research_question = "Tampered unauthorized question text"
        await session.commit()

        tampered_integrity = await service.verify_manifest_integrity(manifest.id)
        assert tampered_integrity["is_tamper_free"] is False
        assert tampered_integrity["status"] == "tampered"


@pytest.mark.asyncio
async def test_reproduction_run_spawns_new_linked_investigation():
    """Verify that reproduction attempts spawn a new investigation linked to parent without overwriting original."""
    inv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="High-temperature superconducting cuprate mechanisms",
            mode="deep",
            status="completed",
        )
        session.add(inv)
        user = User(id=user_id, email=f"repro_researcher_{uuid.uuid4().hex[:6]}@neomon.ai", password_hash="hash", display_name="Dr. Reproducer", role="researcher")
        session.add(user)
        await session.commit()

        service = ReproducibilityService(session)
        reproduced_inv = await service.reproduce_investigation_run(inv_id, user_id)
        assert reproduced_inv.id != inv_id
        assert "[Reproduction]" in reproduced_inv.question
        assert reproduced_inv.owner_id == user_id

        # Verify original investigation was untouched
        original_check = await session.get(Investigation, inv_id)
        assert original_check.question == "High-temperature superconducting cuprate mechanisms"
        assert original_check.status == "completed"

        # Verify child manifest has parent link
        child_manifest = await service.get_latest_manifest(reproduced_inv.id)
        assert child_manifest is not None
        parent_manifest = await service.get_latest_manifest(inv_id)
        assert child_manifest.parent_reproduced_manifest_id == parent_manifest.id
