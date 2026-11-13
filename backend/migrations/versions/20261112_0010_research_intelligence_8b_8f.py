"""Research intelligence milestones 8B through 8F.

Revision ID: 20261112_0010
Revises: 20261112_0009
Create Date: 2026-11-13 23:30:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20261112_0010"
down_revision = "20261112_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 8B: Hypotheses
    op.create_table(
        "research_hypotheses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="proposed"),
        sa.Column("claim_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("gap_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supporting_evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("challenging_evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("proposed_mechanism", sa.Text(), nullable=False, server_default=""),
        sa.Column("independent_variables_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("dependent_variables_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("expected_outcome", sa.Text(), nullable=False, server_default=""),
        sa.Column("boundary_conditions", sa.Text(), nullable=False, server_default=""),
        sa.Column("assumptions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confounding_variables_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("suggested_methodology", sa.Text(), nullable=False, server_default=""),
        sa.Column("falsification_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("generation_method", sa.String(40), nullable=False, server_default="deterministic"),
        sa.Column("confidence_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("testability_score", sa.Float(), nullable=False, server_default="7.0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="6.0"),
        sa.Column("evidence_grounding_score", sa.Float(), nullable=False, server_default="7.0"),
        sa.Column("falsifiability_score", sa.Float(), nullable=False, server_default="8.0"),
        sa.Column("evaluation_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_hypotheses_investigation_id", "research_hypotheses", ["investigation_id"])
    op.create_index("ix_research_hypotheses_category", "research_hypotheses", ["category"])
    op.create_index("ix_research_hypotheses_status", "research_hypotheses", ["status"])

    op.create_table(
        "hypothesis_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("research_hypotheses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_role", sa.String(60), nullable=False, server_default="hypothesis_evaluator"),
        sa.Column("status", sa.String(40), nullable=False, server_default="reviewed"),
        sa.Column("evidence_grounding_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("logical_consistency_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("falsifiability_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("testability_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("methodological_feasibility_score", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("review_comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_hypothesis_evaluations_hypothesis_id", "hypothesis_evaluations", ["hypothesis_id"])

    # 8C: Cross-investigation relationships & synthesis
    op.create_table(
        "cross_investigation_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("detection_method", sa.String(40), nullable=False, server_default="deterministic"),
        sa.Column("claim_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("shared_evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_cross_investigation_source_id", "cross_investigation_relationships", ["source_investigation_id"])
    op.create_index("ix_cross_investigation_target_id", "cross_investigation_relationships", ["target_investigation_id"])
    op.create_index("ix_cross_investigation_rel_type", "cross_investigation_relationships", ["relationship_type"])

    op.create_table(
        "investigation_synthesis_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("investigation_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("shared_themes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("common_findings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("complementary_findings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("conflicting_findings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("shared_evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("independent_corroboration_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("methodological_differences_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unresolved_questions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("cross_investigation_gaps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recommended_future_investigations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    # 8D: Contradictions
    op.create_table(
        "research_contradictions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("primary_investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secondary_investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="moderate"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("detection_method", sa.String(40), nullable=False, server_default="deterministic"),
        sa.Column("status", sa.String(40), nullable=False, server_default="newly_detected"),
        sa.Column("claim_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supporting_passages_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("conflicting_passages_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("scope_differences", sa.Text(), nullable=False, server_default=""),
        sa.Column("methodological_differences", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolution_explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_research_action", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_contradictions_primary_id", "research_contradictions", ["primary_investigation_id"])
    op.create_index("ix_research_contradictions_secondary_id", "research_contradictions", ["secondary_investigation_id"])
    op.create_index("ix_research_contradictions_category", "research_contradictions", ["category"])
    op.create_index("ix_research_contradictions_severity", "research_contradictions", ["severity"])
    op.create_index("ix_research_contradictions_status", "research_contradictions", ["status"])

    op.create_table(
        "contradiction_resolution_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contradiction_id", sa.Uuid(), sa.ForeignKey("research_contradictions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(40), nullable=False),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("resolution_rationale", sa.Text(), nullable=False),
        sa.Column("resolving_evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_contradiction_resolution_logs_id", "contradiction_resolution_logs", ["contradiction_id"])

    # 8E: Trends
    op.create_table(
        "research_trend_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("total_investigations_analyzed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sources_analyzed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_evidence_analyzed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("temporal_span_start", sa.String(80), nullable=True),
        sa.Column("temporal_span_end", sa.String(80), nullable=True),
        sa.Column("trend_topics_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("emerging_themes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("consensus_shifts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("persistent_gaps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("active_contradictions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_table(
        "research_trend_topics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("research_trend_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_name", sa.String(200), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("activity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("independence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("growth_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("contradiction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gap_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("temporal_observations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("investigation_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("summary_narrative", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_research_trend_topics_analysis_id", "research_trend_topics", ["analysis_id"])
    op.create_index("ix_research_trend_topics_name", "research_trend_topics", ["topic_name"])
    op.create_index("ix_research_trend_topics_class", "research_trend_topics", ["classification"])


def downgrade() -> None:
    op.drop_table("research_trend_topics")
    op.drop_table("research_trend_analyses")
    op.drop_table("contradiction_resolution_logs")
    op.drop_table("research_contradictions")
    op.drop_table("investigation_synthesis_reports")
    op.drop_table("cross_investigation_relationships")
    op.drop_table("hypothesis_evaluations")
    op.drop_table("research_hypotheses")
