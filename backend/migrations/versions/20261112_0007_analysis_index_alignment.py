"""Align the analysis job uniqueness constraint with the ORM model."""

from typing import Sequence, Union

from alembic import op

revision: str = "20261112_0007"
down_revision: Union[str, None] = "20261112_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_analysis_jobs_investigation_id", table_name="analysis_jobs")


def downgrade() -> None:
    op.create_index("ix_analysis_jobs_investigation_id", "analysis_jobs", ["investigation_id"])
