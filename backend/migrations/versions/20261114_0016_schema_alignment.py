"""Align the live schema with the current ORM metadata.

Revision ID: 20261114_0016
Revises: 20261114_0015
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20261114_0016"
down_revision = "20261114_0015"
branch_labels = None
depends_on = None


def _rename_index(table: str, old_name: str, new_name: str, columns: list[str], unique: bool = False) -> None:
    op.drop_index(old_name, table_name=table, if_exists=True)
    op.create_index(new_name, table, columns, unique=unique, if_not_exists=True)


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    has_report_versions = False
    try:
        inspector = sa.inspect(bind)
        has_report_versions = inspector.has_table("report_versions")
    except Exception:
        has_report_versions = False

    if not has_report_versions:
        op.create_table(
            "report_versions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "investigation_id",
                sa.Uuid(),
                sa.ForeignKey("investigations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Uuid(),
                sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version_number", sa.Integer(), nullable=False, default=1),
            sa.Column("executive_summary", sa.Text(), nullable=False),
            sa.Column("overall_assessment", sa.String(32), nullable=False),
            sa.Column("evidence_gap", sa.Text(), nullable=True),
            sa.Column("evidence_strength_score", sa.Float(), nullable=False, default=0.0),
            sa.Column("evidence_strength_tier", sa.String(32), nullable=False, default="moderate"),
            sa.Column("evidence_strength_json", sa.Text(), nullable=False, default="{}"),
            sa.Column("sections_json", sa.Text(), nullable=False, default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_report_versions_investigation_id", "report_versions", ["investigation_id"], if_not_exists=True)
        op.create_index("ix_report_versions_job_id", "report_versions", ["job_id"], if_not_exists=True)
    else:
        if is_sqlite:
            with op.batch_alter_table("report_versions", recreate="always") as batch_op:
                batch_op.alter_column(
                    "created_at",
                    existing_type=sa.DateTime(),
                    nullable=False,
                )
        else:
            op.alter_column(
                "report_versions",
                "created_at",
                existing_type=sa.DateTime(),
                nullable=False,
            )

    if is_sqlite:
        with op.batch_alter_table("investigations", recreate="always") as batch_op:
            batch_op.create_foreign_key(
                "fk_investigations_workspace_id_workspaces",
                "workspaces",
                ["workspace_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_foreign_key(
                "fk_investigations_owner_id_users",
                "users",
                ["owner_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.create_foreign_key(
            "fk_investigations_workspace_id_workspaces",
            "investigations",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_investigations_owner_id_users",
            "investigations",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.drop_index("ix_comment_threads_target", table_name="comment_threads", if_exists=True)
    index_renames = [
        ("autonomous_research_workflows", "ix_autonomous_workflows_investigation_id", "ix_autonomous_research_workflows_investigation_id", ["investigation_id"]),
        ("autonomous_research_workflows", "ix_autonomous_workflows_status", "ix_autonomous_research_workflows_status", ["status"]),
        ("contradiction_resolution_logs", "ix_contradiction_resolution_logs_id", "ix_contradiction_resolution_logs_contradiction_id", ["contradiction_id"]),
        ("cross_investigation_relationships", "ix_cross_investigation_rel_type", "ix_cross_investigation_relationships_relationship_type", ["relationship_type"]),
        ("cross_investigation_relationships", "ix_cross_investigation_source_id", "ix_cross_investigation_relationships_source_investigation_id", ["source_investigation_id"]),
        ("cross_investigation_relationships", "ix_cross_investigation_target_id", "ix_cross_investigation_relationships_target_investigation_id", ["target_investigation_id"]),
        ("evidence_claim_validations", "ix_evidence_claim_validations_classification", "ix_evidence_claim_validations_entailment_classification", ["entailment_classification"]),
        ("password_reset_tokens", "ix_password_reset_tokens_hash", "ix_password_reset_tokens_token_hash", ["token_hash"], True),
        ("provider_failure_impacts", "ix_provider_failure_impacts_severity", "ix_provider_failure_impacts_impact_severity", ["impact_severity"]),
        ("research_actions", "ix_research_actions_type", "ix_research_actions_action_type", ["action_type"]),
        ("research_contradictions", "ix_research_contradictions_primary_id", "ix_research_contradictions_primary_investigation_id", ["primary_investigation_id"]),
        ("research_contradictions", "ix_research_contradictions_secondary_id", "ix_research_contradictions_secondary_investigation_id", ["secondary_investigation_id"]),
        ("research_quality_calibrations", "ix_research_quality_calibrations_investigation_id", "ix_research_quality_calibrations_investigation_id", ["investigation_id"], True),
        ("research_quality_calibrations", "ix_research_quality_calibrations_tier", "ix_research_quality_calibrations_calibrated_tier", ["calibrated_tier"]),
        ("research_query_histories", "ix_research_query_histories_normalized", "ix_research_query_histories_normalized_query", ["normalized_query"]),
        ("research_trend_topics", "ix_research_trend_topics_class", "ix_research_trend_topics_classification", ["classification"]),
        ("research_trend_topics", "ix_research_trend_topics_name", "ix_research_trend_topics_topic_name", ["topic_name"]),
        ("research_workflow_cycles", "ix_research_workflow_cycles_number", "ix_research_workflow_cycles_cycle_number", ["cycle_number"]),
        ("research_workflow_reports", "ix_research_workflow_reports_workflow_id", "ix_research_workflow_reports_workflow_id", ["workflow_id"], True),
        ("source_credibility_assessments", "ix_source_credibility_assessments_status", "ix_source_credibility_assessments_verification_status", ["verification_status"]),
        ("source_lineage_relationships", "ix_source_lineage_relationships_related_id", "ix_source_lineage_relationships_related_source_id", ["related_source_id"]),
        ("source_lineage_relationships", "ix_source_lineage_relationships_type", "ix_source_lineage_relationships_relationship_type", ["relationship_type"]),
        ("user_sessions", "ix_user_sessions_token_hash", "ix_user_sessions_session_token_hash", ["session_token_hash"], True),
    ]
    for table, old_name, new_name, columns, *unique in index_renames:
        _rename_index(table, old_name, new_name, columns, bool(unique and unique[0]))

    op.create_index("ix_comment_threads_created_by_id", "comment_threads", ["created_by_id"], if_not_exists=True)
    op.create_index("ix_comment_threads_target_entity_type", "comment_threads", ["target_entity_type"], if_not_exists=True)
    op.create_index("ix_comment_threads_target_entity_id", "comment_threads", ["target_entity_id"], if_not_exists=True)
    op.create_index("ix_evidence_annotations_author_id", "evidence_annotations", ["author_id"], if_not_exists=True)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], if_not_exists=True)
    op.create_index("ix_notifications_workspace_id", "notifications", ["workspace_id"], if_not_exists=True)
    op.create_index("ix_research_gaps_gap_type", "research_gaps", ["gap_type"], if_not_exists=True)
    op.create_index("ix_research_query_histories_action_id", "research_query_histories", ["action_id"], if_not_exists=True)
    op.create_index("ix_research_query_histories_cycle_id", "research_query_histories", ["cycle_id"], if_not_exists=True)
    op.create_index("ix_review_requests_requester_id", "review_requests", ["requester_id"], if_not_exists=True)
    op.create_index("ix_review_requests_target_type", "review_requests", ["target_type"], if_not_exists=True)
    op.create_index("ix_review_requests_target_id", "review_requests", ["target_id"], if_not_exists=True)
    op.create_index("ix_workspace_activities_actor_id", "workspace_activities", ["actor_id"], if_not_exists=True)
    op.create_index("ix_workspace_activities_created_at", "workspace_activities", ["created_at"], if_not_exists=True)
    op.create_index("ix_workspace_invitations_inviter_id", "workspace_invitations", ["inviter_id"], if_not_exists=True)


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    for table, name in [
        ("workspace_invitations", "ix_workspace_invitations_inviter_id"),
        ("workspace_activities", "ix_workspace_activities_created_at"),
        ("workspace_activities", "ix_workspace_activities_actor_id"),
        ("review_requests", "ix_review_requests_target_id"),
        ("review_requests", "ix_review_requests_target_type"),
        ("review_requests", "ix_review_requests_requester_id"),
        ("research_query_histories", "ix_research_query_histories_cycle_id"),
        ("research_query_histories", "ix_research_query_histories_action_id"),
        ("research_gaps", "ix_research_gaps_gap_type"),
        ("notifications", "ix_notifications_workspace_id"),
        ("notifications", "ix_notifications_created_at"),
        ("evidence_annotations", "ix_evidence_annotations_author_id"),
        ("comment_threads", "ix_comment_threads_created_by_id"),
        ("comment_threads", "ix_comment_threads_target_entity_id"),
        ("comment_threads", "ix_comment_threads_target_entity_type"),
    ]:
        op.drop_index(name, table_name=table, if_exists=True)
    op.create_index(
        "ix_comment_threads_target",
        "comment_threads",
        ["target_entity_type", "target_entity_id"],
        if_not_exists=True,
    )

    for table, old_name, new_name, columns, *unique in reversed(
        [
            ("autonomous_research_workflows", "ix_autonomous_workflows_investigation_id", "ix_autonomous_research_workflows_investigation_id", ["investigation_id"]),
            ("autonomous_research_workflows", "ix_autonomous_workflows_status", "ix_autonomous_research_workflows_status", ["status"]),
            ("contradiction_resolution_logs", "ix_contradiction_resolution_logs_id", "ix_contradiction_resolution_logs_contradiction_id", ["contradiction_id"]),
            ("cross_investigation_relationships", "ix_cross_investigation_rel_type", "ix_cross_investigation_relationships_relationship_type", ["relationship_type"]),
            ("cross_investigation_relationships", "ix_cross_investigation_source_id", "ix_cross_investigation_relationships_source_investigation_id", ["source_investigation_id"]),
            ("cross_investigation_relationships", "ix_cross_investigation_target_id", "ix_cross_investigation_relationships_target_investigation_id", ["target_investigation_id"]),
            ("evidence_claim_validations", "ix_evidence_claim_validations_classification", "ix_evidence_claim_validations_entailment_classification", ["entailment_classification"]),
            ("password_reset_tokens", "ix_password_reset_tokens_hash", "ix_password_reset_tokens_token_hash", ["token_hash"], True),
            ("provider_failure_impacts", "ix_provider_failure_impacts_severity", "ix_provider_failure_impacts_impact_severity", ["impact_severity"]),
            ("research_actions", "ix_research_actions_type", "ix_research_actions_action_type", ["action_type"]),
            ("research_contradictions", "ix_research_contradictions_primary_id", "ix_research_contradictions_primary_investigation_id", ["primary_investigation_id"]),
            ("research_contradictions", "ix_research_contradictions_secondary_id", "ix_research_contradictions_secondary_investigation_id", ["secondary_investigation_id"]),
            ("research_quality_calibrations", "ix_research_quality_calibrations_investigation_id", "ix_research_quality_calibrations_investigation_id", ["investigation_id"], True),
            ("research_quality_calibrations", "ix_research_quality_calibrations_tier", "ix_research_quality_calibrations_calibrated_tier", ["calibrated_tier"]),
            ("research_query_histories", "ix_research_query_histories_normalized", "ix_research_query_histories_normalized_query", ["normalized_query"]),
            ("research_trend_topics", "ix_research_trend_topics_class", "ix_research_trend_topics_classification", ["classification"]),
            ("research_trend_topics", "ix_research_trend_topics_name", "ix_research_trend_topics_topic_name", ["topic_name"]),
            ("research_workflow_cycles", "ix_research_workflow_cycles_number", "ix_research_workflow_cycles_cycle_number", ["cycle_number"]),
            ("research_workflow_reports", "ix_research_workflow_reports_workflow_id", "ix_research_workflow_reports_workflow_id", ["workflow_id"], True),
            ("source_credibility_assessments", "ix_source_credibility_assessments_status", "ix_source_credibility_assessments_verification_status", ["verification_status"]),
            ("source_lineage_relationships", "ix_source_lineage_relationships_related_id", "ix_source_lineage_relationships_related_source_id", ["related_source_id"]),
            ("source_lineage_relationships", "ix_source_lineage_relationships_type", "ix_source_lineage_relationships_relationship_type", ["relationship_type"]),
            ("user_sessions", "ix_user_sessions_token_hash", "ix_user_sessions_session_token_hash", ["session_token_hash"], True),
        ]
    ):
        _rename_index(table, new_name, old_name, columns, bool(unique and unique[0]))

    if is_sqlite:
        with op.batch_alter_table("investigations", recreate="always") as batch_op:
            batch_op.drop_constraint("fk_investigations_owner_id_users", type_="foreignkey")
            batch_op.drop_constraint("fk_investigations_workspace_id_workspaces", type_="foreignkey")
    else:
        op.drop_constraint("fk_investigations_owner_id_users", "investigations", type_="foreignkey")
        op.drop_constraint("fk_investigations_workspace_id_workspaces", "investigations", type_="foreignkey")
    # report_versions may have been created by create_all() before this
    # corrective migration. Keep the table and its records on downgrade.
