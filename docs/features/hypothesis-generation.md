# Feature Specification: Scientific Hypothesis Generation Engine

## 1. Feature Overview
The **Scientific Hypothesis Generation Engine** (`/hypotheses`) formulates novel, testable, and falsifiable scientific hypotheses by analyzing evidence gaps, resolving contradictions, and bridging cross-disciplinary concepts. It evaluates generated hypotheses on two objective quantitative scales: **Testability Score** (feasibility of experimental validation) and **Plausibility Rating** (grounding in established physical and biological laws), producing actionable experimental proposals.

## 2. Purpose and Problem Solved
Generating original scientific hypotheses typically relies on serendipity or individual researcher intuition. AI tools frequently produce either trivial common-sense statements or wild, ungrounded speculation. NEOMON's Hypothesis Generation engine provides systematic abduction and induction:
- Seeds hypothesis generation with verified empirical evidence gaps.
- Synthesizes findings across distinct research domains to propose cross-cutting mechanisms.
- Enforces strict Popperian falsifiability criteria.
- Outlines concrete experimental protocols (required sample size, controls, independent variables).

## 3. Where Users Access It
- **Dedicated Route**: `/hypotheses` (Hypothesis Generation Workspace).
- **In-Investigation**: Hypotheses tab on `/investigations/[id]`.
- **Knowledge Graph**: Hypothesis nodes (purple badges) on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/hypotheses`.
2. Select an active investigation from the dropdown.
3. Review the **Hypothesis Generation Overview**:
   - Total generated hypotheses.
   - Average testability score.
   - High-plausibility candidate count.
4. Click **"Generate Novel Hypotheses"**:
   - The engine ingests the investigation's verified claims, evidence gaps, and contradictions.
   - Synthesizes 3 to 5 candidate hypotheses.
5. Review **Hypothesis Cards**:
   - **Hypothesis Statement**: Clear, falsifiable scientific proposition.
   - **Theoretical Rationale**: Scientific grounding and deductive reasoning.
   - **Testability Score** (0.0 to 1.0): Assessment of whether modern instruments/trials can test the hypothesis.
   - **Plausibility Score** (0.0 to 1.0): Compatibility with established empirical literature.
   - **Proposed Experimental Protocol**: Step-by-step validation methodology, recommended assay/trial design, and primary endpoint metrics.
6. Click **"Evaluate Feasibility"** to recalculate testability metrics based on updated literature.

## 5. How the Feature Works Internally
1. The `app.analysis.hypothesis_service`:
   - Retrieves all `ResearchGap` and `ResearchContradiction` entries linked to the investigation.
   - Constructs an abductive reasoning prompt pairing identified limitations with cross-domain empirical analogies.
   - Instructs the model to generate structured candidates adhering to `HypothesisCandidate` schemas.
2. Falsifiability & Testability Scoring:
   - Scans candidate text for concrete measurable variables, control groups, and clear null hypotheses ($H_0$).
   - Calculates **Testability Score**:
     $$\text{Testability} = 0.4 \times \text{Specificity} + 0.3 \times \text{Measurability} + 0.3 \times \text{Protocol Completeness}$$
3. Results are saved in the `research_hypotheses` and `hypothesis_evaluations` tables.

## 6. Relevant Frontend Pages and Components
- `app/hypotheses/page.tsx`: Hypothesis generation page container.
- `components/hypothesis-workspace.tsx`: Candidate cards, feasibility meters, and experimental protocol modal.
- `components/graph-detail-panel.tsx`: Inspector for hypothesis nodes in the Knowledge Graph.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/investigations/{id}/hypotheses`: Retrieves generated hypotheses for an investigation.
- `POST /api/v1/research/investigations/{id}/hypotheses/generate`: Triggers novel hypothesis generation.
- `POST /api/v1/research/hypotheses/{id}/evaluate`: Runs a detailed experimental feasibility audit.

## 8. Relevant Services and Agents
- `app.analysis.hypothesis_service.HypothesisEngine`: Abductive reasoning and scoring service.
- `app.agents.decomposer`: Assists in breaking hypotheses into testable operational variables.

## 9. Database Tables and Relationships
- `research_hypotheses`: Stores `id`, `investigation_id`, `statement`, `rationale`, `testability_score`, `plausibility_score`, `experimental_design`, `status`.
- `hypothesis_evaluations`: Stores `id`, `hypothesis_id`, `evaluator_agent`, `score_breakdown_json`, `evaluation_notes`.
- `investigations`: Parent inquiry entity.

## 10. Inputs and Outputs
- **Generation Request (`HypothesisGenerateRequest`)**:
  ```json
  {
    "provider_kind": "optional model override",
    "model": "optional model name"
  }
  ```
  *(Endpoint supports empty body via `Body(default=None)`)*.
- **Generation Response (`HypothesisGenerationResponse`)**:
  JSON object containing generated hypothesis items, scores, and experimental protocol proposals.

## 11. AI Provider Dependencies
Requires an AI model (local or cloud) capable of abductive reasoning. Falls back to deterministic heuristic hypothesis formulation based on evidence gap templates when AI providers are offline.

## 12. External API Dependencies
None.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Trivial Hypotheses**: The scoring engine detects tautological or trivial statements (e.g. *"More research is needed"*) and filters them out before presentation.
- **Resilient Request Parsing**: The `/generate` POST route accepts empty body payloads cleanly.

## 15. Security and Permission Considerations
- Generating hypotheses requires workspace write permissions.
- Hypotheses remain private to the active workspace.

## 16. Related Features and Dependencies
- **Gap Discovery** (`docs/features/research-gaps.md`): Gaps serve as primary inputs for hypothesis generation.
- **Reports and Exports** (`docs/features/reports-and-exports.md`): Top-ranking hypotheses are included in exported research dossiers.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_hypothesis_generation.py -q`
