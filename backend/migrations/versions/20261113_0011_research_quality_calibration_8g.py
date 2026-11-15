"""Research quality calibration and scientific evidence validation (Milestone 8G).

Revision ID: 20261113_0011
Revises: 20261112_0010
Create Date: 2026-11-14 00:45:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20261113_0011"
down_revision = "20261112_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 8G.1: Unified Source Credibility Assessments
    op.create_table(
        "source_credibility_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(60), nullable=False),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="unverified"),
        sa.Column("venue", sa.String(300), nullable=True),
        sa.Column("is_peer_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_source_credibility_assessments_source_id", "source_credibility_assessments", ["source_id"])
    op.create_index("ix_source_credibility_assessments_source_type", "source_credibility_assessments", ["source_type"])
    op.create_index("ix_source_credibility_assessments_status", "source_credibility_assessments", ["verification_status"])

    # 8G.2: Source Lineage & Independence Relationships
    op.create_table(
        "source_lineage_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(60), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("shared_identifiers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_source_lineage_relationships_source_id", "source_lineage_relationships", ["source_id"])
    op.create_index("ix_source_lineage_relationships_related_id", "source_lineage_relationships", ["related_source_id"])
    op.create_index("ix_source_lineage_relationships_type", "source_lineage_relationships", ["relationship_type"])

    # 8G.3: Evidence-to-Claim Entailment Validations
    op.create_table(
        "evidence_claim_validations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entailment_classification", sa.String(60), nullable=False),
        sa.Column("entailment_strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("missing_inferential_steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("correlation_vs_causation_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("validation_method", sa.String(40), nullable=False, server_default="deterministic_heuristic"),
        sa.Column("validator_model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="validated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_evidence_claim_validations_investigation_id", "evidence_claim_validations", ["investigation_id"])
    op.create_index("ix_evidence_claim_validations_claim_id", "evidence_claim_validations", ["claim_id"])
    op.create_index("ix_evidence_claim_validations_evidence_id", "evidence_claim_validations", ["evidence_id"])
    op.create_index("ix_evidence_claim_validations_classification", "evidence_claim_validations", ["entailment_classification"])

    # 8G.4: Research Quality Score Calibrations
    op.create_table(
        "research_quality_calibrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("calibrated_tier", sa.String(40), nullable=False, server_default="Moderate"),
        sa.Column("raw_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("calibrated_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("failure_penalty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dimension_breakdown_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("calibration_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_quality_calibrations_investigation_id", "research_quality_calibrations", ["investigation_id"])
    op.create_index("ix_research_quality_calibrations_tier", "research_quality_calibrations", ["calibrated_tier"])

    # 8G.5: Provider Failure Impacts
    op.create_table(
        "provider_failure_impacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("failure_type", sa.String(60), nullable=False),
        sa.Column("retry_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impact_severity", sa.String(40), nullable=False, server_default="harmless_optional"),
        sa.Column("missing_category", sa.String(100), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_provider_failure_impacts_investigation_id", "provider_failure_impacts", ["investigation_id"])
    op.create_index("ix_provider_failure_impacts_severity", "provider_failure_impacts", ["impact_severity"])


def downgrade() -> None:
    op.drop_table("provider_failure_impacts")
    op.drop_table("research_quality_calibrations")
    op.drop_table("evidence_claim_validations")
    op.drop_table("source_lineage_relationships")
    op.drop_table("source_credibility_assessments")
