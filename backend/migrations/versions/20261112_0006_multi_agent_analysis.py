"""Add bounded multi-agent analysis persistence."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0006"
down_revision: Union[str, None] = "20261112_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("explanation", sa.Text(), server_default="", nullable=False))
    op.add_column("claims", sa.Column("priority", sa.Integer(), server_default="3", nullable=False))
    op.add_column("claims", sa.Column("search_objectives_json", sa.Text(), server_default="[]", nullable=False))
    op.add_column("claims", sa.Column("evidence_categories_json", sa.Text(), server_default="[]", nullable=False))
    op.add_column("claims", sa.Column("dependencies_json", sa.Text(), server_default="[]", nullable=False))

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("max_debate_rounds", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_concurrent_agents", sa.Integer(), server_default="1", nullable=False),
        sa.Column("provider_kind", sa.String(length=32), nullable=True),
        sa.Column("default_model", sa.String(length=200), nullable=True),
        sa.Column("role_models_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
    )
    op.create_index("ix_analysis_jobs_investigation_id", "analysis_jobs", ["investigation_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])

    op.create_table(
        "analysis_agent_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("agent_identifier", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("token_usage_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_agent_executions_job_id", "analysis_agent_executions", ["job_id"])
    op.create_index("ix_analysis_agent_executions_agent_identifier", "analysis_agent_executions", ["agent_identifier"])

    op.create_table(
        "agent_arguments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("agent_identifier", sa.String(length=80), nullable=False),
        sa.Column("argument_type", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("evidence_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("source_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("confidence_level", sa.String(length=24), nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["analysis_agent_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_arguments_job_id", "agent_arguments", ["job_id"])
    op.create_index("ix_agent_arguments_execution_id", "agent_arguments", ["execution_id"])
    op.create_index("ix_agent_arguments_claim_id", "agent_arguments", ["claim_id"])
    op.create_index("ix_agent_arguments_agent_identifier", "agent_arguments", ["agent_identifier"])

    op.create_table(
        "debate_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("moderator_summary", sa.Text(), nullable=False),
        sa.Column("unresolved_disagreements_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("requested_follow_up_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_debate_rounds_job_id", "debate_rounds", ["job_id"])

    op.create_table(
        "adjudication_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("supporting_argument_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("unresolved_disagreements_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adjudication_decisions_job_id", "adjudication_decisions", ["job_id"])
    op.create_index("ix_adjudication_decisions_claim_id", "adjudication_decisions", ["claim_id"])

    op.create_table(
        "research_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("overall_assessment", sa.String(length=32), nullable=False),
        sa.Column("evidence_gap", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_table(
        "report_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("section_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("claim_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("evidence_ids_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["research_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_sections_report_id", "report_sections", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_report_sections_report_id", table_name="report_sections")
    op.drop_table("report_sections")
    op.drop_table("research_reports")
    op.drop_index("ix_adjudication_decisions_claim_id", table_name="adjudication_decisions")
    op.drop_index("ix_adjudication_decisions_job_id", table_name="adjudication_decisions")
    op.drop_table("adjudication_decisions")
    op.drop_index("ix_debate_rounds_job_id", table_name="debate_rounds")
    op.drop_table("debate_rounds")
    op.drop_index("ix_agent_arguments_agent_identifier", table_name="agent_arguments")
    op.drop_index("ix_agent_arguments_claim_id", table_name="agent_arguments")
    op.drop_index("ix_agent_arguments_execution_id", table_name="agent_arguments")
    op.drop_index("ix_agent_arguments_job_id", table_name="agent_arguments")
    op.drop_table("agent_arguments")
    op.drop_index("ix_analysis_agent_executions_agent_identifier", table_name="analysis_agent_executions")
    op.drop_index("ix_analysis_agent_executions_job_id", table_name="analysis_agent_executions")
    op.drop_table("analysis_agent_executions")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_investigation_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_column("claims", "dependencies_json")
    op.drop_column("claims", "evidence_categories_json")
    op.drop_column("claims", "search_objectives_json")
    op.drop_column("claims", "priority")
    op.drop_column("claims", "explanation")
