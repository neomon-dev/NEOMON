"""Persist evidence basis and report provenance."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0008"
down_revision: Union[str, None] = "20261112_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_arguments",
        sa.Column("evidence_basis", sa.String(length=16), server_default="none", nullable=False),
    )
    op.add_column(
        "adjudication_decisions",
        sa.Column("evidence_ids_json", sa.Text(), server_default="[]", nullable=False),
    )
    op.add_column(
        "report_sections",
        sa.Column("provenance_json", sa.Text(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("report_sections", "provenance_json")
    op.drop_column("adjudication_decisions", "evidence_ids_json")
    op.drop_column("agent_arguments", "evidence_basis")
