"""Autonomous Research Workflow Orchestration Service (Milestone 9A, 9G, 9H).

Manages the complete lifecycle, state machine, durable recovery, human oversight,
and final report generation for autonomous research workflows.
"""

import asyncio
from datetime import UTC, datetime
import json
from typing import Any
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.research_cycle_service import execute_research_cycle
from app.db import SessionFactory
from app.events import EventBroker
from app.models import (
    AutonomousResearchWorkflow,
    Claim,
    Evidence,
    Investigation,
    ResearchAction,
    ResearchContradiction,
    ResearchGap,
    ResearchHypothesis,
    ResearchQueryHistory,
    ResearchWorkflowCheckpoint,
    ResearchWorkflowCycle,
    ResearchWorkflowReport,
    Source,
)
from app.schemas import EventType


# Valid state transitions
_VALID_TRANSITIONS = {
    "created": {"queued", "planning", "executing", "awaiting_approval", "paused", "cancelled"},
    "queued": {"planning", "executing", "paused", "cancelled", "failed"},
    "planning": {"executing", "awaiting_approval", "paused", "cancelled", "failed"},
    "awaiting_approval": {"executing", "paused", "cancelled", "failed"},
    "executing": {
        "evaluating",
        "refining",
        "paused",
        "awaiting_approval",
        "completed",
        "completed_with_limitations",
        "stopped_by_budget",
        "stopped_by_user",
        "failed",
        "cancelled",
    },
    "evaluating": {"refining", "executing", "completed", "completed_with_limitations", "stopped_by_budget", "paused", "failed", "cancelled"},
    "refining": {"executing", "completed", "completed_with_limitations", "stopped_by_budget", "paused", "failed", "cancelled"},
    "paused": {"executing", "planning", "cancelled"},
    "awaiting_human_review": {"executing", "cancelled"},
    "completed": {"executing", "planning"},  # Can be continued with explicit new cycle
    "completed_with_limitations": {"executing", "planning"},
    "stopped_by_budget": {"executing", "planning"},
    "stopped_by_user": {"executing"},
    "failed": {"executing", "queued"},
    "cancelled": set(),
}


