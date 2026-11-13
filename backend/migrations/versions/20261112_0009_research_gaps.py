"""Persist autonomous research gaps and gap analysis versions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0009"
down_revision: Union[str, None] = "20261112_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_gap_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moderate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("coverage_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_research_gap_analyses_investigation_id"),
        "research_gap_analyses",
        ["investigation_id"],
        unique=False,
    )

    op.create_table(
        "research_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("gap_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("claim_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supporting_explanation", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("research_priority", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("is_observed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("recommended_action_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["research_gap_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_gaps_analysis_id"), "research_gaps", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_research_gaps_investigation_id"), "research_gaps", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_research_gaps_category"), "research_gaps", ["category"], unique=False)
    op.create_index(op.f("ix_research_gaps_severity"), "research_gaps", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_research_gaps_severity"), table_name="research_gaps")
    op.drop_index(op.f("ix_research_gaps_category"), table_name="research_gaps")
    op.drop_index(op.f("ix_research_gaps_investigation_id"), table_name="research_gaps")
    op.drop_index(op.f("ix_research_gaps_analysis_id"), table_name="research_gaps")
    op.drop_table("research_gaps")
    op.drop_index(op.f("ix_research_gap_analyses_investigation_id"), table_name="research_gap_analyses")
    op.drop_table("research_gap_analyses")
