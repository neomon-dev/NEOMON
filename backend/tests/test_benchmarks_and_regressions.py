"""Tests for Benchmarks, Quantitative Evaluation, and Regression Comparisons (Milestone 12)."""

import json
import uuid
import pytest
from app.db import SessionFactory
from app.models import Investigation, Source, Claim, Evidence
from app.benchmarks.service import BenchmarkService


@pytest.mark.asyncio
async def test_seed_and_list_benchmarks():
    """Verify seeding of 10 canonical benchmark datasets across distinct categories."""
    async with SessionFactory() as session:
        service = BenchmarkService(session)
        created = await service.seed_default_benchmarks()
        datasets = await service.list_benchmark_datasets()
        assert len(datasets) >= 10

        categories = {d.category for d in datasets}
        assert "technology_industry" in categories
        assert "historical" in categories
        assert "scientific" in categories
        assert "causal" in categories
        assert "conflicting_evidence" in categories


@pytest.mark.asyncio
async def test_benchmark_quantitative_evaluation():
    """Verify evaluation generates retrieval, evidence, synthesis, and ops metrics."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        service = BenchmarkService(session)
        await service.seed_default_benchmarks()
        nvidia_bench = await service.get_benchmark_by_slug("nvidia-ai-era")
        assert nvidia_bench is not None

        # Create investigation matching benchmark
        inv = Investigation(id=inv_id, question="What role nvidia played in the era of AI", mode="deep", status="completed")
        session.add(inv)
        s1 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="CUDA Architecture Whitepaper",
            canonical_url="https://nvidianews.nvidia.com/cuda",
            original_url="https://nvidianews.nvidia.com/cuda",
            source_type="peer_reviewed",
        )
        session.add(s1)
        claim = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="NVIDIA CUDA architecture created lock-in for GPU acceleration.")
        session.add(claim)
        ev = Evidence(
            id=uuid.uuid4(),
            source_id=s1.id,
            exact_text="Empirical results confirm that CUDA architecture created developer lock-in.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)
        await session.commit()

        run = await service.evaluate_investigation(nvidia_bench.id, inv_id)
        assert run.status == "completed"

        retrieval = json.loads(run.retrieval_metrics_json)
        assert "source_recall" in retrieval
        assert "primary_source_discovery" in retrieval

        evidence_m = json.loads(run.evidence_metrics_json)
        assert "passage_relevance" in evidence_m
        assert "direct_entailment_precision" in evidence_m

        synthesis_m = json.loads(run.synthesis_metrics_json)
        assert "claim_coverage" in synthesis_m
        assert "study_independence_accuracy" in synthesis_m


@pytest.mark.asyncio
async def test_nvidia_historical_regression_comparison():
    """Verify side-by-side comparison between historical baseline and Milestone 12 engine."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        service = BenchmarkService(session)
        await service.seed_default_benchmarks()

        inv = Investigation(id=inv_id, question="What role nvidia played in the era of AI", mode="deep", status="completed")
        session.add(inv)
        s1 = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="NVIDIA GPU Scaling",
            canonical_url="https://nvidianews.nvidia.com/gpu",
            original_url="https://nvidianews.nvidia.com/gpu",
            source_type="peer_reviewed",
        )
        session.add(s1)
        claim = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="NVIDIA GPUs dominate deep learning training clusters.")
        session.add(claim)
        ev = Evidence(
            id=uuid.uuid4(),
            source_id=s1.id,
            exact_text="Empirical findings show NVIDIA GPUs power over 80% of top500 supercomputing clusters.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)
        await session.commit()

        comparison = await service.run_regression_comparison("nvidia-ai-era", inv_id)
        assert comparison["benchmark_slug"] == "nvidia-ai-era"
        assert "historical_baseline" in comparison
        assert "milestone_12_calibrated" in comparison
        assert len(comparison["changes_explained"]) >= 3
        assert "Defensible under peer review" in comparison["scientific_defensibility"]
