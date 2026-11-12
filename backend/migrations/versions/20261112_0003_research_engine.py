"""Add research engine persistence tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0003"
down_revision: Union[str, None] = "20261112_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_column() -> sa.Uuid:
    return sa.Uuid()


def upgrade() -> None:
    op.add_column("investigations", sa.Column("mode", sa.String(length=16), server_default="quick", nullable=False))
    op.add_column("investigations", sa.Column("timeframe", sa.String(length=120), nullable=True))
    op.create_table(
        "research_queries",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("investigation_id", uuid_column(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_queries_investigation_id", "research_queries", ["investigation_id"])
    op.create_table(
        "sources",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("investigation_id", uuid_column(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=False),
        sa.Column("original_url", sa.String(length=1000), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("authors_json", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.String(length=80), nullable=True),
        sa.Column("doi", sa.String(length=300), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_investigation_id", "sources", ["investigation_id"])
    op.create_index("ix_sources_canonical_url", "sources", ["canonical_url"])
    op.create_index("ix_sources_doi", "sources", ["doi"])
    op.create_index("ix_sources_content_hash", "sources", ["content_hash"])
    op.create_table(
        "documents",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("source_id", uuid_column(), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("headings_json", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_source_id", "documents", ["source_id"])
    op.create_table(
        "claims",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("investigation_id", uuid_column(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_investigation_id", "claims", ["investigation_id"])
    op.create_table(
        "evidence",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("source_id", uuid_column(), nullable=False),
        sa.Column("claim_id", uuid_column(), nullable=True),
        sa.Column("exact_text", sa.Text(), nullable=False),
        sa.Column("surrounding_context", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(length=24), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_name", sa.String(length=300), nullable=True),
        sa.Column("retrieval_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])
    op.create_table(
        "claim_evidence_relationships",
        sa.Column("id", uuid_column(), nullable=False),
        sa.Column("claim_id", uuid_column(), nullable=False),
        sa.Column("evidence_id", uuid_column(), nullable=False),
        sa.Column("relationship_type", sa.String(length=24), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claim_evidence_relationships_claim_id", "claim_evidence_relationships", ["claim_id"])
    op.create_index("ix_claim_evidence_relationships_evidence_id", "claim_evidence_relationships", ["evidence_id"])
    for table_name in ("search_provider_executions", "extraction_executions"):
        if table_name == "search_provider_executions":
            columns = [
                sa.Column("id", uuid_column(), nullable=False),
                sa.Column("investigation_id", uuid_column(), nullable=False),
                sa.Column("provider", sa.String(length=64), nullable=False),
                sa.Column("query", sa.Text(), nullable=False),
                sa.Column("status", sa.String(length=24), nullable=False),
                sa.Column("error_message", sa.Text(), nullable=True),
                sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
                sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
                sa.PrimaryKeyConstraint("id"),
            ]
        else:
            columns = [
                sa.Column("id", uuid_column(), nullable=False),
                sa.Column("source_id", uuid_column(), nullable=False),
                sa.Column("status", sa.String(length=24), nullable=False),
                sa.Column("error_message", sa.Text(), nullable=True),
                sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
                sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
                sa.PrimaryKeyConstraint("id"),
            ]
        op.create_table(table_name, *columns)
    op.create_index("ix_search_provider_executions_investigation_id", "search_provider_executions", ["investigation_id"])
    op.create_index("ix_extraction_executions_source_id", "extraction_executions", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_extraction_executions_source_id", table_name="extraction_executions")
    op.drop_table("extraction_executions")
    op.drop_index("ix_search_provider_executions_investigation_id", table_name="search_provider_executions")
    op.drop_table("search_provider_executions")
    op.drop_index("ix_claim_evidence_relationships_evidence_id", table_name="claim_evidence_relationships")
    op.drop_index("ix_claim_evidence_relationships_claim_id", table_name="claim_evidence_relationships")
    op.drop_table("claim_evidence_relationships")
    op.drop_index("ix_evidence_claim_id", table_name="evidence")
    op.drop_index("ix_evidence_source_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_claims_investigation_id", table_name="claims")
    op.drop_table("claims")
    op.drop_index("ix_documents_source_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_sources_content_hash", table_name="sources")
    op.drop_index("ix_sources_doi", table_name="sources")
    op.drop_index("ix_sources_canonical_url", table_name="sources")
    op.drop_index("ix_sources_investigation_id", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_research_queries_investigation_id", table_name="research_queries")
    op.drop_table("research_queries")
    op.drop_column("investigations", "timeframe")
    op.drop_column("investigations", "mode")
