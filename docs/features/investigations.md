# Feature Specification: Investigation Lifecycle & Real-Time Telemetry

## 1. Feature Overview
The **Investigation Lifecycle** is the core operational unit in NEOMON. It encompasses the initiation, query decomposition, literature retrieval, factual claim extraction, multi-agent dialectical analysis, and persistent storage of research inquiries. A dedicated **Investigation Detail Workspace** (`/investigations/[id]`) provides real-time event streaming via Server-Sent Events (SSE), telemetry metrics, evidence citation grids, and multi-agent debate controls.

## 2. Purpose and Problem Solved
Standard LLM chat systems answer complex research queries in a single opaque step, frequently hallucinating citations and omitting counter-arguments. NEOMON's Investigation Lifecycle replaces opaque generation with a transparent, observable scientific discovery loop:
- Breaks complex scientific questions into sub-queries.
- Retrieves primary academic and web literature with persistent DOIs and canonical URLs.
- Extracts verbatim factual evidence passages with surrounding context.
- Exposes real-time event telemetry to researchers as agents execute.

## 3. Where Users Access It
- **Creation**: `/` (Quick launcher) and `/investigations/new` (Advanced configuration).
- **Execution & Detail**: `/investigations/[id]` (Permanent investigation workspace).
- **History**: Accessible via the dashboard recent investigations grid and sidebar.

## 4. Step-by-Step User Workflow
1. Navigate to `/investigations/new`.
2. Input a detailed research question (e.g. *"What are the clinical efficacy and safety outcomes of GLP-1 receptor agonists in non-diabetic obesity management?"*).
3. Configure parameters:
   - **Mode**: `Quick` (targeted synthesis, 1-3 sources) or `Deep` (exhaustive multi-provider search, 10+ sources).
   - **Timeframe**: Optional temporal filter (e.g. `2020-2026` or `Past 5 years`).
   - **Max Sources**: Upper bound on literature acquisition (default: 10).
   - **Max Search Depth**: Iterative query expansion limit (1 to 4).
4. Click **"Launch Investigation"**.
5. The interface immediately routes to `/investigations/[id]`.
6. Watch real-time execution telemetry:
   - Status badge transitions: `created` → `decomposing` → `retrieving` → `extracting` → `analyzing` → `completed`.
   - Event log streams agent thoughts, query executions, and citation links via SSE.
7. Review generated scientific outputs across tabs:
   - **Overview**: Core findings, confidence score, and verification progress.
   - **Claims & Evidence**: Extracted factual assertions linked to verbatim source quotes.
   - **Sources**: Indexed literature with credibility tiers.
   - **Multi-Agent Intelligence**: Advocate vs. Skeptic debate rounds and methodology audits.
   - **Knowledge Graph**: Local interactive entity-relationship sub-graph.

## 5. How the Feature Works Internally
1. **Creation**: `POST /api/v1/research/investigations` validates the user's workspace membership and persists an `Investigation` record in database state `created`.
2. **Decomposition**: The Research Orchestrator calls the Decomposer agent to parse the question into distinct search categories (background, mechanisms, clinical trials, counter-evidence).
3. **Retrieval**: Search queries are executed concurrently across configured providers (arXiv, Crossref, OpenAlex, PubMed, and optional Tavily).
4. **Extraction**: Documents are fetched, content hashes verified, and relevant text passages extracted using deterministic heuristic or LLM extraction.
5. **Real-time Event Streaming**: Every pipeline event is emitted to the in-memory `EventBroker` and broadcast over SSE (`/api/v1/events/investigations/{id}`).
6. **SSE Security**: Before opening the `EventSource`, the frontend requests a short-lived, single-use stream ticket (`POST /api/v1/auth/stream-ticket`), preventing bearer token leakage in URL query parameters.

