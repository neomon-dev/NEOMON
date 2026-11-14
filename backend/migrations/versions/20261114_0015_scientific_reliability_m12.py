"""Milestone 12: Research Intelligence Validation, Reproducibility & Scientific Reliability

Revision ID: 20261114_0015
Revises: 20261114_0014
Create Date: 2026-11-14 21:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261114_0015"
down_revision = "20261114_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. evidence_verification_records
    op.create_table(
        "evidence_verification_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("exact_passage_text", sa.Text(), nullable=False),
        sa.Column("passage_location", sa.String(length=256), nullable=True),
        sa.Column("source_publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieval_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relationship_classification", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verification_method", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_meaning", sa.String(length=128), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("agent_or_process", sa.String(length=64), nullable=False),
        sa.Column("model_provider_info", sa.String(length=128), nullable=True),
        sa.Column("is_challenged", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("challenge_reason", sa.Text(), nullable=True),
        sa.Column("corrected_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corrected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_verification_records_claim_id"), "evidence_verification_records", ["claim_id"], unique=False)
    op.create_index(op.f("ix_evidence_verification_records_evidence_id"), "evidence_verification_records", ["evidence_id"], unique=False)
    op.create_index(op.f("ix_evidence_verification_records_investigation_id"), "evidence_verification_records", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_evidence_verification_records_relationship_classification"), "evidence_verification_records", ["relationship_classification"], unique=False)
    op.create_index(op.f("ix_evidence_verification_records_source_id"), "evidence_verification_records", ["source_id"], unique=False)
    op.create_index(op.f("ix_evidence_verification_records_verification_status"), "evidence_verification_records", ["verification_status"], unique=False)

    # 2. claim_synthesis_results
    op.create_table(
        "claim_synthesis_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("relevant_sources_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_underlying_studies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("direct_supporting_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_supporting_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contradicting_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contextual_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unverified_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("methodological_limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("publication_date_distribution_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source_independence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("important_missing_evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("outstanding_verification_operations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("synthesis_outcome", sa.String(length=64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_synthesis_results_claim_id"), "claim_synthesis_results", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_synthesis_results_investigation_id"), "claim_synthesis_results", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_claim_synthesis_results_synthesis_outcome"), "claim_synthesis_results", ["synthesis_outcome"], unique=False)

    # 3. study_independence_clusters
    op.create_table(
        "study_independence_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_label", sa.String(length=128), nullable=False),
        sa.Column("primary_source_id", sa.Uuid(), nullable=True),
        sa.Column("member_source_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("relationship_category", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_rationale", sa.Text(), nullable=False),
        sa.Column("shared_attributes_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_study_independence_clusters_investigation_id"), "study_independence_clusters", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_study_independence_clusters_relationship_category"), "study_independence_clusters", ["relationship_category"], unique=False)

    # 4. methodology_audit_findings
    op.create_table(
        "methodology_audit_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("audit_dimension", sa.String(length=64), nullable=False),
        sa.Column("issue_severity", sa.String(length=32), nullable=False),
        sa.Column("finding_title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("linked_source_id", sa.Uuid(), nullable=True),
        sa.Column("linked_passage_text", sa.Text(), nullable=True),
        sa.Column("missing_data_condition", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_methodology_audit_findings_audit_dimension"), "methodology_audit_findings", ["audit_dimension"], unique=False)
    op.create_index(op.f("ix_methodology_audit_findings_investigation_id"), "methodology_audit_findings", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_methodology_audit_findings_issue_severity"), "methodology_audit_findings", ["issue_severity"], unique=False)

    # 5. research_execution_manifests
    op.create_table(
        "research_execution_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("research_question", sa.Text(), nullable=False),
        sa.Column("config_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("claim_decomposition_version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("search_queries_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("providers_used_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("execution_timeline_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_manifest_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_manifest_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("quality_assessment_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("reproducibility_status", sa.String(length=32), nullable=False, server_default="fully_reproducible"),
        sa.Column("reproducibility_notes", sa.Text(), nullable=True),
        sa.Column("parent_reproduced_manifest_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_execution_manifests_investigation_id"), "research_execution_manifests", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_research_execution_manifests_manifest_hash"), "research_execution_manifests", ["manifest_hash"], unique=False)

    # 6. benchmark_datasets
    op.create_table(
        "benchmark_datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("research_question", sa.Text(), nullable=False),
        sa.Column("expected_claims_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("verified_source_references_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("expected_support_classifications_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("known_counterevidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("known_methodological_limitations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("expected_conclusion", sa.Text(), nullable=False, server_default=""),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_datasets_category"), "benchmark_datasets", ["category"], unique=False)
    op.create_index(op.f("ix_benchmark_datasets_slug"), "benchmark_datasets", ["slug"], unique=True)

    # 7. benchmark_runs
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_dataset_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=True),
        sa.Column("run_version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("retrieval_metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("synthesis_metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("operations_metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("overall_evaluation_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["benchmark_dataset_id"], ["benchmark_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_runs_benchmark_dataset_id"), "benchmark_runs", ["benchmark_dataset_id"], unique=False)
    op.create_index(op.f("ix_benchmark_runs_status"), "benchmark_runs", ["status"], unique=False)

    # 8. human_evidence_corrections
    op.create_table(
        "human_evidence_corrections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("correction_type", sa.String(length=64), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_human_evidence_corrections_claim_id"), "human_evidence_corrections", ["claim_id"], unique=False)
    op.create_index(op.f("ix_human_evidence_corrections_correction_type"), "human_evidence_corrections", ["correction_type"], unique=False)
    op.create_index(op.f("ix_human_evidence_corrections_evidence_id"), "human_evidence_corrections", ["evidence_id"], unique=False)
    op.create_index(op.f("ix_human_evidence_corrections_investigation_id"), "human_evidence_corrections", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_human_evidence_corrections_user_id"), "human_evidence_corrections", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("human_evidence_corrections")
    op.drop_table("benchmark_runs")
    op.drop_table("benchmark_datasets")
    op.drop_table("research_execution_manifests")
    op.drop_table("methodology_audit_findings")
    op.drop_table("study_independence_clusters")
    op.drop_table("claim_synthesis_results")
    op.drop_table("evidence_verification_records")
