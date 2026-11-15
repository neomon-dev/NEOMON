# NEOMON Milestone 8G — Research Quality Calibration & Scientific Evidence Validation

## Executive Overview

Milestone 8G represents NEOMON's core scientific reliability milestone. While previous milestones expanded research discovery, multi-agent debates, and cross-investigation intelligence, Milestone 8G ensures that research-quality ratings, evidence classifications, source credibility assessments, independence calculations, and research coverage scores accurately and defensibly represent the underlying scientific reality.

**Tagline:** "Every claim is questioned. Every source is traced. Every conclusion is earned."

---

## 1. Regression Benchmark Analysis & Root Cause Resolutions

### Benchmark A — "What role NVIDIA played in the era of AI?"
- **Historical Failure**: Quality was rated as `very_strong` despite coverage being only 66.5%, full-text documents at 9/20, 8 provider retrieval operations failed, and gap discovery reporting 0 peer-reviewed sources while the source catalogue labeled sources as `peer_reviewed`.
- **Root Cause Identified**:
  1. **DOI Conflation**: In `scientific_integrity.py`, line 231 checked `elif doi: st = SourceCredibilityType.PEER_REVIEWED; is_peer_reviewed = True`. Any source with a DOI (including corporate whitepapers, preprints, and open repository files) was automatically marked as peer-reviewed with a 0.95 score.
  2. **Subsystem Disconnect**: In `gap_service.py`, peer-reviewed sources were checked using `if cred.credibility_tier in { SourceCredibilityType.PEER_REVIEWED, ... }`. Since `credibility_tier` was a string such as `"authoritative"`, this condition evaluated to `False` for every source, incorrectly asserting zero peer-reviewed sources.
  3. **Independence Illusion**: The raw unique URL count was converted directly into an independence score, granting 25/25 independence points regardless of syndicated reporting.
  4. **Unpenalized Failures**: 8 failed provider retrieval operations had zero impact on the final score.
- **Milestone 8G Resolution**:
  - `SourceCredibilityAssessment` separates Source Type, Verification Status, and Evidence Quality Attributes. A DOI alone never grants peer-reviewed status.
  - Research coverage is decoupled from raw evidence strength: coverage < 70% caps the maximum tier at `Moderate`.
  - Provider retrieval failures incur explicit deductions (-12 to -20 pts for critical loss; -6 to -10 pts for significant coverage).
  - Benchmark A is now correctly calibrated to `Moderate` (calibrated score reflecting the 8 provider failures and sub-threshold coverage).

### Benchmark B — "How does AI contribute to RAM shortages?"
- **Historical Failure**: Five tech journalism websites reporting on the exact same press release were counted as five independent evidence clusters. Evidence observing that consumer RAM prices rose alongside AI hardware deployments was treated as causal proof of AI driving consumer RAM shortages.
- **Root Cause Identified**:
  1. Domain uniqueness was equated with research independence.
  2. Topical relevance and concurrent timelines were conflated with causal entailment.
- **Milestone 8G Resolution**:
  - `source_lineage.py` clusters syndicated publications, derivative reporting, and shared primary citations, collapsing the 5 articles into 1 effective cluster.
  - `entailment_service.py` evaluates logical entailment against claims, flags correlation-vs-causation co-occurrence without mechanism, and surfaces missing inferential steps.

---

## 2. Implemented Sub-Milestones

### 8G.1 — Unified Source Credibility Classification
Implemented in `backend/app/research/source_credibility.py`:
- **`CanonicalSourceType`**: `peer_reviewed_journal`, `academic_conference_proceeding`, `institutional_report`, `academic_preprint`, `technical_whitepaper`, `news_syndication`, `reputable_journalism`, `blog_editorial`, `unverified_web`.
- **`SourceVerificationStatus`**: `verified`, `high_confidence`, `unverified`, `disputed`, `self_declared`.
- **Rules Enforced**:
  - Preprints (arXiv, bioRxiv, etc.) have DOIs but are strictly classified as `academic_preprint` with `is_peer_reviewed = False`.
  - Open data/code repositories (Zenodo, Figshare, OSF) with DOIs are classified as `technical_whitepaper` / `unverified`.
  - Verified journals require recognized academic publisher or verified journal indexing.
  - Government and institutional reports (.gov, who.int, nih.gov) are recognized as primary institutional evidence (`is_primary = True`), but not academic peer review.

### 8G.2 — Source Independence & Publication Lineage
Implemented in `backend/app/research/source_lineage.py`:
- Rigorous lineage relationship detection:
  - `shared_primary_source`
  - `syndicated_publication`
  - `derivative_reporting`
  - `shared_authorship`
  - `shared_dataset`
  - `independent_research`
- Replaces raw URL counts with `effective_independent_count` based on connected lineage components.
- Computes `independence_ratio` to detect artificial consensus and domain-diversity illusions.

