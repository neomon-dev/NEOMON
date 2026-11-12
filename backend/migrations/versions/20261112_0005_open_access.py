"""Add open-access locations and document-version provenance."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0005"
down_revision: Union[str, None] = "20261112_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("open_access_status", sa.String(length=32), server_default="not_checked", nullable=False))
    op.add_column("sources", sa.Column("selected_document_url", sa.String(length=1000), nullable=True))
    op.add_column("sources", sa.Column("study_identity_key", sa.String(length=500), nullable=True))
    op.create_index("ix_sources_study_identity_key", "sources", ["study_identity_key"])
    op.add_column("documents", sa.Column("document_url", sa.String(length=1000), nullable=True))
    op.add_column("documents", sa.Column("version_type", sa.String(length=32), server_default="unknown", nullable=False))
    op.add_column("documents", sa.Column("access_route", sa.String(length=32), server_default="original", nullable=False))
    op.add_column("documents", sa.Column("metadata_match_status", sa.String(length=24), server_default="unknown", nullable=False))
    op.create_table(
        "open_access_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("repository", sa.String(length=300), nullable=True),
        sa.Column("version_type", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("license", sa.String(length=120), nullable=True),
        sa.Column("match_status", sa.String(length=24), server_default="unassessed", nullable=False),
        sa.Column("match_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("acquisition_status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_open_access_locations_source_id", "open_access_locations", ["source_id"])
    op.create_table(
        "document_version_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("related_document_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_version_relationships_source_id", "document_version_relationships", ["source_id"])
    op.create_index("ix_document_version_relationships_document_id", "document_version_relationships", ["document_id"])
    op.create_index(
        "ix_document_version_relationships_related_document_id",
        "document_version_relationships",
        ["related_document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_version_relationships_related_document_id", table_name="document_version_relationships")
    op.drop_index("ix_document_version_relationships_document_id", table_name="document_version_relationships")
    op.drop_index("ix_document_version_relationships_source_id", table_name="document_version_relationships")
    op.drop_table("document_version_relationships")
    op.drop_index("ix_open_access_locations_source_id", table_name="open_access_locations")
    op.drop_table("open_access_locations")
    op.drop_column("documents", "metadata_match_status")
    op.drop_column("documents", "access_route")
    op.drop_column("documents", "version_type")
    op.drop_column("documents", "document_url")
    op.drop_index("ix_sources_study_identity_key", table_name="sources")
    op.drop_column("sources", "study_identity_key")
    op.drop_column("sources", "selected_document_url")
    op.drop_column("sources", "open_access_status")