## 6. Relevant Frontend Pages and Components
- `app/investigations/new/page.tsx`: Advanced investigation form with mode and depth selectors.
- `app/investigations/[id]/page.tsx`: Primary investigation workspace, telemetry banner, tabs, and SSE listener.
- `components/evidence-explorer.tsx`: Tabular and card view of linked evidence.
- `components/source-intelligence.tsx`: Source breakdown with credibility scores.
- `components/collaboration-panel.tsx`: In-context peer review triggers, annotations, and discussions.

## 7. Relevant Backend Routes and Endpoints
- `POST /api/v1/research/investigations`: Creates and triggers a new research investigation.
- `GET /api/v1/research/investigations/{id}`: Fetches complete investigation state, metrics, and linked counts.
- `GET /api/v1/events/investigations/{id}`: SSE endpoint streaming live research events.
- `POST /api/v1/auth/stream-ticket`: Issues a single-use ticket for authenticated SSE connection.

## 8. Relevant Services and Agents
- `app.research.service`: Coordinates investigation pipeline execution.
- `app.research.decomposition`: Decomposes questions into multi-angle queries.
- `app.research.retrieval`: Dispatches queries to academic and web sources.
- `app.analysis.event_broker`: Thread-safe broadcast channel for SSE events.

## 9. Database Tables and Relationships
- `investigations`: Primary entity with `id`, `question`, `status`, `mode`, `timeframe`, `workspace_id`, `owner_id`.
- `research_events`: Persisted event log entries linked to `investigation_id`.
- `research_queries`: Generated search queries linked to `investigation_id`.
- `sources`: Documents retrieved for the investigation.
- `claims`: Extracted scientific assertions linked to `investigation_id`.
- `evidence`: Verbatim passages linked to `claims` and `sources`.

## 10. Inputs and Outputs
- **Creation Request (`InvestigationCreate`)**:
  ```json
  {
    "question": "string (min 5 chars)",
    "mode": "quick | deep",
    "timeframe": "string (optional)",
    "workspace_id": "UUID (optional, defaults to user's active workspace)"
  }
  ```
- **Response (`ResearchStartResponse`)**:
  Returns the initialized `investigation`, list of dispatched `queries`, initial `source_count`, and `evidence_count`.

## 11. AI Provider Dependencies
- Optional for rule-based mode; required for neural decomposition and deep synthesis. Supports LM Studio, Ollama, OpenAI, and Anthropic.
- If AI providers are unavailable, the engine falls back to deterministic rule-based query expansion without halting.

## 12. External API Dependencies
- Public Academic APIs: arXiv API, Crossref REST API, OpenAlex API, Europe PMC / PubMed.
- Web Search: Tavily API (optional, utilized if `TAVILY_API_KEY` is configured).

## 13. Configuration Requirements
- `NEOMON_REQUEST_TIMEOUT_SECONDS`: Maximum HTTP request wait time (default: 15s).
- `NEOMON_ANALYSIS_OVERALL_TIMEOUT_SECONDS`: Total pipeline timeout (default: 1800s).

## 14. Error Handling and Limitations
- **Provider Timeouts**: Individual search provider failures are logged in `provider_failure_impacts` without aborting the investigation.
- **SSE Disconnection**: The client automatically reconnects with exponential backoff and refreshes data on reconnect.
- **Empty Results**: If no sources match, the investigation marks status `completed` with a clear advisory to broaden the question keywords.

## 15. Security and Permission Considerations
- Investigation creation checks workspace write permission (`admin` or `researcher`).
- Cross-workspace isolation: Users cannot view or query investigations from workspaces they do not belong to.
- SSE stream ticket expires after 60 seconds and is invalidated upon connection.

## 16. Related Features and Dependencies
- **Multi-Agent Analysis** (`/agents`): Can be launched directly from the investigation detail page.
- **Knowledge Graph** (`/graph`): Renders the investigation's relational network.
- **Export Engine**: Generates PDF/Markdown/JSON dossiers directly from the investigation.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_research_engine.py -q`
  - `python -m pytest backend/tests/test_events.py -q`
- **Frontend Tests**:
  - `node --test tests/workspace-ui.test.mjs`
