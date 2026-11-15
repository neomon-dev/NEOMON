# Feature Specification: Contradiction Intelligence & Resolution Engine

## 1. Feature Overview
The **Contradiction Intelligence Engine** detects, visualizes, and helps resolve scientific contradictions across empirical literature. It operates at two levels: **intra-investigation** (opposing claims within a single inquiry) and **cross-investigation** (conflicting conclusions discovered across different studies within a workspace). The dedicated **Contradiction Workspace** (`/contradictions`) provides contradiction severity metrics, tension maps, and formal human resolution workflows.

## 2. Purpose and Problem Solved
Conflicting results are common in cutting-edge science (e.g. varying efficacy rates in clinical trials, or non-reproducible superconductor claims). Most AI systems either ignore contradictions or average them into misleading compromises. NEOMON's Contradiction Intelligence engine:
- Surfaces tensions explicitly rather than concealing them.
- Classifies contradictions by severity (`Critical`, `Moderate`, `Minor`).
- Categorizes the underlying cause (e.g. differing dosages, discordant patient cohorts, distinct measurement techniques, or temporal shifts).
- Provides formal resolution logs where researchers can document reasons for favoring one finding or concluding ongoing controversy.

## 3. Where Users Access It
- **Dedicated Route**: `/contradictions` (Contradiction Intelligence Dashboard).
- **In-Investigation**: Contradictions badge and summary on `/investigations/[id]`.
- **Knowledge Graph**: Red-colored adversarial edges and contradiction nodes on `/graph`.

## 4. Step-by-Step User Workflow
1. Navigate to `/contradictions`.
2. Inspect the **Contradiction Summary Banner**:
   - Total detected scientific contradictions.
   - Severity breakdown: Critical (mutually exclusive conclusions), Moderate (discordant effect sizes), Minor (nuanced qualifiers).
   - Resolution rate: Percentage of contradictions formally resolved by investigators.
3. Filter contradictions:
   - Select a specific investigation or toggle **All Investigations**.
   - Filter by status: `unresolved`, `resolved`, `investigating`.
   - Filter by category: `dosage_discrepancy`, `cohort_difference`, `methodology_divergence`, `temporal_update`.
4. Click **"Detect Scientific Contradictions"** to trigger a real-time scan across workspace claims.
5. Inspect a Contradiction Card:
   - **Primary Claim**: The initial assertion with supporting evidence quote.
   - **Contradictory Claim**: The opposing assertion with counter-evidence quote.
   - **Tension Explanation**: Plain-language description of why the two findings conflict.
6. Click **"Resolve Contradiction"**:
   - Choose resolution type: `reconciled_by_methodology`, `superseded_by_newer_trial`, `unresolved_controversy`, `false_positive_flag`.
   - Input rationales and references.
   - Submit resolution: Updates contradiction status and persists an audit log entry.

## 5. How the Feature Works Internally
1. **Detection Heuristics & Model Scoring**:
   - The `app.analysis.contradiction_service` extracts all claim-evidence pairs within the target scope.
   - Computes semantic similarity between claims. Pairs with high topical similarity but opposite sentiment/polarity are flagged.
   - An entailment model or heuristic rule evaluates mutual exclusivity. If Claim A asserts efficacy while Claim B asserts no significant effect or adverse harm, a contradiction is instantiated.
2. **Database Persistence**:
   - Persists a `research_contradictions` record linking `primary_investigation_id`, `primary_claim_id`, `secondary_investigation_id`, and `secondary_claim_id`.
3. **Resolution Logging**:
   - When resolved, the engine records the action in `contradiction_resolution_logs` with `resolved_by_id`, `resolution_type`, and `notes`.
   - Updates `status` from `unresolved` to `resolved`.

## 6. Relevant Frontend Pages and Components
- `app/contradictions/page.tsx`: Full Contradiction Intelligence dashboard.
- `components/contradiction-workspace.tsx`: Core contradiction cards, filters, and resolution modal.
- `components/knowledge-graph-workspace.tsx`: Renders red dashed tension edges between contradicting claims.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/contradictions`: Lists contradictions with optional severity/status filters.
- `POST /api/v1/research/contradictions/detect`: Triggers autonomous contradiction detection.
- `POST /api/v1/research/contradictions/{id}/resolve`: Submits a formal resolution decision.
- `GET /api/v1/research/contradictions/{id}/logs`: Fetches resolution history and investigator notes.

## 8. Relevant Services and Agents
- `app.analysis.contradiction_service`: Detection engine, semantic comparison, and resolution tracker.
- `app.agents.skeptic`: Identifies contradictory evidence during debate loops.

## 9. Database Tables and Relationships
- `research_contradictions`: Primary table storing `id`, `primary_investigation_id`, `secondary_investigation_id`, `primary_claim_id`, `secondary_claim_id`, `severity`, `category`, `explanation`, `status`.
- `contradiction_resolution_logs`: Audit trail storing `id`, `contradiction_id`, `resolved_by_id`, `resolution_type`, `explanation`, `created_at`.
- `claims`: The contradicting claim entities.

## 10. Inputs and Outputs
- **Detection Request (`ContradictionDetectRequest`)**:
  ```json
  {
    "investigation_id": "UUID (optional)",
    "cross_investigation": true,
    "provider_kind": "optional model override"
  }
  ```
- **Detection Response**: Array of `ResearchContradictionView` objects.
- **Resolution Request (`ContradictionResolveRequest`)**:
  ```json
  {
    "resolution_type": "reconciled_by_methodology",
    "explanation": "Trial B used an insufficient 5mg dose; Trial A confirmed efficacy at 15mg."
  }
  ```

## 11. AI Provider Dependencies
Optional. Contradiction detection supports deterministic rule-based sentence alignment and keyword polarity matching, enhanced by LLM semantic reasoning when an AI provider is configured.

## 12. External API Dependencies
None. Operates over indexed database claims.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Empty Payloads**: The POST `/detect` endpoint supports empty bodies via `Body(default=None)`, defaulting cleanly to full-scope workspace scanning.
- **False Tensions**: Nuanced qualifications (e.g. differing patient age cohorts) are classified as `Moderate` or `Minor` rather than false alarms.

## 15. Security and Permission Considerations
- Viewing contradictions is available to all workspace members.
- Resolving contradictions requires `researcher` or `admin` permissions; resolution decisions record the acting user's ID for accountability.

## 16. Related Features and Dependencies
- **Knowledge Graph** (`docs/features/knowledge-graph.md`): Visualizes contradiction links as red relational arcs.
- **Synthesis Engine** (`docs/features/research-synthesis.md`): Surfaces unresolved contradictions in executive synthesis summaries.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_contradiction_intelligence.py -q`
