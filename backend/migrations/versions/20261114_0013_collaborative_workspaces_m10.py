"""Collaborative Research Intelligence & Multi-User Workspaces (Milestone 10).

Revision ID: 20261114_0013
Revises: 20261114_0012
Create Date: 2026-11-14 18:55:00
"""

import uuid
from alembic import op
import sqlalchemy as sa
from app.auth.security import hash_password

revision = "20261114_0013"
down_revision = "20261114_0012"
branch_labels = None
depends_on = None

DEFAULT_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="researcher"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. User sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token_hash", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["session_token_hash"], unique=True)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    # 3. Password reset tokens table
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_hash", "password_reset_tokens", ["token_hash"], unique=True)

    # 4. Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # 5. Workspace members table
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="researcher"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # 6. Workspace invitations table
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inviter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="researcher"),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_workspace_invitations_workspace_id", "workspace_invitations", ["workspace_id"])
    op.create_index("ix_workspace_invitations_email", "workspace_invitations", ["email"])
    op.create_index("ix_workspace_invitations_token_hash", "workspace_invitations", ["token_hash"], unique=True)

    # 7. Add workspace_id and owner_id columns to investigations
    op.add_column("investigations", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.add_column("investigations", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index("ix_investigations_workspace_id", "investigations", ["workspace_id"])
    op.create_index("ix_investigations_owner_id", "investigations", ["owner_id"])

    # 8. Comment threads table
    op.create_table(
        "comment_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("target_entity_type", sa.String(50), nullable=False),
        sa.Column("target_entity_id", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_comment_threads_workspace_id", "comment_threads", ["workspace_id"])
    op.create_index("ix_comment_threads_investigation_id", "comment_threads", ["investigation_id"])
    op.create_index("ix_comment_threads_target", "comment_threads", ["target_entity_type", "target_entity_id"])

    # 9. Comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("comment_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("parent_comment_id", sa.Uuid(), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_comments_thread_id", "comments", ["thread_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    # 10. Evidence annotations table
    op.create_table(
        "evidence_annotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("annotation_type", sa.String(50), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("reviewer_rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_evidence_annotations_workspace_id", "evidence_annotations", ["workspace_id"])
    op.create_index("ix_evidence_annotations_investigation_id", "evidence_annotations", ["investigation_id"])
    op.create_index("ix_evidence_annotations_evidence_id", "evidence_annotations", ["evidence_id"])

    # 11. Review requests table
    op.create_table(
        "review_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("target_version", sa.String(50), nullable=True),
        sa.Column("requester_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("requires_independent_review", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_review_requests_workspace_id", "review_requests", ["workspace_id"])
    op.create_index("ix_review_requests_investigation_id", "review_requests", ["investigation_id"])
    op.create_index("ix_review_requests_status", "review_requests", ["status"])

    # 12. Review decisions table
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_request_id", sa.Uuid(), sa.ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_review_decisions_review_request_id", "review_decisions", ["review_request_id"])
    op.create_index("ix_review_decisions_reviewer_id", "review_decisions", ["reviewer_id"])

    # 13. Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    # 14. Notification preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("in_app_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=True)

    # 15. Workspace activities table
    op.create_table(
        "workspace_activities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_workspace_activities_workspace_id", "workspace_activities", ["workspace_id"])
    op.create_index("ix_workspace_activities_action_type", "workspace_activities", ["action_type"])

    # 16. Seed default system/demo user and default workspace for backward compatibility
    # Seed default user: admin@neomon.ai / Password123!
    pwd_hash = hash_password("Password123!")
    users_tbl = sa.table(
        "users",
        sa.column("id", sa.Uuid),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("display_name", sa.String),
        sa.column("role", sa.String),
        sa.column("status", sa.String),
    )
    op.bulk_insert(
        users_tbl,
        [
            {
                "id": DEFAULT_ADMIN_ID,
                "email": "admin@neomon.ai",
                "password_hash": pwd_hash,
                "display_name": "NEOMON Lead Researcher",
                "role": "admin",
                "status": "active",
            }
        ],
    )

    # Seed default workspace: NEOMON Global Research Workspace
    workspaces_tbl = sa.table(
        "workspaces",
        sa.column("id", sa.Uuid),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("owner_id", sa.Uuid),
        sa.column("status", sa.String),
        sa.column("settings_json", sa.Text),
    )
    op.bulk_insert(
        workspaces_tbl,
        [
            {
                "id": DEFAULT_WORKSPACE_ID,
                "name": "NEOMON Global Research Workspace",
                "slug": "neomon-global",
                "description": "Primary collaborative research workspace for autonomous investigations.",
                "owner_id": DEFAULT_ADMIN_ID,
                "status": "active",
                "settings_json": '{"require_independent_review": true, "max_autonomous_budget": 50}',
            }
        ],
    )

    # Seed default workspace membership
    members_tbl = sa.table(
        "workspace_members",
        sa.column("id", sa.Uuid),
        sa.column("workspace_id", sa.Uuid),
        sa.column("user_id", sa.Uuid),
        sa.column("role", sa.String),
    )
    op.bulk_insert(
        members_tbl,
        [
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "user_id": DEFAULT_ADMIN_ID,
                "role": "owner",
            }
        ],
    )

    # Backfill historical investigations: associate all unassigned investigations with the default workspace
    investigations_tbl = sa.table(
        "investigations",
        sa.column("workspace_id", sa.Uuid),
        sa.column("owner_id", sa.Uuid),
    )
    op.execute(
        investigations_tbl.update()
        .where(investigations_tbl.c.workspace_id.is_(None))
        .values(workspace_id=DEFAULT_WORKSPACE_ID, owner_id=DEFAULT_ADMIN_ID)
    )


def downgrade() -> None:
    op.drop_table("workspace_activities")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
    op.drop_table("review_decisions")
    op.drop_table("review_requests")
    op.drop_table("evidence_annotations")
    op.drop_table("comments")
    op.drop_table("comment_threads")
    op.drop_column("investigations", "owner_id")
    op.drop_column("investigations", "workspace_id")
    op.drop_table("workspace_invitations")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_sessions")
    op.drop_table("users")
