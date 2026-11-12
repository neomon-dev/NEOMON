"""Remove the redundant non-unique agent identifier index."""

from typing import Sequence, Union

from alembic import op

revision: str = "20261112_0002"
down_revision: Union[str, None] = "20261112_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_agents_identifier", table_name="agents")


def downgrade() -> None:
    op.create_index("ix_agents_identifier", "agents", ["identifier"], unique=False)