class AutonomousWorkflowService:
    def __init__(self, broker: EventBroker | None = None):
        self.broker = broker
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}

    def _validate_transition(self, current_status: str, new_status: str) -> None:
        allowed = _VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid autonomous workflow transition: cannot transition from '{current_status}' to '{new_status}'."
            )

    async def create_workflow(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        title: str,
        research_objective: str,
        autonomy_mode: str = "bounded",
        budget_max_cycles: int = 5,
        budget_max_searches: int = 20,
        budget_max_sources: int = 50,
        budget_max_documents: int = 20,
        budget_max_duration_seconds: int = 1800,
    ) -> AutonomousResearchWorkflow:
        inv = await session.get(Investigation, investigation_id)
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found")

        wf = AutonomousResearchWorkflow(
            investigation_id=investigation_id,
            title=title,
            research_objective=research_objective,
            status="created",
            autonomy_mode=autonomy_mode,
            budget_max_cycles=budget_max_cycles,
            budget_max_searches=budget_max_searches,
            budget_max_sources=budget_max_sources,
            budget_max_documents=budget_max_documents,
            budget_max_duration_seconds=budget_max_duration_seconds,
        )
        session.add(wf)
        await session.flush()

        checkpoint = ResearchWorkflowCheckpoint(
            workflow_id=wf.id,
            checkpoint_type="created",
            cycle_number=0,
            state_snapshot_json=json.dumps({
                "status": "created",
                "objective": research_objective,
                "autonomy_mode": autonomy_mode,
            }),
        )
        session.add(checkpoint)
        await session.commit()
        return wf

    async def start_workflow(
        self,
        session: AsyncSession,
        workflow_id: uuid.UUID,
        run_in_background: bool = True,
    ) -> dict[str, Any]:
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._validate_transition(wf.status, "executing")
        wf.status = "executing"
        wf.started_at = datetime.now(UTC)
        await session.commit()

        if run_in_background:
            task = asyncio.create_task(self._run_workflow_execution_loop(wf.id))
            self._active_tasks[str(wf.id)] = task
            return {
                "workflow_id": str(wf.id),
                "status": "executing",
                "message": "Workflow started in background.",
            }
        else:
            return await self._run_workflow_execution_loop(wf.id)

    async def _run_workflow_execution_loop(self, workflow_id: uuid.UUID) -> dict[str, Any]:
        """Main iterative execution loop running across research cycles."""
        while True:
            async with SessionFactory() as session:
                wf = await session.get(AutonomousResearchWorkflow, workflow_id)
                if not wf or wf.status not in ("executing", "created", "queued"):
                    break

                next_cycle = wf.current_cycle_number + 1
                if next_cycle > wf.budget_max_cycles:
                    wf.status = "stopped_by_budget"
                    wf.stopping_reason = "maximum_cycles_reached"
                    wf.completed_at = datetime.now(UTC)
                    await session.commit()
                    break

                # Execute one research cycle
                cycle_res = await execute_research_cycle(
                    session=session,
                    broker=self.broker,
                    workflow_id=wf.id,
                    cycle_number=next_cycle,
                )

                # Check if cycle paused for approval or reached terminal state
                terminal_states = {
                    "completed",
                    "completed_with_limitations",
                    "stopped_by_budget",
                    "stopped_by_user",
                    "failed",
                    "cancelled",
                    "awaiting_approval",
                    "paused",
                }
                if cycle_res.get("status") in terminal_states:
                    break

        # Synthesize final report upon completion
        async with SessionFactory() as session:
            final_wf = await session.get(AutonomousResearchWorkflow, workflow_id)
            if final_wf and final_wf.status in ("completed", "completed_with_limitations", "stopped_by_budget"):
                await self.generate_final_report(session, final_wf.id)

            return {
                "workflow_id": str(workflow_id),
                "final_status": final_wf.status if final_wf else "unknown",
                "stopping_reason": final_wf.stopping_reason if final_wf else None,
                "cycles_completed": final_wf.total_cycles_completed if final_wf else 0,
            }

    async def pause_workflow(
        self, session: AsyncSession, workflow_id: uuid.UUID
    ) -> dict[str, Any]:
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._validate_transition(wf.status, "paused")
        wf.status = "paused"
        checkpoint = ResearchWorkflowCheckpoint(
            workflow_id=wf.id,
            checkpoint_type="pause",
            cycle_number=wf.current_cycle_number,
            state_snapshot_json=json.dumps({"status": "paused"}),
        )
        session.add(checkpoint)
        await session.commit()
        return {"workflow_id": str(wf.id), "status": "paused"}

    async def resume_workflow(
        self, session: AsyncSession, workflow_id: uuid.UUID
    ) -> dict[str, Any]:
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._validate_transition(wf.status, "executing")
        wf.status = "executing"
        await session.commit()

        task = asyncio.create_task(self._run_workflow_execution_loop(wf.id))
        self._active_tasks[str(wf.id)] = task
        return {"workflow_id": str(wf.id), "status": "executing"}

    async def cancel_workflow(
        self, session: AsyncSession, workflow_id: uuid.UUID
    ) -> dict[str, Any]:
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        self._validate_transition(wf.status, "cancelled")
        wf.status = "cancelled"
        wf.stopping_reason = "user_cancelled"
        wf.stopping_explanation = "Workflow explicitly cancelled by user."
        wf.completed_at = datetime.now(UTC)

        # Cancel active background task if running
        task = self._active_tasks.pop(str(wf.id), None)
        if task and not task.done():
            task.cancel()

        await session.commit()
        return {"workflow_id": str(wf.id), "status": "cancelled"}

    async def approve_action(
        self, session: AsyncSession, workflow_id: uuid.UUID, action_id: uuid.UUID
    ) -> dict[str, Any]:
        action = await session.get(ResearchAction, action_id)
        if not action or action.workflow_id != workflow_id:
            raise ValueError(f"Action {action_id} not found for workflow {workflow_id}")

        action.status = "approved"
        await session.commit()

        # Check if workflow was awaiting approval and can now resume
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if wf and wf.status == "awaiting_approval":
            # Check remaining pending approvals in current cycle
            pending_res = await session.execute(
                select(func.count(ResearchAction.id)).where(
                    ResearchAction.cycle_id == action.cycle_id,
                    ResearchAction.status == "awaiting_approval",
                )
            )
            if (pending_res.scalar() or 0) == 0:
                wf.status = "executing"
                await session.commit()
                task = asyncio.create_task(self._run_workflow_execution_loop(wf.id))
                self._active_tasks[str(wf.id)] = task

        return {"action_id": str(action.id), "status": "approved"}

    async def reject_action(
        self,
        session: AsyncSession,
        workflow_id: uuid.UUID,
        action_id: uuid.UUID,
        rejection_reason: str = "Rejected by user during human oversight review.",
    ) -> dict[str, Any]:
        action = await session.get(ResearchAction, action_id)
        if not action or action.workflow_id != workflow_id:
            raise ValueError(f"Action {action_id} not found for workflow {workflow_id}")

        action.status = "rejected"
        action.approval_notes = rejection_reason
        await session.commit()
        return {"action_id": str(action.id), "status": "rejected"}

    async def continue_workflow(
        self, session: AsyncSession, workflow_id: uuid.UUID, additional_cycles: int = 2
    ) -> dict[str, Any]:
        """Grant additional cycles to a stopped/completed workflow and resume."""
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        wf.budget_max_cycles += additional_cycles
        wf.status = "executing"
        wf.stopping_reason = None
        wf.stopping_explanation = ""
        wf.completed_at = None
        await session.commit()

        task = asyncio.create_task(self._run_workflow_execution_loop(wf.id))
        self._active_tasks[str(wf.id)] = task
        return {
            "workflow_id": str(wf.id),
            "status": "executing",
            "new_max_cycles": wf.budget_max_cycles,
        }

    async def generate_final_report(
        self, session: AsyncSession, workflow_id: uuid.UUID
    ) -> ResearchWorkflowReport:
        wf = await session.get(AutonomousResearchWorkflow, workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")

        inv = await session.get(Investigation, wf.investigation_id)

        # Cycles summary
        cycles_res = await session.execute(
            select(ResearchWorkflowCycle)
            .where(ResearchWorkflowCycle.workflow_id == workflow_id)
            .order_by(ResearchWorkflowCycle.cycle_number)
        )
        cycles = list(cycles_res.scalars().all())
        cycles_summary = [
            {
                "cycle_number": c.cycle_number,
                "goal": c.cycle_goal,
                "sources_acquired": c.sources_acquired,
                "evidence_acquired": c.evidence_acquired,
                "claims_updated": c.claims_updated,
                "information_gain": c.information_gain_score,
                "summary": c.evaluation_summary,
            }
            for c in cycles
        ]

        # Counts
        claims_res = await session.execute(
            select(Claim).where(Claim.investigation_id == wf.investigation_id)
        )
        claims = list(claims_res.scalars().all())

        sources_res = await session.execute(
            select(Source).where(Source.investigation_id == wf.investigation_id)
        )
        sources = list(sources_res.scalars().all())

        ev_count_res = await session.execute(
            select(func.count(Evidence.id))
            .join(Source)
            .where(Source.investigation_id == wf.investigation_id)
        )
        total_evidence = ev_count_res.scalar() or 0

        contra_res = await session.execute(
            select(ResearchContradiction).where(
                (ResearchContradiction.primary_investigation_id == wf.investigation_id)
                | (ResearchContradiction.secondary_investigation_id == wf.investigation_id)
            )
        )
        contradictions = list(contra_res.scalars().all())

        # Load calibrated quality
        from app.models import ResearchQualityCalibration
        cal_res = await session.execute(
            select(ResearchQualityCalibration).where(
                ResearchQualityCalibration.investigation_id == wf.investigation_id
            )
        )
        cal = cal_res.scalar_one_or_none()

        q_tier = cal.calibrated_tier if cal else "Moderate"
        q_score = cal.calibrated_score if cal else 50.0

        # Remaining uncertainties
        uncertainties = []
        unsupported = [c.text for c in claims if c.status in ("unassessed", "disputed")]
        if unsupported:
            uncertainties.append(f"Disputed or ungrounded claims remain: {len(unsupported)} claim(s).")
        active_contra = [con.title for con in contradictions if con.status == "active"]
        if active_contra:
            uncertainties.append(f"Unresolved dialectical tensions: {'; '.join(active_contra[:2])}.")

        # Recommended next actions
        recommendations = [
            "Conduct targeted empirical trials or laboratory benchmark replications.",
            "Cross-reference newly discovered findings with future academic conference proceedings.",
            "Review methodological constraints highlighted in the quality audit matrix.",
        ]

        exec_summary = (
            f"Autonomous research workflow executed {len(cycles)} cycle(s) over research objective '{wf.research_objective[:80]}'. "
            f"Acquired {len(sources)} sources and {total_evidence} evidence passages. Final evidence rating: {q_tier} ({q_score:.1f}/100). "
            f"Stopping rationale: {wf.stopping_explanation or 'Workflow reached stopping condition.'}"
        )

        existing_rep_res = await session.execute(
            select(ResearchWorkflowReport).where(ResearchWorkflowReport.workflow_id == workflow_id)
        )
        report = existing_rep_res.scalar_one_or_none()

        if report:
            report.executive_summary = exec_summary
            report.cycles_summary_json = json.dumps(cycles_summary)
            report.total_sources_acquired = len(sources)
            report.total_evidence_extracted = total_evidence
            report.stopping_reason = wf.stopping_reason or "completed"
            report.stopping_explanation = wf.stopping_explanation or ""
            report.calibrated_quality_tier = q_tier
            report.calibrated_quality_score = q_score
            report.remaining_uncertainties_json = json.dumps(uncertainties)
        else:
            report = ResearchWorkflowReport(
                workflow_id=wf.id,
                investigation_id=wf.investigation_id,
                title=f"Autonomous Research Report: {wf.title}",
                executive_summary=exec_summary,
                research_objective=wf.research_objective,
                initial_state_json=json.dumps({"claims": len(claims), "status": "created"}),
                final_state_json=json.dumps({"claims": len(claims), "sources": len(sources), "evidence": total_evidence}),
                cycles_summary_json=json.dumps(cycles_summary),
                total_queries_executed=wf.spent_searches,
                total_sources_acquired=len(sources),
                total_evidence_extracted=total_evidence,
                claims_reassessed_count=sum(1 for c in claims if c.status != "unassessed"),
                contradictions_resolved_count=sum(1 for con in contradictions if con.status == "resolved"),
                remaining_uncertainties_json=json.dumps(uncertainties),
                recommended_next_actions_json=json.dumps(recommendations),
                stopping_reason=wf.stopping_reason or "completed",
                stopping_explanation=wf.stopping_explanation or "",
                calibrated_quality_tier=q_tier,
                calibrated_quality_score=q_score,
            )
            session.add(report)

        await session.commit()
        return report

    async def recover_workflows(self) -> int:
        """Startup recovery: recovers in-flight workflows interrupted by server restart."""
        recovered_count = 0
        async with SessionFactory() as session:
            active_res = await session.execute(
                select(AutonomousResearchWorkflow).where(
                    AutonomousResearchWorkflow.status.in_(["executing", "planning", "evaluating", "refining"])
                )
            )
            interrupted = list(active_res.scalars().all())

            for wf in interrupted:
                # Set to paused with checkpoint explanation so user can resume cleanly
                wf.status = "paused"
                wf.stopping_explanation = "Execution paused automatically due to backend server restart. Can be resumed cleanly."
                cp = ResearchWorkflowCheckpoint(
                    workflow_id=wf.id,
                    checkpoint_type="recovery",
                    cycle_number=wf.current_cycle_number,
                    state_snapshot_json=json.dumps({
                        "event": "server_restart_recovery",
                        "cycle": wf.current_cycle_number,
                    }),
                )
                session.add(cp)
                recovered_count += 1

            if recovered_count > 0:
                await session.commit()

        return recovered_count


autonomous_workflow_service = AutonomousWorkflowService()


async def recover_workflows(session_factory: Any = None) -> int:
    """Convenience helper for server startup recovery."""
    return await autonomous_workflow_service.recover_workflows()

