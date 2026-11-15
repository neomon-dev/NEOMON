# Feature Specification: Cross-Investigation Research Synthesis Hub

## 1. Feature Overview
The **Research Synthesis Hub** (`/synthesis`) enables researchers to aggregate, compare, and synthesize findings across multiple disparate investigations within their workspace. It provides multi-study selection checklists, synthesis perspective filters, a **Global Claim Search** querying claims across all historical inquiries, and automated executive consensus reporting.

## 2. Purpose and Problem Solved
Individual investigations answer focused questions, but comprehensive literature reviews require cross-study meta-synthesis: comparing clinical trial findings across different drug molecules, or synthesizing materials science experiments from multiple labs. The Synthesis Hub solves this by:
- Allowing researchers to select arbitrary combinations of investigations for joint analysis.
- Resolving agreement, dissent, and evidentiary overlap across studies.
- Exposing a unified Global Claim Search across workspace knowledge.
- Producing structured synthesis dossiers with comparative consensus ratings.

## 3. Where Users Access It
- **Dedicated Route**: `/synthesis` (Cross-Investigation Synthesis Hub).
- **Navigation**: "Cross-study synthesis" link in the primary sidebar navigation.

## 4. Step-by-Step User Workflow
1. Navigate to `/synthesis`.
2. Inspect the **Investigation Selection Checklist**:
   - Select two or more investigations to include in the synthesis pool.
   - View investigation summary, date conducted, and source counts.
3. Configure **Synthesis Perspectives**:
   - **Focus Area**: Overall Consensus, Methodological Variance, or Adverse Signals.
   - **Resolution Mode**: Conservative (demands high evidence strength) vs. Comprehensive.
4. Click **"Run Multi-Study Synthesis"**:
   - The engine aggregates claims, clusters related findings, and identifies shared versus divergent conclusions.
   - Generates an executive consensus summary and comparative findings table.
5. Switch to the **Global Claim Search** tab:
   - Enter a query (e.g., *"weight loss"*, *"cardiovascular risk"*).
   - Instant search across all claims in the workspace, displaying confidence tiers and source investigations.

## 5. How the Feature Works Internally
1. The user submits a synthesis request with a list of `investigation_ids`.
2. The `app.analysis.synthesis_service`:
   - Validates user read access to all requested investigations.
   - Ingests all claims and evidence associated with the selected investigations.
   - Executes semantic clustering over claims to group topical findings.
   - Compares polarity and confidence across studies to determine consensus level (`unanimous_consensus`, `moderate_agreement`, `active_controversy`, `insufficient_evidence`).
3. Persists results into `investigation_synthesis_reports` and `claim_synthesis_results`.
4. Returns the synthesized dossier to the frontend.

## 6. Relevant Frontend Pages and Components
- `app/synthesis/page.tsx`: Synthesis Hub page container.
- `components/cross-investigation-workspace.tsx`: Multi-study selector, Global Claim Search, and synthesis cards.

## 7. Relevant Backend Routes and Endpoints
- `POST /api/v1/research/synthesis`: Runs cross-investigation synthesis over selected investigations.
- `GET /api/v1/research/synthesis/reports`: Lists historical cross-study synthesis reports.
- `GET /api/v1/research/synthesis/claims/search`: Global claim search endpoint querying across all investigations in the active workspace.

## 8. Relevant Services and Agents
- `app.analysis.synthesis_service`: Multi-study clustering and consensus aggregator.
- `app.agents.synthesizer`: AI agent providing narrative consensus summaries.

## 9. Database Tables and Relationships
- `investigation_synthesis_reports`: Stores `id`, `workspace_id`, `title`, `executive_summary`, `investigation_ids_json`, `consensus_level`, `created_at`.
- `claim_synthesis_results`: Individual synthesized claim clusters linked to the synthesis report.
- `cross_investigation_relationships`: Tracks inter-investigation dependencies.

## 10. Inputs and Outputs
- **Synthesis Request**:
  ```json
  {
    "investigation_ids": ["UUID-1", "UUID-2"],
    "focus_area": "overall_consensus",
    "provider_kind": "optional model override"
  }
  ```
- **Synthesis Response**:
  Executive summary, consensus score (0.0 to 1.0), consensus classification, list of synthesized claim themes, and unresolved tensions list.

## 11. AI Provider Dependencies
Optional. Consensus categorization and claim clustering support rule-based deterministic matching, enhanced by LLM narrative summarization when available.

## 12. External API Dependencies
None. Operates over indexed workspace investigations.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Single Investigation Selected**: If fewer than 2 investigations are chosen, the UI prompts the user to select at least two studies for cross-analysis.
- **Disjoint Investigations**: If selected investigations share zero topical overlap, the synthesis report explicitly notes the lack of shared concepts without failing.

## 15. Security and Permission Considerations
- The backend verifies that the user holds read access to *every* investigation in the requested list before running the synthesis.
- Synthesis reports are scoped to the active workspace.

## 16. Related Features and Dependencies
- **Investigations** (`docs/features/investigations.md`): Individual investigations provide the source data.
- **Reports and Exports** (`docs/features/reports-and-exports.md`): Synthesis reports can be exported to Markdown and PDF.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_claim_synthesis.py -q`
  - `python -m pytest backend/tests/test_cross_investigation.py -q`
