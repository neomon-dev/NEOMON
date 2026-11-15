"""Autonomous Research Workflow Engine API Router (Milestone 9)."""

import json
from typing import Any
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.autonomous_workflow_service import autonomous_workflow_service
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.db import get_session
from app.errors import BackendError
from app.models import (
    AutonomousResearchWorkflow,
    Investigation,
    ResearchAction,
    ResearchWorkflowCycle,
    ResearchWorkflowReport,
    User,
)
from app.schemas import (
    ActionApprovalRequest,
    AutonomousWorkflowCreateRequest,
    AutonomousWorkflowView,
    ResearchActionView,
    ResearchWorkflowCycleView,
    ResearchWorkflowReportView,
    WorkflowContinueRequest,
)

router = APIRouter(prefix="/research/autonomous", tags=["autonomous_workflows"])


def _action_to_view(a: ResearchAction) -> ResearchActionView:
    queries = []
    providers = []
    res = {}
    try:
        queries = json.loads(a.search_queries_json)
    except Exception:
        pass
    try:
        providers = json.loads(a.target_providers_json)
    except Exception:
        pass
    try:
        res = json.loads(a.execution_result_json)
    except Exception:
        pass

    return ResearchActionView(
        id=a.id,
        workflow_id=a.workflow_id,
        cycle_id=a.cycle_id,
        action_type=a.action_type,
        target_entity_type=a.target_entity_type,
        target_entity_id=a.target_entity_id,
        objective=a.objective,
        rationale=a.rationale,
        search_queries=queries,
        target_providers=providers,
        priority=a.priority,
        expected_information_gain=a.expected_information_gain,
        estimated_cost=a.estimated_cost,
        status=a.status,
        requires_approval=a.requires_approval,
        approval_notes=a.approval_notes,
        execution_result=res,
        error_message=a.error_message,
        created_at=a.created_at,
        completed_at=a.completed_at,
    )


def _cycle_to_view(c: ResearchWorkflowCycle, actions: list[ResearchAction] | None = None) -> ResearchWorkflowCycleView:
    action_list = actions if actions is not None else []
    action_views = [_action_to_view(a) for a in action_list]
    return ResearchWorkflowCycleView(
        id=c.id,
        workflow_id=c.workflow_id,
        cycle_number=c.cycle_number,
        cycle_goal=c.cycle_goal,
        status=c.status,
        actions_total=c.actions_total,
        actions_completed=c.actions_completed,
        actions_failed=c.actions_failed,
        sources_acquired=c.sources_acquired,
        evidence_acquired=c.evidence_acquired,
        claims_updated=c.claims_updated,
        contradictions_detected=c.contradictions_detected,
        gaps_updated=c.gaps_updated,
        information_gain_score=c.information_gain_score,
        evaluation_summary=c.evaluation_summary,
        started_at=c.started_at,
        completed_at=c.completed_at,
        actions=action_views,
    )


async def _get_workflow_with_access(
    session: AsyncSession,
    user: User,
    workflow_id: uuid.UUID,
    capability: str = "read",
) -> AutonomousResearchWorkflow:
    wf = await session.get(AutonomousResearchWorkflow, workflow_id)
    if not wf:
        raise BackendError(f"Workflow {workflow_id} not found", status_code=404)
    perm = PermissionService(session)
    await perm.check_investigation_access(user, wf.investigation_id, capability)
    return wf


