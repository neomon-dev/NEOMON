"""Tests for Study Independence and Cluster Validation (Milestone 12)."""

import json
import uuid
import pytest
from app.db import SessionFactory
from app.models import Investigation, Source, StudyIndependenceCluster
from app.research.study_independence_service import StudyIndependenceService, IndependenceCategory


@pytest.mark.asyncio
async def test_detect_duplicate_by_doi_and_title():
    """Verify that sources with identical DOIs or near-identical headlines cluster into duplicate_publications."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="CRISPR therapeutics off-target", mode="deep", status="created")
        session.add(inv)

        s1 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Genome-wide off-target profiling of Cas9 nucleases",
            doi="10.1038/nature12345",
            canonical_url="https://nature.com/articles/nature12345",
            original_url="https://nature.com/articles/nature12345",
            source_type="peer_reviewed",
        )
        s2 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Genome-wide off-target profiling of Cas9 nucleases (Reprint)",
            doi="10.1038/nature12345",
            canonical_url="https://europepmc.org/articles/PMC12345",
            original_url="https://europepmc.org/articles/PMC12345",
            source_type="peer_reviewed",
        )
        session.add(s1)
        session.add(s2)
        await session.commit()

        service = StudyIndependenceService(session)
        clusters = await service.analyze_and_persist_clusters(inv_id)
        assert len(clusters) == 1
        c = clusters[0]
        assert c.relationship_category == IndependenceCategory.DUPLICATE_PUBLICATIONS.value
        assert c.confidence >= 0.90
        member_ids = json.loads(c.member_source_ids_json)
        assert len(member_ids) == 2


@pytest.mark.asyncio
async def test_detect_shared_authorship_related_studies():
    """Verify that separate papers sharing multiple authors are clustered as related_studies."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="Transformer attention memory scaling", mode="deep", status="created")
        session.add(inv)

        s1 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
            doi="10.48550/arXiv.2205.14135",
            canonical_url="https://arxiv.org/abs/2205.14135",
            original_url="https://arxiv.org/abs/2205.14135",
            authors_json=json.dumps(["Tri Dao", "Daniel Y. Fu", "Stefano Ermon", "Atri Rudra", "Christopher Re"]),
            source_type="academic",
        )
        s2 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning",
            doi="10.48550/arXiv.2307.08691",
            canonical_url="https://arxiv.org/abs/2307.08691",
            original_url="https://arxiv.org/abs/2307.08691",
            authors_json=json.dumps(["Tri Dao", "Christopher Re"]),
            source_type="academic",
        )
        session.add(s1)
        session.add(s2)
        await session.commit()

        service = StudyIndependenceService(session)
        clusters = await service.analyze_and_persist_clusters(inv_id)
        assert len(clusters) == 1
        c = clusters[0]
        assert c.relationship_category == IndependenceCategory.RELATED_STUDIES.value
        assert "Shared authorship" in c.evidence_rationale


@pytest.mark.asyncio
async def test_unknown_independence_safeguard():
    """Verify that sources lacking metadata do not falsely receive 1.0 independence score."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="GPU market trends", mode="deep", status="created")
        session.add(inv)

        s1 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Blog post on computer graphics",
            canonical_url="https://random-tech-blog-123.com/post1",
            original_url="https://random-tech-blog-123.com/post1",
            source_type="general_reference",
            # No DOI, no authors
        )
        session.add(s1)
        await session.commit()

        service = StudyIndependenceService(session)
        clusters = await service.analyze_and_persist_clusters(inv_id)
        assert len(clusters) == 1
        c = clusters[0]
        assert c.relationship_category == IndependenceCategory.UNKNOWN_INDEPENDENCE.value
        assert c.confidence < 0.60
        assert "independence cannot be confirmed" in c.evidence_rationale
