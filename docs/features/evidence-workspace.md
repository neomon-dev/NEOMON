# Feature Specification: Evidence Workspace & Fact Explorer

## 1. Feature Overview
The **Evidence Workspace** (`/evidence`) provides an interactive library for exploring, filtering, verifying, and auditing all factual evidence passages extracted across NEOMON investigations. Every evidence entry preserves the verbatim quote, surrounding contextual sentences, confidence score, evidence polarity (`supporting`, `refuting`, or `contextual`), and a direct link to the underlying document source.

## 2. Purpose and Problem Solved
Traditional AI chat summaries synthesize claims without showing where in the source text the fact originated, making fact-checking tedious and error-prone. The Evidence Workspace provides transparent traceability:
- Every extracted claim is anchored to verbatim text.
- Researchers can view surrounding sentences to check for quote-mining or missing context.
- Evidence polarity reveals both confirmation and counter-evidence at a glance.
- Human researchers can challenge and correct evidence annotations.

## 3. Where Users Access It
- **Dedicated Route**: `/evidence` (Evidence Explorer).
- **In-Investigation**: Claims & Evidence tab on `/investigations/[id]`.
- **Knowledge Graph**: Evidence nodes and inspector panel on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/evidence`.
2. Inspect the **Evidence Metrics Cards**:
   - Total matching evidence items.
   - Traceable on page (percentage with verified full-text provenance).
   - Supporting vs. Refuting distribution.
   - Total distinct investigations represented.
3. Filter evidence:
   - **Investigation Dropdown**: Filter to a specific research investigation or view all workspace evidence.
   - **Type Filter**: Toggle `All Types`, `Supporting`, `Refuting`, or `Contextual`.
   - **Search Input**: Enter keywords (e.g., *"blood glucose"*, *"critical temperature"*, *"adverse events"*).
4. Review evidence cards:
   - Read the exact highlighted quote.
   - Inspect the **Surrounding Context** drawer to verify nuance and methodology notes.
   - Check the **Confidence Meter** (e.g. `0.92 High Confidence`).
   - Click the source badge to inspect author credentials, publication venue, and DOI.
5. Click **"Reset Filters"** to restore default full workspace view.

## 5. How the Feature Works Internally
1. Evidence extraction executes during the research pipeline:
   - Extractor identifies sentences containing empirical results, quantitative data, or causal assertions.
   - Extracted passage is matched against the raw document to verify exact string alignment (`traceable = True`).
   - An entailment classifier assigns polarity (`supporting`, `refuting`, `contextual`) relative to the investigation's primary claim.
2. The `/api/v1/research/evidence` endpoint queries the database with dynamic filtering on `investigation_id`, `evidence_type`, and search text `q`.
3. Results are returned with joined `Claim` and `Source` relationships.
4. The client component (`components/evidence-explorer.tsx`) renders responsive card grids with highlight formatting and copy-citation actions.

## 6. Relevant Frontend Pages and Components
- `app/evidence/page.tsx`: Full-page Evidence Explorer route.
- `components/evidence-explorer.tsx`: Core evidence card list, search filters, and detail modals.
- `components/graph-detail-panel.tsx`: Evidence inspector panel for Knowledge Graph nodes.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/evidence`: Paginated, searchable evidence query endpoint.
- `GET /api/v1/research/evidence/{id}`: Single evidence record detail.
- `GET /api/v1/research/investigations/{id}/evidence`: All evidence items tied to a specific investigation.
- `POST /api/v1/research/evidence/{id}/challenge`: Allows researchers to submit accuracy challenges against an evidence passage.

## 8. Relevant Services and Agents
- `app.research.service`: Evidence retrieval and filtering queries.
- `app.analysis.evidence_verification`: Deterministic entailment verification and sentence alignment.
- `app.research.normalization`: Snippet boundary detector preserving surrounding sentences.

## 9. Database Tables and Relationships
- `evidence`: Primary table storing `id`, `source_id`, `claim_id`, `exact_text`, `surrounding_context`, `evidence_type`, `confidence_score`, `relevance_reason`, `traceable`.
- `claims`: Parent assertion entity linked via `claim_id`.
- `sources`: Source document entity linked via `source_id`.
- `evidence_annotations`: Human or agent annotations attached to evidence items.
- `human_evidence_corrections`: Correction audit trail for challenged evidence.

## 10. Inputs and Outputs
- **Query Parameters**:
  `GET /api/v1/research/evidence?limit=20&offset=0&evidence_type=supporting&q=metformin`
- **Response**: Array of `EvidenceResponse` items containing `id`, `claim_id`, `source_id`, `exact_text`, `surrounding_context`, `evidence_type`, `confidence_score`, `traceable`, and populated `source` summary.

## 11. AI Provider Dependencies
Optional. Extraction and alignment can be performed via deterministic regex and sentence tokenization or enhanced via LLM entailment scoring.

## 12. External API Dependencies
None. Operates entirely over local relational database storage.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Connection string to PostgreSQL or SQLite.

## 14. Error Handling and Limitations
- **Untraceable Passages**: If an LLM synthesizes an evidence passage that cannot be matched to the underlying source document, the system flags `traceable=False` with a warning badge.
- **Empty States**: If a search filter yields 0 matches, renders a helpful suggestion to adjust the search query or reset type filters.

## 15. Security and Permission Considerations
- Multi-tenant isolation: Users only see evidence linked to investigations in workspaces where they hold active membership.
- Evidence challenge actions require authenticated researcher credentials.

## 16. Related Features and Dependencies
- **Evidence Quality Calibration** (`docs/features/evidence-quality.md`): Calibrates quality scores for evidence items.
- **Knowledge Graph** (`docs/features/knowledge-graph.md`): Renders evidence as green (supporting) or red (refuting) nodes.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_evidence_verification.py -q`
  - `python -m pytest backend/tests/test_human_review_and_corrections.py -q`
- **Frontend Tests**:
  - `node --test tests/workspace-ui.test.mjs`