### 8G.3 — Evidence-to-Claim Entailment Validation
Implemented in `backend/app/analysis/entailment_service.py`:
- Deterministic semantic and inferential validation:
  - `direct_support`: Explicit causal mechanism and direct empirical proof.
  - `contextual_support`: Topical relevance or descriptive background without causal proof.
  - `direct_contradiction`: Empirical refutation or counter-evidence.
  - `mitigating`: Compensating factors or adaptive adjustments.
  - `methodological_limitation`: Sample size constraints, simulation vs empirical reality.
  - `insufficient_evidence`: Too brief or semantically disconnected.
- Automated `correlation_vs_causation_flag`: Detects concurrent timelines mistaken for causality.
- Explicit `missing_inferential_steps`: Documents logical gaps required to substantiate the claim.

### 8G.4 & 8G.5 — Research Quality Score Calibration & Failure Impact
Implemented in `backend/app/analysis/quality_calibration_service.py`:
- Calibrates 5 dimensions:
  1. `empirical_depth` (0–25)
  2. `source_credibility` (0–25)
  3. `methodological_rigor` (0–15)
  4. `consensus_stability` (0–15)
  5. `source_independence` (0–20)
- Enforces strict coverage prerequisites:
  - Coverage < 70% caps tier at `Moderate`.
  - Coverage < 85% caps tier at `Strong`.
  - `Very Strong` strictly requires calibrated score >= 85, coverage >= 80%, at least one verified peer-reviewed publication or primary study, and zero critical retrieval failures.
- Provider failure impact assessment:
  - `harmless_optional`: 0 penalty
  - `partial_coverage`: -3 pts
  - `significant_coverage`: -7 pts
  - `critical_loss`: -12 pts (and caps tier at Moderate)

### 8G.6 — Scientific Quality Audit Workspace
Implemented in:
- `components/quality-audit-workspace.tsx`
- `app/quality-audit/page.tsx`
- `components/app-shell.tsx` (navigation entry)
- `app/investigations/[id]/page.tsx` (direct quick-link button)
- **Workspace Features**:
  - Investigation selector with instant status overview.
  - 5 KPI summary cards: Calibrated Quality Tier, Calibrated vs Raw Score, Research Coverage progress, Verified Peer-Reviewed count, Effective Lineage Clusters count.
  - Tab 1: 5-Dimension Calibration Breakdown & Calibration Rationale.
  - Tab 2: Source Lineage & Independence Explorer (cluster cards, member counts, explanations).
  - Tab 3: Evidence Entailment Matrix (filterable by classification, correlation alerts, missing inferential steps).
  - Tab 4: Provider Retrieval Failure Impact Log (severity badges, query details, missing categories).

### 8G.7 — Export Integration Across All 9 Formats
Updated in `backend/app/analysis/export_service.py`:
1. **Markdown Export**: Adds Calibrated Research Quality callout box with score, tier, coverage %, failure penalty, and rationale.
2. **PDF Export**: Running header and summary box displays calibrated quality tier and score.
3. **Structured JSON Export**: Contains `quality_calibration` object, canonical credibility per source, and entailment validation per evidence passage.
4. **Interactive HTML Graph**: Embeds calibrated quality metadata in central node and detail views.
5. **SVG Graph**: Visual banner showcases calibrated quality tier badge.
6. **JSON-LD Linked Data**: Includes schema.org `scientificQuality` / `QualityAssessment` block.
7. **Evidence CSV**: Adds `entailment_classification`, `correlation_vs_causation`, and `missing_inferential_steps` columns.
8. **Sources CSV**: Adds `canonical_source_type`, `verification_status`, `is_peer_reviewed`, and `is_primary` columns.
9. **Export Manifest**: Returns calibrated quality metrics in export metadata.

---

## 3. Database Migration

- Alembic revision: `20261113_0011` (`backend/migrations/versions/20261113_0011_research_quality_calibration_8g.py`).
- New tables:
  - `source_credibility_assessments`
  - `source_lineage_relationships`
  - `evidence_claim_validations`
  - `research_quality_calibrations`
  - `provider_failure_impacts`
- Successfully applied and upgraded to head.

---

## 4. Verification & Validation Summary

| Test Suite | Result | Details |
|---|---|---|
| Backend Pytest (`backend/tests/`) | **142 passed** (100%) | 142 passed in 10.43s, including 6 dedicated 8G tests and regression benchmarks |
| Dedicated Calibration Tests | **6 passed** (100%) | `test_canonical_source_credibility_separation`, `test_source_lineage_and_syndication_clustering`, `test_evidence_claim_entailment_validation`, `test_regression_benchmark_a_nvidia`, `test_regression_benchmark_b_ram_shortages`, `test_quality_audit_api_integration` |
| Frontend Unit Tests (`npm test`) | **9 passed** (100%) | All workspace and UI tests passed in 621ms |
| TypeScript Check (`npx tsc --noEmit`) | **0 errors** | Clean pass |
| Next.js Build (`npm run build`) | **18 routes compiled** | All static and dynamic routes compiled cleanly with Turbopack |
