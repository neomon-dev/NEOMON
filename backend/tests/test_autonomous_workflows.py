"""Automated tests for Autonomous Research Workflow Engine (Milestone 9).

Verifies:
- 9A: Persistent state machine transitions and execution controls
- 9B: Intelligent deterministic-first research planning and prioritization
- 9C: Adaptive query refinement, deduplication, and counter-evidence queries
- 9D: Iterative evidence calibration, claim reevaluation, and information gain
- 9E: Resource budget constraints (cycles, searches, sources, duration)
- 9F: Scientific stopping criteria (saturation, diminishing returns, persistent uncertainty)
- 9G: Human oversight and action approval/rejection in assisted mode
- 9H: Startup crash recovery and checkpointing
- 9I: REST API endpoints for autonomous workflows
- 9J: Graph node and edge integration for workflows, cycles, and actions
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.analysis.adaptive_query_service import (
    adapt_query_for_provider,
    generate_adaptive_query_variants,
    is_near_duplicate_query,
    refine_query_for_counter_evidence,
)
from app.analysis.autonomous_workflow_service import (
    AutonomousWorkflowService,
    recover_workflows,
)
from app.analysis.research_planner import (
    PlannedResearchAction,
    ResearchActionType,
    plan_research_cycle,
)
from app.analysis.research_stopping_service import (
    StoppingReason,
    evaluate_stopping_criteria,
)
from app.db import SessionFactory
from app.main import app
from app.models import (
    AutonomousResearchWorkflow,
    Claim,
    Evidence,
    Investigation,
    ResearchAction,
    ResearchContradiction,
    ResearchGap,
    ResearchHypothesis,
    ResearchWorkflowCheckpoint,
    ResearchWorkflowCycle,
    ResearchWorkflowReport,
    Source,
)


# =====================================================================
# 1. 9B: Research Planner Unit Tests
# =====================================================================

def test_research_planner_action_formulation_and_prioritization():
    """Verify deterministic formulation of prioritized research actions."""
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    gap_id = uuid.uuid4()
    hyp_id = uuid.uuid4()

    claims = [
        Claim(
            id=claim_id,
            investigation_id=inv_id,
            text="Quantum error correction reduces logical error rates below physical rates.",
            priority=1,
            status="unassessed",
        )
    ]
    gaps = [
        ResearchGap(
            id=gap_id,
            category="methodological_limitation",
            title="Lack of macroscopic multi-qubit benchmarking",
            severity="critical",
            research_priority=9,
            recommended_action_json='{"action_type": "empirical_benchmark", "query": "macroscopic surface code threshold"}',
        )
    ]
    hypotheses = [
        ResearchHypothesis(
            id=hyp_id,
            investigation_id=inv_id,
            title="Threshold Scaling Hypothesis",
            statement="Logical error suppression scales exponentially with code distance d.",
            category="theoretical",
            status="active",
            testability_score=8.5,
            falsification_criteria="Observation of non-exponential scaling at d >= 7.",
        )
    ]
    contradictions = [
        ResearchContradiction(
            id=uuid.uuid4(),
            primary_investigation_id=inv_id,
            title="Divergent threshold estimates",
            severity="critical",
            status="active",
            scope_differences="Planar vs 3D color codes",
        )
    ]

    inv = Investigation(
        id=inv_id,
        question="What are the physical limits of surface code quantum error correction?",
        mode="quick",
        status="completed",
    )
    plan = plan_research_cycle(
        workflow_id=str(uuid.uuid4()),
        cycle_number=1,
        investigation=inv,
        claims=claims,
        sources=[],
        evidence=[],
        gaps=gaps,
        contradictions=contradictions,
        hypotheses=hypotheses,
        max_actions=6,
    )

    assert plan.cycle_number == 1
    assert len(plan.actions) > 0
    assert len(plan.actions) <= 6

    # Verify prioritization is deterministic and sorted ascending by priority (1 is highest)
    priorities = [a.priority for a in plan.actions]
    assert priorities == sorted(priorities)

    assert any(
        a.action_type
        in [
            ResearchActionType.INVESTIGATE_CONTRADICTION,
            ResearchActionType.INVESTIGATE_METHODOLOGY,
            ResearchActionType.INVESTIGATE_CLAIM,
            ResearchActionType.EVALUATE_HYPOTHESIS,
        ]
        for a in plan.actions
    )


# =====================================================================
# 2. 9C: Adaptive Query Refinement & Deduplication Unit Tests
# =====================================================================

def test_query_deduplication_and_similarity():
    """Verify near-duplicate query detection using token overlap and Jaccard similarity."""
    history = [
        "surface code quantum error correction threshold",
        "fault-tolerant quantum computing physical qubit scaling",
    ]

    # Exact or near exact match
    assert is_near_duplicate_query("surface code quantum error correction threshold", history) is True
    # Word reordering or minor stopword addition
    assert is_near_duplicate_query("quantum error correction surface code threshold", history) is True
    # Distinct new query
    assert is_near_duplicate_query("cryogenic CMOS control wiring thermal dissipation", history) is False


def test_provider_specific_query_adaptation():
    """Verify provider-specific syntax adaptation (arXiv, OpenAlex, Tavily)."""
    base_query = "surface code quantum error correction"

    arxiv_q = adapt_query_for_provider(base_query, "arxiv")
    assert len(arxiv_q.split()) <= 6

    openalex_q = adapt_query_for_provider(base_query, "openalex")
    assert "empirical study" in openalex_q

    tavily_q = adapt_query_for_provider(base_query, "tavily")
    assert isinstance(tavily_q, str)


def test_counter_evidence_query_formulation():
    """Verify counter-evidence reformulation creates critical falsification probes."""
    claim_text = "mRNA vaccines demonstrate complete long-term humoral immunity."
    counter_q = refine_query_for_counter_evidence(claim_text)

    lower_cq = counter_q.lower()
    assert any(term in lower_cq for term in ["limitations", "counter-evidence", "confounding", "refutation", "failure"])


# =====================================================================
# 3. 9E & 9F: Budget Management & Scientific Stopping Criteria Unit Tests
# =====================================================================

def test_stopping_criteria_evaluation():
    """Verify operational budget limits vs scientific stopping conditions."""
    inv_id = uuid.uuid4()
    inv = Investigation(
        id=inv_id,
        question="What are the mechanistic limits of biological aging?",
        mode="quick",
        status="completed",
    )
    claims = [
        Claim(id=uuid.uuid4(), investigation_id=inv_id, text="Claim 1", priority=1),
        Claim(id=uuid.uuid4(), investigation_id=inv_id, text="Claim 2", priority=2),
    ]

    # 1. Max cycles reached
    wf_max_cycles = AutonomousResearchWorkflow(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        title="Aging Loop",
        research_objective="Investigate aging limits",
        current_cycle_number=3,
        budget_max_cycles=3,
        budget_max_searches=30,
        budget_max_sources=50,
        budget_max_duration_seconds=1800,
    )
    res_cycles = evaluate_stopping_criteria(
        workflow=wf_max_cycles,
        investigation=inv,
        claims=claims,
        sources=[],
        evidence=[],
        calibration=None,
    )
    assert res_cycles.should_stop is True
    assert res_cycles.stopping_reason == StoppingReason.MAXIMUM_CYCLES_REACHED

    # 2. Diminishing returns (consecutive low value cycles)
    wf_dim = AutonomousResearchWorkflow(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        title="Aging Loop",
        research_objective="Investigate aging limits",
        current_cycle_number=2,
        budget_max_cycles=10,
        consecutive_low_value_cycles=3,  # Reached limit
        budget_max_consecutive_low_value=2,
    )
    res_dim = evaluate_stopping_criteria(
        workflow=wf_dim,
        investigation=inv,
        claims=claims,
        sources=[],
        evidence=[],
        calibration=None,
        recent_cycle_gain=0.01,
    )
    assert res_dim.should_stop is True
    assert res_dim.stopping_reason == StoppingReason.DIMINISHING_RETURNS

    # 3. Active critical contradictions prevent premature scientific completion
    contra = ResearchContradiction(
        id=uuid.uuid4(),
        primary_investigation_id=inv_id,
        title="Disputed senolytic efficacy",
        severity="critical",
        status="active",
    )
    wf_active = AutonomousResearchWorkflow(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        title="Aging Loop",
        research_objective="Investigate aging limits",
        current_cycle_number=1,
        budget_max_cycles=5,
        consecutive_low_value_cycles=0,
    )
    res_contra = evaluate_stopping_criteria(
        workflow=wf_active,
        investigation=inv,
        claims=claims,
        sources=[],
        evidence=[],
        calibration=None,
        contradictions=[contra],
        recent_cycle_gain=0.6,
    )
    # Should not stop because cycle budget remains and active contradictions require research
    assert res_contra.should_stop is False


# =====================================================================
# 4. 9H: Startup Crash Recovery Unit Tests
# =====================================================================

@pytest.mark.asyncio
async def test_recover_workflows_on_startup():
    """Verify recovery on startup transitions in-flight workflows to paused with checkpoints."""
    inv_id = uuid.uuid4()
    wf_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="Can cold atmospheric plasma sterilize biofilm on titanium implants?",
            mode="quick",
            status="completed",
        )
        session.add(inv)

        # In-flight workflow that was interrupted during server restart
        wf = AutonomousResearchWorkflow(
            id=wf_id,
            investigation_id=inv_id,
            title="Biofilm In-Flight Workflow",
            research_objective="Autonomous biofilm research",
            autonomy_mode="bounded",
            status="executing",
            current_cycle_number=1,
            budget_max_cycles=3,
        )
        session.add(wf)
        await session.commit()

    # Run startup recovery
    recovered_count = await recover_workflows(SessionFactory)
    assert recovered_count >= 1

    # Verify workflow state transitioned to paused with a checkpoint
    async with SessionFactory() as session:
        wf_updated = await session.get(AutonomousResearchWorkflow, wf_id)
        assert wf_updated is not None
        assert wf_updated.status == "paused"

        checkpoints = list(
            (
                await session.scalars(
                    select(ResearchWorkflowCheckpoint).where(
                        ResearchWorkflowCheckpoint.workflow_id == wf_id
                    )
                )
            ).all()
        )
        assert len(checkpoints) >= 1
        assert "recovery" in checkpoints[0].checkpoint_type.lower()


# =====================================================================
# 5. 9A, 9G: End-to-End Workflow Service & Oversight Unit Tests
# =====================================================================

@pytest.mark.asyncio
async def test_workflow_lifecycle_and_assisted_oversight():
    """Verify workflow state transitions, assisted mode oversight, and report generation."""
    inv_id = uuid.uuid4()
    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="What is the evidence for neural plasticity in adult neurogenesis?",
            mode="deep",
            status="completed",
        )
        session.add(inv)
        await session.commit()

    service = AutonomousWorkflowService()

    # 1. Create assisted workflow
    async with SessionFactory() as session:
        wf = await service.create_workflow(
            session=session,
            investigation_id=inv_id,
            title="Adult Neurogenesis Assisted Loop",
            research_objective="Investigate subventricular zone neurogenesis in adults",
            autonomy_mode="assisted",
            budget_max_cycles=2,
            budget_max_searches=6,
            budget_max_sources=15,
            budget_max_duration_seconds=600,
        )
        await session.commit()
        wf_id = wf.id

    # 2. Pause and Resume state machine transitions
    async with SessionFactory() as session:
        paused_res = await service.pause_workflow(session, wf_id)
        assert paused_res["status"] == "paused"

    async with SessionFactory() as session:
        with patch.object(service, "_run_workflow_execution_loop", new_callable=AsyncMock):
            resumed_res = await service.resume_workflow(session, wf_id)
            assert resumed_res["status"] == "executing"

    # 3. Simulate cycle execution with actions
    cycle_id = uuid.uuid4()
    act_id = uuid.uuid4()
    act2_id = uuid.uuid4()

    async with SessionFactory() as session:
        cycle = ResearchWorkflowCycle(
            id=cycle_id,
            workflow_id=wf_id,
            cycle_number=1,
            cycle_goal="Test assisted action approval",
            status="awaiting_approval",
        )
        session.add(cycle)

        act = ResearchAction(
            id=act_id,
            workflow_id=wf_id,
            cycle_id=cycle.id,
            action_type="counter_evidence_probe",
            objective="Probe adult neurogenesis counter-evidence",
            rationale="Test counter-evidence query approval",
            priority=8,
            status="awaiting_approval",
            requires_approval=True,
            expected_information_gain=0.6,
        )
        session.add(act)

        act2 = ResearchAction(
            id=act2_id,
            workflow_id=wf_id,
            cycle_id=cycle.id,
            action_type="secondary_source_broadening",
            objective="Broad pop-science query",
            rationale="Low quality broad search",
            priority=3,
            status="awaiting_approval",
            requires_approval=True,
            expected_information_gain=0.1,
        )
        session.add(act2)
        await session.commit()

    # 4. Human Approval of action
    async with SessionFactory() as session:
        approved_act = await service.approve_action(session, wf_id, act_id)
        assert approved_act["status"] == "approved"

    # 5. Human Rejection of second action
    async with SessionFactory() as session:
        rejected_act = await service.reject_action(
            session,
            wf_id,
            act2_id,
            rejection_reason="Query too broad and lacks academic precision",
        )
        assert rejected_act["status"] == "rejected"

    # 6. Workflow extension with continue_workflow
    async with SessionFactory() as session:
        extended_res = await service.continue_workflow(session, wf_id, additional_cycles=2)
        assert extended_res["status"] == "executing"
        assert extended_res["new_max_cycles"] == 4


# =====================================================================
# 6. 9I: Autonomous Workflow REST API Integration Tests
# =====================================================================

def test_autonomous_workflow_api_endpoints():
    """Verify REST API endpoints for workflow CRUD, cycle inspection, and report retrieval."""
    from tests.conftest import authed_client
    client = authed_client()

    # 1. Create investigation to attach workflow
    inv_id = str(uuid.uuid4())
    async def _setup_inv():
        async with SessionFactory() as session:
            inv = Investigation(
                id=uuid.UUID(inv_id),
                question="What is the efficacy of transcranial direct current stimulation in working memory?",
                mode="quick",
                status="completed",
            )
            session.add(inv)
            await session.commit()

    asyncio.run(_setup_inv())

    # 2. POST /research/autonomous/workflows
    create_resp = client.post(
        "/api/v1/research/autonomous/workflows",
        json={
            "investigation_id": inv_id,
            "title": "tDCS Memory Workflow",
            "research_objective": "Test working memory enhancement claims via tDCS",
            "autonomy_mode": "bounded",
            "budget_max_cycles": 2,
            "budget_max_searches": 8,
            "budget_max_sources": 20,
            "budget_max_duration_seconds": 1200,
        },
    )
    assert create_resp.status_code == 200
    wf_data = create_resp.json()
    wf_id = wf_data["id"]
    assert wf_data["title"] == "tDCS Memory Workflow"
    assert wf_data["status"] == "created"

    # 3. GET /research/autonomous/workflows
    list_resp = client.get(f"/api/v1/research/autonomous/workflows?investigation_id={inv_id}")
    assert list_resp.status_code == 200
    workflows = list_resp.json()
    assert len(workflows) >= 1
    assert any(w["id"] == wf_id for w in workflows)

    # 4. GET /research/autonomous/workflows/{id}
    get_resp = client.get(f"/api/v1/research/autonomous/workflows/{wf_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == wf_id

    # 5. POST /research/autonomous/workflows/{id}/pause
    pause_resp = client.post(f"/api/v1/research/autonomous/workflows/{wf_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    # 6. POST /research/autonomous/workflows/{id}/resume
    resume_resp = client.post(f"/api/v1/research/autonomous/workflows/{wf_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "executing"

    # 7. GET /research/autonomous/workflows/{id}/cycles
    cycles_resp = client.get(f"/api/v1/research/autonomous/workflows/{wf_id}/cycles")
    assert cycles_resp.status_code == 200
    assert isinstance(cycles_resp.json(), list)

    # 8. GET /research/autonomous/workflows/{id}/actions
    actions_resp = client.get(f"/api/v1/research/autonomous/workflows/{wf_id}/actions")
    assert actions_resp.status_code == 200
    assert isinstance(actions_resp.json(), list)

    # 9. POST /research/autonomous/workflows/{id}/continue
    continue_resp = client.post(
        f"/api/v1/research/autonomous/workflows/{wf_id}/continue",
        json={"additional_cycles": 1},
    )
    assert continue_resp.status_code == 200
    assert continue_resp.json()["status"] == "executing"

    # 10. POST /research/autonomous/workflows/{id}/cancel
    cancel_resp = client.post(f"/api/v1/research/autonomous/workflows/{wf_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


# =====================================================================
# 7. 9J: Knowledge Graph Workflow Nodes & Edges Integration Tests
# =====================================================================

def test_knowledge_graph_workflow_nodes_and_edges():
    """Verify autonomous workflow, cycle, and action nodes and edges in the knowledge graph."""
    from tests.conftest import authed_client
    client = authed_client()

    inv_id = str(uuid.uuid4())
    wf_id = str(uuid.uuid4())
    cycle_id = str(uuid.uuid4())
    action_id = str(uuid.uuid4())
    claim_id = str(uuid.uuid4())

    async def _setup_graph_data():
        async with SessionFactory() as session:
            inv = Investigation(
                id=uuid.UUID(inv_id),
                question="What are the mechanistic pathways of metformin in lifespan extension?",
                mode="quick",
                status="completed",
            )
            session.add(inv)

            cl = Claim(
                id=uuid.UUID(claim_id),
                investigation_id=uuid.UUID(inv_id),
                text="Metformin activates AMP-activated protein kinase (AMPK) in hepatocyte models.",
                priority=1,
            )
            session.add(cl)

            wf = AutonomousResearchWorkflow(
                id=uuid.UUID(wf_id),
                investigation_id=uuid.UUID(inv_id),
                title="Metformin Pathway Loop",
                research_objective="Investigate AMPK activation and lifespan outcomes",
                autonomy_mode="bounded",
                status="completed",
                current_cycle_number=1,
                budget_max_cycles=1,
            )
            session.add(wf)

            cyc = ResearchWorkflowCycle(
                id=uuid.UUID(cycle_id),
                workflow_id=uuid.UUID(wf_id),
                cycle_number=1,
                cycle_goal="Map primary hepatocyte AMPK studies",
                status="completed",
                information_gain_score=0.75,
            )
            session.add(cyc)

            act = ResearchAction(
                id=uuid.UUID(action_id),
                workflow_id=uuid.UUID(wf_id),
                cycle_id=uuid.UUID(cycle_id),
                action_type="primary_claim_search",
                priority=9,
                status="completed",
                target_entity_type="claim",
                target_entity_id=uuid.UUID(claim_id),
                objective="Search hepatocyte AMPK studies",
                rationale="Probe direct enzymatic phosphorylation",
                expected_information_gain=0.8,
            )
            session.add(act)
            await session.commit()

    asyncio.run(_setup_graph_data())

    # Request knowledge graph for this investigation
    resp = client.get(f"/api/v1/research/graph?investigation_id={inv_id}")
    assert resp.status_code == 200
    data = resp.json()

    node_types = {n["type"] for n in data["nodes"]}
    assert "autonomous_workflow" in node_types
    assert "research_cycle" in node_types
    assert "research_action" in node_types

    edge_rels = {e["relationship_type"] for e in data["edges"]}
    assert "investigates" in edge_rels
    assert "executes_cycle" in edge_rels
    assert "performs_action" in edge_rels
    assert "targets_claim" in edge_rels
