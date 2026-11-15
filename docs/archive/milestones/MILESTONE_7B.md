# NEOMON Milestone 7B — Advanced Report Intelligence & Synthesis

## Executive Overview

Milestone 7B transforms NEOMON's research synthesis capabilities from basic narrative summaries into a rigorous, standardized 18-section academic intelligence report. It introduces deterministic multi-dimensional evidence-strength scoring, complete claim-centered adjudication, immutable report versioning, and an interactive document-style report interface with clickable provenance citations.

**Tagline:** "Every claim is questioned. Every source is traced. Every conclusion is earned."

---

## Architecture & Implementation

### 1. Standardized 18-Section Research Report Schema
Every investigation report generates 18 structured sections:
1. `executive_summary`: High-level synthesis, verdict distribution, evidence strength score, and execution notices.
2. `research_question`: Exact research question, scope, time horizon, and operationalized definitions.
3. `investigation_scope`: Autonomous multi-agent investigation methodology and boundary parameters.
4. `search_strategy`: Academic vs institutional discovery distribution and query coverage.
5. `key_findings`: Bulleted findings summary derived strictly from evaluated claims.
6. `claim_by_claim_assessment`: Exhaustive adjudication verdict, rationale, and unresolved tensions per claim.
7. `supporting_evidence`: Passages directly substantiating claims with full bibliographic provenance.
8. `contradicting_evidence`: Conflicting, countervailing, or limitation passages with tension analysis.
9. `advocate_perspective`: Synthesis of arguments built in favor of hypotheses.
10. `skeptic_perspective`: Methodological falsification, failure modes, and alternative explanations.
11. `methodological_assessment`: Audit of study designs, sample sizes, and statistical validity.
12. `source_quality_assessment`: Evaluation of publisher reputation, institutional credibility, and DOI verification.
13. `citation_genealogy`: Citation network structure, foundation papers, and cross-publisher confirmation.
14. `temporal_intelligence`: Chronological distribution, recency, and temporal drift analysis.
15. `unresolved_questions`: Specific questions and ongoing debates that available literature cannot resolve.
16. `limitations`: Explicit retrieval boundaries, paywall limitations, and scope constraints.
17. `final_assessment`: Definitive verdict, evidence-strength rating, and synthesis.
18. `references_directory`: Complete catalog of cited sources, authors, DOIs, URLs, and passages.

### 2. Evidence-Strength Scoring Methodology
A deterministic score between `0.0` and `100.0` is computed across 5 weighted dimensions:
- **Source Independence (25 pts)**: Count of distinct publisher domains and institutional origins.
- **Source Quality (25 pts)**: Academic peer-reviewed (1.0x) vs institutional (0.85x) vs web (0.5x), scaled by relevance.
- **Full-Text Coverage (20 pts)**: Proportion of sources with resolved full-text documents vs metadata-only abstracts.
- **Methodological Rigor (15 pts)**: Ratio of direct empirical evidence vs contextual/indirect data.
- **Conflict Resolution (15 pts)**: Adjudication completeness and explicit resolution of conflicting evidence.
- **Tiers**:
  - `Very Strong` ($\ge 85.0$)
  - `Strong` ($70.0 - 84.9$)
  - `Moderate` ($50.0 - 69.9$)
  - `Weak` ($30.0 - 49.9$)
  - `Inconclusive` ($< 30.0$)

### 3. Report Versioning & Snapshotting
- **Data Model**: `ReportVersion` persists immutable version snapshots (`version_number: int`, `executive_summary`, `overall_assessment`, `evidence_strength_score`, `evidence_strength_tier`, `evidence_strength_json`, `sections_json`, `created_at`).
- **REST Endpoints**:
  - `GET /api/v1/research/investigations/{id}/reports`: Lists version history summaries.
  - `GET /api/v1/research/investigations/{id}/reports/{version_or_id}`: Retrieves full report snapshot for any version.
  - `POST /api/v1/research/investigations/{id}/reports/generate`: Regenerates and commits a new report version from latest evidence without re-running entire research pipelines.

### 4. Document-Style Report UI
- Interactive header displaying overall verdict, evidence strength score badge, and collapsible component breakdown drawer.
- Version history switcher pills allowing seamless toggling between report snapshots.
- Table of Contents navigation bar enabling instant jump-scrolling to any of the 18 sections.
- Clickable provenance citation tags that highlight and scroll to source evidence passages.
- Print stylesheet (`@media print`) optimizing clean output for physical printing or PDF export.

---

## Verification & Test Results
- **Backend Tests**: 69 unit and integration tests passing (`pytest tests/`).
  - Added `backend/tests/test_report_intelligence.py` verifying 18 section specifications, multi-tier evidence-strength scoring, snapshot persistence, and API version endpoints.
- **Frontend Verification**: TypeScript type-check (`tsc --noEmit`) and Node workspace UI test suite passing with 0 errors.
