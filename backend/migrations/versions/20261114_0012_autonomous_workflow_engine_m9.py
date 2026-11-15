"""Autonomous Research Workflow Engine (Milestone 9).

Revision ID: 20261114_0012
Revises: 20261113_0011
Create Date: 2026-11-14 16:35:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20261114_0012"
down_revision = "20261113_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Autonomous Research Workflows table
    op.create_table(
        "autonomous_research_workflows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="created"),
        sa.Column("autonomy_mode", sa.String(30), nullable=False, server_default="bounded"),
        sa.Column("current_cycle_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cycles_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stopping_reason", sa.String(50), nullable=True),
        sa.Column("stopping_explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("scientific_confidence", sa.String(30), nullable=False, server_default="medium"),
        sa.Column("budget_max_cycles", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("budget_max_searches", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("budget_max_sources", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("budget_max_documents", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("budget_max_llm_calls", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("budget_max_duration_seconds", sa.Integer(), nullable=False, server_default="1800"),
        sa.Column("budget_max_consecutive_low_value", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("spent_searches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spent_sources", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spent_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spent_llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_low_value_cycles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_autonomous_workflows_investigation_id", "autonomous_research_workflows", ["investigation_id"])
    op.create_index("ix_autonomous_workflows_status", "autonomous_research_workflows", ["status"])

    # 2. Research Workflow Cycles table
    op.create_table(
        "research_workflow_cycles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("cycle_goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
        sa.Column("actions_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actions_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actions_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_acquired", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_acquired", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claims_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contradictions_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gaps_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("information_gain_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evaluation_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_research_workflow_cycles_workflow_id", "research_workflow_cycles", ["workflow_id"])
    op.create_index("ix_research_workflow_cycles_number", "research_workflow_cycles", ["cycle_number"])

    # 3. Research Actions table
    op.create_table(
        "research_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), sa.ForeignKey("research_workflow_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(60), nullable=False),
        sa.Column("target_entity_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("target_entity_id", sa.Uuid(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("search_queries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("target_providers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("expected_information_gain", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("dependencies_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approval_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("execution_result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_research_actions_workflow_id", "research_actions", ["workflow_id"])
    op.create_index("ix_research_actions_cycle_id", "research_actions", ["cycle_id"])
    op.create_index("ix_research_actions_type", "research_actions", ["action_type"])
    op.create_index("ix_research_actions_status", "research_actions", ["status"])

    # 4. Checkpoints table
    op.create_table(
        "research_workflow_checkpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkpoint_type", sa.String(50), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_workflow_checkpoints_workflow_id", "research_workflow_checkpoints", ["workflow_id"])

    # 5. Query History table
    op.create_table(
        "research_query_histories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), sa.ForeignKey("research_workflow_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_id", sa.Uuid(), sa.ForeignKey("research_actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevant_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effectiveness_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_counter_evidence_query", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_query_histories_workflow_id", "research_query_histories", ["workflow_id"])
    op.create_index("ix_research_query_histories_normalized", "research_query_histories", ["normalized_query"])

    # 6. Workflow Reports table
    op.create_table(
        "research_workflow_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("initial_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("final_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("cycles_summary_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("total_queries_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sources_acquired", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_evidence_extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claims_reassessed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contradictions_resolved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_uncertainties_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recommended_next_actions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("stopping_reason", sa.String(50), nullable=False),
        sa.Column("stopping_explanation", sa.Text(), nullable=False),
        sa.Column("calibrated_quality_tier", sa.String(40), nullable=False, server_default="Moderate"),
        sa.Column("calibrated_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_workflow_reports_workflow_id", "research_workflow_reports", ["workflow_id"])
    op.create_index("ix_research_workflow_reports_investigation_id", "research_workflow_reports", ["investigation_id"])


def downgrade() -> None:
    op.drop_table("research_workflow_reports")
    op.drop_table("research_query_histories")
    op.drop_table("research_workflow_checkpoints")
    op.drop_table("research_actions")
    op.drop_table("research_workflow_cycles")
    op.drop_table("autonomous_research_workflows")
