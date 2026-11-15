# Feature Specification: Evidence Quality & Scientific Calibration

## 1. Feature Overview
The **Evidence Quality & Calibration Engine** evaluates scientific credibility across multi-dimensional criteria rather than relying on naive text sentiment. It computes empirical scores for peer-review status, journal venue reputation, sample size adequacy, study design rigor, citation lineage independence, and provider failure impacts, classifying investigations into calibrated quality tiers (`Strong`, `Moderate`, `Preliminary`, `Challenged`).

## 2. Purpose and Problem Solved
Standard LLM research tools treat all text identically: a post on an anonymous blog receives the same weight as a double-blind, randomized controlled trial published in *The New England Journal of Medicine*. NEOMON's Quality Calibration engine solves this fundamental epistemic flaw by:
- Differentiating primary peer-reviewed literature from unreviewed preprints and general web pages.
- Penalizing research syntheses when critical academic providers fail or return rate-limit errors.
- Validating inferential entailment between evidence passages and high-level claims.
- Flagging correlation versus causation fallacies.

## 3. Where Users Access It
- **Dedicated Route**: `/quality-audit` (Quality Audit & Calibration Workspace).
- **Telemetry Bar**: Quality badge and score meters on `/investigations/[id]`.
- **Dashboard Alert**: Quality status flags on `/`.

## 4. Step-by-Step User Workflow
1. Navigate to `/quality-audit`.
2. Select an investigation from the dropdown or inspect workspace-wide calibration metrics.
3. Review the **Calibration Breakdown**:
   - **Calibrated Score** (0.0 to 1.0): Final adjusted epistemic reliability score.
   - **Coverage Score**: Breadth of search queries and domain representation.
   - **Failure Penalty**: Penalty deducted if academic providers timed out or failed.
   - **Quality Tier**: Visual badge (`Strong`, `Moderate`, `Preliminary`, `Challenged`).
4. Inspect the **Dimension Breakdown Radar**:
   - Peer-review ratio.
   - Primary vs. secondary source distribution.
   - Entailment strength average.
   - Methodological limitation flags.
5. Review **Source Credibility Assessments**:
   - View per-source credibility scores (e.g., `0.95` for *Nature*, `0.70` for arXiv preprint).
   - View peer-review verification rationale.
6. Inspect **Provider Failure Impact Register**:
   - Check if arXiv, PubMed, or Tavily experienced API errors during data acquisition and view the assessed impact severity (`harmless_optional`, `moderate_gap`, `critical_omission`).

## 5. How the Feature Works Internally
1. **Source Credibility Assessment**:
   - As sources are indexed, the engine evaluates the venue (e.g. ISSN matching, Crossref container title).
   - Flag `is_peer_reviewed` is set to `True` for recognized peer-reviewed venues and `False` for preprints and web sources.
   - Assessment records are persisted in `source_credibility_assessments`.
2. **Entailment & Fallacy Check**:
   - Each claim-evidence pair is analyzed for inferential validity.
   - If a claim asserts causation (e.g. *"X causes Y"*) but the supporting evidence only establishes correlation, the engine sets `correlation_vs_causation_flag = True`.
3. **Score Calibration Formula**:
   $$\text{Raw Score} = w_{\text{peer}} \cdot S_{\text{peer}} + w_{\text{entail}} \cdot S_{\text{entail}} + w_{\text{coverage}} \cdot S_{\text{coverage}}$$
   $$\text{Calibrated Score} = \max(0.0, \text{Raw Score} - \text{Failure Penalty} - \text{Fallacy Penalty})$$
4. Tier Thresholds:
   - `Strong`: Score $\ge 0.80$ with $\ge 50\%$ peer-reviewed sources and zero unaddressed critical provider failures.
   - `Moderate`: Score $\ge 0.60$.
   - `Preliminary`: Score $\ge 0.40$ or dominated by preprints.
   - `Challenged`: Methodological flaws or correlation/causation fallacies detected.

## 6. Relevant Frontend Pages and Components
- `app/quality-audit/page.tsx`: Quality Audit Workspace page.
- `components/quality-audit-workspace.tsx`: Score breakdown cards, dimension meters, and provider failure tables.
- `components/source-intelligence.tsx`: Displays per-source credibility badges.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/quality-audit/{investigation_id}`: Retrieves complete calibration breakdown for an investigation.
- `POST /api/v1/research/quality-audit/{investigation_id}/recalibrate`: Triggers recalculation of quality metrics.
- `GET /api/v1/research/quality-audit/sources/{source_id}`: Fetches specific credibility assessment record.

## 8. Relevant Services and Agents
- `app.analysis.quality_service.QualityCalibrationEngine`: Core mathematical scoring and tier assignment service.
- `app.analysis.methodology_service`: Bias and fallacy detection heuristics.

## 9. Database Tables and Relationships
- `source_credibility_assessments`: Stores `source_id`, `verification_status`, `venue`, `is_peer_reviewed`, `is_primary`, `confidence`, `reasons_json`.
- `evidence_claim_validations`: Stores `investigation_id`, `claim_id`, `evidence_id`, `entailment_classification`, `entailment_strength`, `correlation_vs_causation_flag`.
- `research_quality_calibrations`: Stores `investigation_id`, `calibrated_tier`, `raw_score`, `calibrated_score`, `coverage_score`, `failure_penalty`, `dimension_breakdown_json`.
- `provider_failure_impacts`: Stores `investigation_id`, `provider`, `operation`, `failure_type`, `retry_attempts`, `impact_severity`.

## 10. Inputs and Outputs
- **Input**: `investigation_id` (UUID).
- **Output (`ResearchQualityCalibrationView`)**:
  JSON object containing calibrated tier, scores (raw, calibrated, coverage, failure penalty), dimension breakdown dictionary, and calibration reasons array.

## 11. AI Provider Dependencies
Optional. Venue lookup and mathematical scoring are fully deterministic. LLM assistance is used for deep inferential entailment classification when available.

## 12. External API Dependencies
None. Utilizes cached metadata and internal credibility rules.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Connection string.

## 14. Error Handling and Limitations
- **Missing Source Data**: If an indexed source lacks publisher metadata, it defaults to `unverified` and receives a conservative credibility weight (0.50) rather than failing.
- **Div-by-zero Protection**: Investigations with 0 claims or 0 sources assign default `Preliminary` tier with score `0.0`.

## 15. Security and Permission Considerations
- Recalibration requires workspace write permissions.
- Audit records cannot be deleted; historical calibrations are preserved for auditability.

## 16. Related Features and Dependencies
- **Methodology Audit** (`docs/features/methodology-audit.md`): Contributes bias and statistical power penalties to calibration.
- **Scientific Benchmarks** (`docs/features/benchmarks.md`): Evaluates calibration accuracy against gold-standard datasets.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_quality_calibration.py -q`
  - `python -m pytest backend/tests/test_scientific_calibration.py -q`