@router.post("/workflows", response_model=AutonomousWorkflowView)
async def create_workflow(
    payload: AutonomousWorkflowCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AutonomousWorkflowView:
    """Create a new persistent autonomous research workflow."""
    perm = PermissionService(session)
    await perm.check_investigation_access(user, payload.investigation_id, "write")
    try:
        wf = await autonomous_workflow_service.create_workflow(
            session=session,
            investigation_id=payload.investigation_id,
            title=payload.title,
            research_objective=payload.research_objective,
            autonomy_mode=payload.autonomy_mode,
            budget_max_cycles=payload.budget_max_cycles,
            budget_max_searches=payload.budget_max_searches,
            budget_max_sources=payload.budget_max_sources,
            budget_max_documents=payload.budget_max_documents,
            budget_max_duration_seconds=payload.budget_max_duration_seconds,
        )
        return await get_workflow(wf.id, user, session)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.get("/workflows", response_model=list[AutonomousWorkflowView])
async def list_workflows(
    investigation_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AutonomousWorkflowView]:
    """List all autonomous research workflows, optionally filtered by investigation_id."""
    perm = PermissionService(session)
    user_workspaces = await perm.get_user_workspaces(user.id)
    if not user_workspaces:
        return []

    if investigation_id is not None:
        await perm.check_investigation_access(user, investigation_id, "read")
        stmt = (
            select(AutonomousResearchWorkflow)
            .where(AutonomousResearchWorkflow.investigation_id == investigation_id)
            .order_by(desc(AutonomousResearchWorkflow.updated_at))
        )
        wf_res = await session.execute(stmt)
        workflows = list(wf_res.scalars().all())
    else:
        # Scoped to investigations in user's active workspaces
        stmt = (
            select(AutonomousResearchWorkflow)
            .join(Investigation, Investigation.id == AutonomousResearchWorkflow.investigation_id)
            .where(Investigation.workspace_id.in_(user_workspaces))
            .order_by(desc(AutonomousResearchWorkflow.updated_at))
        )
        wf_res = await session.execute(stmt)
        workflows = list(wf_res.scalars().all())

    items: list[AutonomousWorkflowView] = []
    for wf in workflows:
        inv = await session.get(Investigation, wf.investigation_id)
        items.append(
            AutonomousWorkflowView(
                id=wf.id,
                investigation_id=wf.investigation_id,
                investigation_question=inv.question if inv else "",
                title=wf.title,
                research_objective=wf.research_objective,
                status=wf.status,
                autonomy_mode=wf.autonomy_mode,
                current_cycle_number=wf.current_cycle_number,
                total_cycles_completed=wf.total_cycles_completed,
                stopping_reason=wf.stopping_reason,
                stopping_explanation=wf.stopping_explanation,
                scientific_confidence=wf.scientific_confidence,
                budget_max_cycles=wf.budget_max_cycles,
                budget_max_searches=wf.budget_max_searches,
                budget_max_sources=wf.budget_max_sources,
                budget_max_documents=wf.budget_max_documents,
                budget_max_duration_seconds=wf.budget_max_duration_seconds,
                spent_searches=wf.spent_searches,
                spent_sources=wf.spent_sources,
                spent_documents=wf.spent_documents,
                spent_llm_calls=wf.spent_llm_calls,
                consecutive_low_value_cycles=wf.consecutive_low_value_cycles,
                created_at=wf.created_at,
                updated_at=wf.updated_at,
                started_at=wf.started_at,
                completed_at=wf.completed_at,
                cycles=[],
            )
        )
    return items


@router.get("/workflows/{workflow_id}", response_model=AutonomousWorkflowView)
async def get_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AutonomousWorkflowView:
    """Retrieve full details of an autonomous workflow including cycles and actions."""
    wf = await _get_workflow_with_access(session, user, workflow_id, "read")

    inv = await session.get(Investigation, wf.investigation_id)

    cycles_res = await session.execute(
        select(ResearchWorkflowCycle)
        .where(ResearchWorkflowCycle.workflow_id == workflow_id)
        .order_by(ResearchWorkflowCycle.cycle_number)
    )
    cycles = list(cycles_res.scalars().all())

    cycle_views = []
    for c in cycles:
        actions_res = await session.execute(
            select(ResearchAction).where(ResearchAction.cycle_id == c.id).order_by(ResearchAction.priority)
        )
        actions = list(actions_res.scalars().all())
        cycle_views.append(_cycle_to_view(c, actions))

    return AutonomousWorkflowView(
        id=wf.id,
        investigation_id=wf.investigation_id,
        investigation_question=inv.question if inv else "",
        title=wf.title,
        research_objective=wf.research_objective,
        status=wf.status,
        autonomy_mode=wf.autonomy_mode,
        current_cycle_number=wf.current_cycle_number,
        total_cycles_completed=wf.total_cycles_completed,
        stopping_reason=wf.stopping_reason,
        stopping_explanation=wf.stopping_explanation,
        scientific_confidence=wf.scientific_confidence,
        budget_max_cycles=wf.budget_max_cycles,
        budget_max_searches=wf.budget_max_searches,
        budget_max_sources=wf.budget_max_sources,
        budget_max_documents=wf.budget_max_documents,
        budget_max_duration_seconds=wf.budget_max_duration_seconds,
        spent_searches=wf.spent_searches,
        spent_sources=wf.spent_sources,
        spent_documents=wf.spent_documents,
        spent_llm_calls=wf.spent_llm_calls,
        consecutive_low_value_cycles=wf.consecutive_low_value_cycles,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        started_at=wf.started_at,
        completed_at=wf.completed_at,
        cycles=cycle_views,
    )


@router.post("/workflows/{workflow_id}/start")
async def start_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Start execution of an approved autonomous research workflow."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        return await autonomous_workflow_service.start_workflow(
            session=session, workflow_id=workflow_id, run_in_background=True
        )
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.post("/workflows/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Pause execution of an active autonomous workflow."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        return await autonomous_workflow_service.pause_workflow(session, workflow_id)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.post("/workflows/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Resume execution of a paused autonomous workflow."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        return await autonomous_workflow_service.resume_workflow(session, workflow_id)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Cancel execution of an autonomous workflow."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        return await autonomous_workflow_service.cancel_workflow(session, workflow_id)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.get("/workflows/{workflow_id}/cycles", response_model=list[ResearchWorkflowCycleView])
async def list_cycles(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ResearchWorkflowCycleView]:
    """Retrieve full cycle history for a workflow."""
    await _get_workflow_with_access(session, user, workflow_id, "read")
    cycles_res = await session.execute(
        select(ResearchWorkflowCycle)
        .where(ResearchWorkflowCycle.workflow_id == workflow_id)
        .order_by(ResearchWorkflowCycle.cycle_number)
    )
    cycles = list(cycles_res.scalars().all())

    views = []
    for c in cycles:
        actions_res = await session.execute(
            select(ResearchAction).where(ResearchAction.cycle_id == c.id).order_by(ResearchAction.priority)
        )
        actions = list(actions_res.scalars().all())
        views.append(_cycle_to_view(c, actions))
    return views


@router.get("/workflows/{workflow_id}/actions", response_model=list[ResearchActionView])
async def list_actions(
    workflow_id: uuid.UUID,
    cycle_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ResearchActionView]:
    """Retrieve research actions with optional filtering."""
    await _get_workflow_with_access(session, user, workflow_id, "read")
    q = select(ResearchAction).where(ResearchAction.workflow_id == workflow_id)
    if cycle_id:
        q = q.where(ResearchAction.cycle_id == cycle_id)
    if status:
        q = q.where(ResearchAction.status == status)
    q = q.order_by(ResearchAction.priority)

    actions_res = await session.execute(q)
    return [_action_to_view(a) for a in actions_res.scalars().all()]


@router.post("/workflows/{workflow_id}/actions/{action_id}/approve")
async def approve_action(
    workflow_id: uuid.UUID,
    action_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Approve a pending research action in the human review queue."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        return await autonomous_workflow_service.approve_action(session, workflow_id, action_id)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.post("/workflows/{workflow_id}/actions/{action_id}/reject")
async def reject_action(
    workflow_id: uuid.UUID,
    action_id: uuid.UUID,
    payload: ActionApprovalRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Reject a pending research action with rationale."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        reason = payload.rejection_reason if payload and payload.rejection_reason else "Rejected by human operator."
        return await autonomous_workflow_service.reject_action(session, workflow_id, action_id, reason)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.post("/workflows/{workflow_id}/continue")
async def continue_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowContinueRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Grant additional research cycles and continue execution."""
    await _get_workflow_with_access(session, user, workflow_id, "write")
    try:
        add_cycles = payload.additional_cycles if payload else 2
        return await autonomous_workflow_service.continue_workflow(session, workflow_id, add_cycles)
    except ValueError as e:
        raise BackendError(str(e), status_code=400)


@router.get("/workflows/{workflow_id}/report", response_model=ResearchWorkflowReportView)
async def get_workflow_report(
    workflow_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResearchWorkflowReportView:
    """Retrieve or generate the final autonomous research report."""
    await _get_workflow_with_access(session, user, workflow_id, "read")
    rep_res = await session.execute(
        select(ResearchWorkflowReport).where(ResearchWorkflowReport.workflow_id == workflow_id)
    )
    rep = rep_res.scalar_one_or_none()
    if not rep:
        rep = await autonomous_workflow_service.generate_final_report(session, workflow_id)

    cycles_summary = []
    uncertainties = []
    next_actions = []
    try:
        cycles_summary = json.loads(rep.cycles_summary_json)
    except Exception:
        pass
    try:
        uncertainties = json.loads(rep.remaining_uncertainties_json)
    except Exception:
        pass
    try:
        next_actions = json.loads(rep.recommended_next_actions_json)
    except Exception:
        pass

    return ResearchWorkflowReportView(
        id=rep.id,
        workflow_id=rep.workflow_id,
        investigation_id=rep.investigation_id,
        title=rep.title,
        executive_summary=rep.executive_summary,
        research_objective=rep.research_objective,
        cycles_summary=cycles_summary,
        total_queries_executed=rep.total_queries_executed,
        total_sources_acquired=rep.total_sources_acquired,
        total_evidence_extracted=rep.total_evidence_extracted,
        claims_reassessed_count=rep.claims_reassessed_count,
        contradictions_resolved_count=rep.contradictions_resolved_count,
        remaining_uncertainties=uncertainties,
        recommended_next_actions=next_actions,
        stopping_reason=rep.stopping_reason,
        stopping_explanation=rep.stopping_explanation,
        calibrated_quality_tier=rep.calibrated_quality_tier,
        calibrated_quality_score=rep.calibrated_quality_score,
        created_at=rep.created_at,
    )
