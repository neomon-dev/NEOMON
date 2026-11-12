"""Add research relevance, extraction, and quality fields."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0004"
down_revision: Union[str, None] = "20261112_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investigations", sa.Column("quality_status", sa.String(length=32), server_default="insufficient_evidence", nullable=False))
    op.add_column("investigations", sa.Column("quality_summary", sa.Text(), nullable=True))
    op.add_column("investigations", sa.Column("relevant_source_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("investigations", sa.Column("full_text_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("investigations", sa.Column("evidence_gap", sa.Text(), nullable=True))

    op.add_column("sources", sa.Column("relevance_score", sa.Float(), server_default="0", nullable=False))
    op.add_column("sources", sa.Column("relevance_reasons_json", sa.Text(), server_default="[]", nullable=False))
    op.add_column("sources", sa.Column("inclusion_status", sa.String(length=24), server_default="included", nullable=False))
    op.add_column("sources", sa.Column("rejection_reason", sa.Text(), nullable=True))

    op.add_column("documents", sa.Column("access_level", sa.String(length=24), server_default="metadata_only", nullable=False))
    op.add_column("documents", sa.Column("extraction_quality", sa.String(length=24), server_default="low", nullable=False))

    op.add_column("evidence", sa.Column("document_id", sa.Uuid(), nullable=True))
    op.add_column("evidence", sa.Column("relevance_reason", sa.Text(), server_default="", nullable=False))
    op.add_column("evidence", sa.Column("traceable", sa.Boolean(), server_default=sa.true(), nullable=False))
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.create_foreign_key(
            "fk_evidence_document_id_documents",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])


def downgrade() -> None:
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.drop_constraint("fk_evidence_document_id_documents", type_="foreignkey")
    op.drop_column("evidence", "traceable")
    op.drop_column("evidence", "relevance_reason")
    op.drop_index("ix_evidence_document_id", table_name="evidence")
    op.drop_column("evidence", "document_id")
    op.drop_column("documents", "extraction_quality")
    op.drop_column("documents", "access_level")
    op.drop_column("sources", "rejection_reason")
    op.drop_column("sources", "inclusion_status")
    op.drop_column("sources", "relevance_reasons_json")
    op.drop_column("sources", "relevance_score")
    op.drop_column("investigations", "evidence_gap")
    op.drop_column("investigations", "full_text_count")
    op.drop_column("investigations", "relevant_source_count")
    op.drop_column("investigations", "quality_summary")
    op.drop_column("investigations", "quality_status")
