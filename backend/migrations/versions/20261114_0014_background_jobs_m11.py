"""Production Background Job Infrastructure (Milestone 11).

Revision ID: 20261114_0014
Revises: 20261114_0013
Create Date: 2026-11-14 21:10:00
"""

import uuid
from alembic import op
import sqlalchemy as sa

revision = "20261114_0014"
down_revision = "20261114_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("target_entity_type", sa.String(64), nullable=False, server_default="investigation"),
        sa.Column("target_entity_id", sa.Uuid(), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("current_step", sa.String(255), nullable=True),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="1800"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(120), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_background_jobs_job_type", "background_jobs", ["job_type"])
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])
    op.create_index("ix_background_jobs_priority", "background_jobs", ["priority"])
    op.create_index("ix_background_jobs_target_entity_id", "background_jobs", ["target_entity_id"])
    op.create_index("ix_background_jobs_workspace_id", "background_jobs", ["workspace_id"])
    op.create_index("ix_background_jobs_owner_id", "background_jobs", ["owner_id"])
    op.create_index("ix_background_jobs_queued_at", "background_jobs", ["queued_at"])


def downgrade() -> None:
    op.drop_table("background_jobs")
