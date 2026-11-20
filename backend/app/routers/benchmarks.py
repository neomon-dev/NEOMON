"""API Router for Benchmark Datasets, Evaluations, and Regression Comparisons."""

import json
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import BenchmarkDataset, BenchmarkRun, User
from app.auth.dependencies import get_current_user
from app.schemas_m12 import BenchmarkDatasetResponse, BenchmarkRunResponse
from app.benchmarks.service import BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


def _to_dataset_response(b: BenchmarkDataset) -> BenchmarkDatasetResponse:
    def _parse(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    return BenchmarkDatasetResponse(
        id=str(b.id),
        name=b.name,
        slug=b.slug,
        version=b.version,
        category=b.category,
        research_question=b.research_question,
        expected_claims=_parse(b.expected_claims_json, []),
        verified_source_references=_parse(b.verified_source_references_json, []),
        expected_support_classifications=_parse(b.expected_support_classifications_json, {}),
        known_counterevidence=_parse(b.known_counterevidence_json, []),
        known_methodological_limitations=_parse(b.known_methodological_limitations_json, []),
        expected_conclusion=b.expected_conclusion,
        evaluation_notes=b.evaluation_notes,
        is_active=b.is_active,
        created_at=b.created_at.isoformat() if b.created_at else "",
    )


def _to_run_response(r: BenchmarkRun) -> BenchmarkRunResponse:
    def _parse(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    return BenchmarkRunResponse(
        id=str(r.id),
        benchmark_dataset_id=str(r.benchmark_dataset_id),
        investigation_id=str(r.investigation_id) if r.investigation_id else None,
        run_version=r.run_version,
        status=r.status,
        retrieval_metrics=_parse(r.retrieval_metrics_json, {}),
        evidence_metrics=_parse(r.evidence_metrics_json, {}),
        synthesis_metrics=_parse(r.synthesis_metrics_json, {}),
        operations_metrics=_parse(r.operations_metrics_json, {}),
        overall_evaluation_summary=r.overall_evaluation_summary,
        created_at=r.created_at.isoformat() if r.created_at else "",
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
    )


@router.get("", response_model=List[BenchmarkDatasetResponse])
async def list_benchmarks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all available scientific benchmark datasets."""
    service = BenchmarkService(db)
    await service.seed_default_benchmarks()
    datasets = await service.list_benchmark_datasets()
    return [_to_dataset_response(d) for d in datasets]


@router.get("/{benchmark_id_or_slug}", response_model=BenchmarkDatasetResponse)
async def get_benchmark(
    benchmark_id_or_slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve details for a specific benchmark dataset by ID or slug."""
    service = BenchmarkService(db)
    await service.seed_default_benchmarks()

    try:
        b_id = uuid.UUID(benchmark_id_or_slug)
        ds = await db.get(BenchmarkDataset, b_id)
    except ValueError:
        ds = await service.get_benchmark_by_slug(benchmark_id_or_slug)

    if not ds:
        raise HTTPException(status_code=404, detail="Benchmark dataset not found")

    return _to_dataset_response(ds)


@router.get("/{benchmark_id_or_slug}/runs", response_model=List[BenchmarkRunResponse])
async def list_benchmark_runs(
    benchmark_id_or_slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List historical evaluation runs for a benchmark dataset."""
    from sqlalchemy import select, desc
    service = BenchmarkService(db)
    await service.seed_default_benchmarks()

    try:
        b_id = uuid.UUID(benchmark_id_or_slug)
        ds = await db.get(BenchmarkDataset, b_id)
    except ValueError:
        ds = await service.get_benchmark_by_slug(benchmark_id_or_slug)

    if not ds:
        raise HTTPException(status_code=404, detail="Benchmark dataset not found")

    runs = list(
        (
            await db.scalars(
                select(BenchmarkRun)
                .where(BenchmarkRun.benchmark_dataset_id == ds.id)
                .order_by(desc(BenchmarkRun.created_at))
            )
        ).all()
    )
    return [_to_run_response(r) for r in runs]


@router.post("/{benchmark_id_or_slug}/evaluate/{investigation_id}", response_model=BenchmarkRunResponse)
async def evaluate_investigation_benchmark(
    benchmark_id_or_slug: str,
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Execute quantitative benchmark evaluation against an investigation."""
    service = BenchmarkService(db)
    await service.seed_default_benchmarks()

    try:
        b_id = uuid.UUID(benchmark_id_or_slug)
        ds = await db.get(BenchmarkDataset, b_id)
    except ValueError:
        ds = await service.get_benchmark_by_slug(benchmark_id_or_slug)

    if not ds:
        raise HTTPException(status_code=404, detail="Benchmark dataset not found")

    try:
        run = await service.evaluate_investigation(ds.id, investigation_id)
        return _to_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/regression/{slug}/{investigation_id}")
@router.post("/regression/{slug}/{investigation_id}")
async def get_regression_comparison(
    slug: str,
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Perform side-by-side regression comparison between historical baseline and Milestone 12 engine."""
    service = BenchmarkService(db)
    await service.seed_default_benchmarks()

    try:
        return await service.run_regression_comparison(slug, investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
