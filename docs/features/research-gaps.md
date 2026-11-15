# Feature Specification: Autonomous Research Gap Discovery Workspace

## 1. Feature Overview
The **Research Gap Discovery Engine** (`/gaps`) autonomously analyzes scientific literature to identify unaddressed questions, empirical blindspots, and evidentiary voids. It categorizes gaps into **Claim Gaps** (unsubstantiated assertions), **Evidence Gaps** (insufficient empirical data), **Perspective Gaps** (missing disciplinary angles), and **Subquestion Voids**, computing evidence coverage percentages and suggesting precise search queries to bridge identified gaps.

## 2. Purpose and Problem Solved
Identifying the "frontier of knowledge" is the most demanding step in academic research. Investigators often spend months reading literature only to realize their research question has already been answered, or conversely, that a critical foundational assumption remains untested. The Gap Discovery engine solves this by:
- Systematically calculating what percentage of a research question's sub-dimensions are supported by evidence.
- Exposing specific methodological and population voids (e.g. *"No long-term (>2 year) safety data exists for non-diabetic cohorts"*).
- Versioning gap analyses to show how subsequent evidence retrieval closes gaps over time.
- Generating actionable search queries designed specifically to target missing evidence.

## 3. Where Users Access It
- **Dedicated Route**: `/gaps` (Research Gap Discovery Workspace).
- **In-Investigation**: Gap Discovery tab on `/investigations/[id]`.
- **Knowledge Graph**: Research gap nodes (orange badges) on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/gaps`.
2. Select an investigation from the top dropdown.
3. Review the **Gap Discovery Summary**:
   - **Evidence Coverage Percentage**: Empirical metric (e.g. `31.4% Coverage`).
   - **Identified Gaps Count**: Total discrete gaps cataloged.
   - **Version Comparison**: Compares v1 (baseline) to v2 (post-retrieval) coverage progression.
4. Click **"Run Gap Discovery"**:
   - Triggers an algorithmic scan across all claims, evidence passages, and question dimensions.
5. Filter Gaps:
   - By **Severity**: Critical (invalidates core claim if unaddressed), High, Moderate, Low.
   - By **Category**: Claim Gaps, Evidence Gaps, Perspective Gaps, Subquestion Voids.
6. Inspect Individual Gap Cards:
   - **Evidentiary Justification**: Why this gap matters scientifically.
   - **Recommended Next Step**: Specific empirical or experimental action needed.
   - **Suggested Queries**: Ready-to-copy search strings tailored for academic search engines.
7. Click a suggested query to launch a targeted follow-up query in the investigation.

## 5. How the Feature Works Internally
1. The `app.analysis.gap_service`:
   - Deconstructs the investigation question into expected sub-facets (Mechanisms, Efficacy, Adverse Events, Population Subgroups, Longitudinal Durability).
   - Maps existing retrieved evidence against each facet.
   - Calculates **Evidence Coverage Score**:
     $$\text{Coverage Score} = \frac{\sum \text{Weights of Covered Facets}}{\text{Total Expected Facet Weights}} \times 100\%$$
2. For any facet where evidence count is zero or evidence confidence is weak ($<0.40$), the engine instantiates a `ResearchGap` entry.
3. Gap entries are assigned severity based on centrality to the primary hypothesis.
4. Results are stored in `research_gap_analyses` with version numbers (`v1`, `v2`, etc.) and individual gaps persisted in `research_gaps`.

## 6. Relevant Frontend Pages and Components
- `app/gaps/page.tsx`: Research Gap Discovery route.
- `components/research-gap-workspace.tsx`: Gap cards, severity badges, coverage meters, and version comparison views.
- `app/investigations/[id]/page.tsx`: Embedded gap discovery controls.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/investigations/{id}/gaps`: Retrieves the latest gap analysis for an investigation.
- `POST /api/v1/research/investigations/{id}/gaps/analyze`: Generates a new versioned gap analysis.
- `GET /api/v1/research/investigations/{id}/gaps/versions`: Lists all historical gap analysis versions.

## 8. Relevant Services and Agents
- `app.analysis.gap_service.GapDiscoveryEngine`: Mathematical coverage evaluator and gap synthesizer.
- `app.agents.methodology_auditor`: Epistemic auditor providing qualitative critique of missing perspectives.

## 9. Database Tables and Relationships
- `research_gap_analyses`: Parent analysis record (`id`, `investigation_id`, `version_number`, `coverage_score`, `summary`, `created_at`).
- `research_gaps`: Individual gap entries (`id`, `analysis_id`, `gap_type`, `severity`, `title`, `description`, `justification`, `recommended_action`, `suggested_queries_json`).
- `investigations`: Parent investigation.

## 10. Inputs and Outputs
- **Analysis Request (`ResearchGapAnalyzeRequest`)**:
  ```json
  {
    "provider_kind": "optional model override",
    "model": "optional model name"
  }
  ```
  *(Endpoint supports empty body via `Body(default=None)`)*.
- **Analysis Response (`ResearchGapAnalysisResponse`)**:
  JSON object with version number, coverage percentage, executive summary, and array of categorized gap objects.

## 11. AI Provider Dependencies
Optional. Facet coverage evaluation can run via deterministic entity-matching rules, enhanced by LLMs for nuanced qualitative gap description and query formulation.

## 12. External API Dependencies
None. Evaluates existing indexed workspace evidence.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Zero Evidence Found**: If an investigation has zero sources, coverage is reported as `0.0%`, and the engine flags the entire research question as an open void.
- **Resilient Request Parsing**: The `/analyze` POST route accepts empty body payloads cleanly.

## 15. Security and Permission Considerations
- Re-running gap analysis requires workspace write access (`researcher` or `admin`).
- Gap analyses are versioned immutably to preserve historical progress tracking.

## 16. Related Features and Dependencies
- **Hypothesis Generation** (`docs/features/hypothesis-generation.md`): Gaps serve as the primary seed for formulating new research hypotheses.
- **Autonomous Workflows** (`docs/features/autonomous-workflows.md`): Autonomous cycles target identified gaps to guide subsequent search actions.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_gap_discovery.py -q`
