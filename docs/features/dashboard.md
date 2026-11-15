# Feature Specification: Core Dashboard & Research Observatory

## 1. Feature Overview
The **Core Dashboard** serves as the central command cockpit for the NEOMON research intelligence platform. It provides high-level visibility across all research operations, displaying key performance indicators (total investigations, verified sources, extracted evidence items, and peer-review quality distributions), active workspace telemetry, recent investigation feeds, and an immediate launcher for new research inquiries.

## 2. Purpose and Problem Solved
Traditional scientific workflows suffer from fragmented information retrieval, where researchers switch between literature search engines, citation managers, and note-taking applications. The Core Dashboard solves this by unifying:
- Live aggregate research telemetry across the investigator's active workspace.
- Real-time backend connectivity and AI provider status.
- Instant access to historical and ongoing investigations.
- Visual breakdown of scientific evidence strength, flagging investigations that require methodology audits.

## 3. Where Users Access It
- **Route**: `/` (Root route)
- **Navigation**: "Dashboard" item in the primary sidebar navigation (`components/app-shell.tsx`).
- **Deep Links**: Breadcrumb roots and platform logo clicks.

## 4. Step-by-Step User Workflow
1. Navigate to `https://<domain>/` or `http://localhost:3000/`.
2. Inspect the top KPI summary cards:
   - **Investigations**: Total research investigations conducted within the active workspace.
   - **Sources Acquired**: Total distinct academic and web sources indexed.
   - **Extracted Evidence**: Total verified factual claims and evidence passages extracted.
   - **Full-Text Accessible**: Number of primary documents retrieved and parsed into full text.
3. Review the **Quality Status Banner**: Identifies investigations with pending or moderate evidence ratings requiring expert review.
4. Launch an investigation directly via the primary input form or click **"Start new investigation"** to configure advanced search parameters.
5. Review the **Recent Investigations Grid**: Click any card to drill down into the Investigation Detail Workspace (`/investigations/[id]`).

## 5. How the Feature Works Internally
1. On initial mount, the dashboard triggers concurrent API fetches to `/api/v1/research/investigations` and `/api/v1/agents`.
2. The client auth context (`lib/auth-context.tsx`) supplies the JWT session token via the `Authorization: Bearer <token>` header and filters data by the active `neomon_active_workspace_id`.
3. If unauthenticated, the dashboard renders a guest preview indicating authentication is required to persist investigations and run multi-agent debates.
4. Telemetry cards aggregate `source_count`, `evidence_count`, and `full_text_count` from the returned list of investigations.
5. The `BackendStatus` component (`components/backend-status.tsx`) polls `/api/v1/health` every 30 seconds to render operational health, latency, and active provider status (e.g., "Backend online · 17 agents ready").

## 6. Relevant Frontend Pages and Components
- `app/page.tsx`: Root dashboard page layout and data fetching logic.
- `components/backend-status.tsx`: Live backend connectivity badge and latency probe.
- `components/app-shell.tsx`: Primary navigation shell, user profile button, and workspace dropdown.
- `lib/api.ts`: API client with session token injection and error handling.
- `lib/auth-context.tsx`: Active workspace state and authentication lifecycle.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/investigations`: Lists investigations accessible to the requesting user within the workspace.
- `GET /api/v1/agents`: Returns registered agent definitions and operational statuses.
- `GET /api/v1/health`: Returns API operational status, version, database configuration, and demo mode flags.

## 8. Relevant Services and Agents
- `app.research.service`: Queries database sessions for investigation metadata and aggregates source/evidence counts.
- `app.ops.health`: Health check service measuring database latency and connection pool states.

## 9. Database Tables and Relationships
- `investigations`: Primary investigation entity storing question, status, mode, timeframe, workspace_id, owner_id.
- `sources`: Linked to `investigations` via `investigation_id` (one-to-many).
- `evidence`: Linked to `sources` via `source_id` (one-to-many).
- `workspaces`: Encapsulates multi-tenant boundaries via `workspace_id`.

## 10. Inputs and Outputs
- **Inputs**: Optional query parameters: `workspace_id` (UUID), `limit` (integer).
- **Outputs**: Array of `InvestigationResponse` objects containing UUID, question, mode, timeframe, status, created_at, updated_at, source_count, evidence_count, and quality_status.

## 11. AI Provider Dependencies
None for basic dashboard rendering. If local/remote AI providers are offline, the dashboard continues to display persisted investigations and evidence metrics.

## 12. External API Dependencies
None. Dashboard rendering relies exclusively on internal database queries and local health probes.

## 13. Configuration Requirements
- `NEXT_PUBLIC_API_URL`: Directs frontend requests to the FastAPI backend (defaults to `http://127.0.0.1:8000/api/v1`).
- `NEOMON_DATABASE_URL`: Backend database connection string.

## 14. Error Handling and Limitations
- **Backend Offline**: If the backend is unreachable, the dashboard displays a clear alert toast: `"Cannot reach the NEOMON backend... Start the FastAPI server and try again."`
- **Zero Investigations**: Renders an accessible empty state with a call-to-action button to initiate the first research question.
- **Unauthorized (401)**: Gracefully switches to a guest banner encouraging registration or login.

## 15. Security and Permission Considerations
- Multi-tenant workspace isolation: Non-admin users only see investigations belonging to workspaces where they hold active membership (`admin`, `researcher`, `reviewer`, `viewer`).
- Database queries enforce workspace filtering via SQLAlchemy Core expressions.

## 16. Related Features and Dependencies
- **Investigation Detail** (`/investigations/[id]`): Target destination when clicking any recent investigation.
- **New Investigation** (`/investigations/new`): Advanced creation view linked from the dashboard header.
- **Authentication** (`/login`): Required to manage investigations and switch workspaces.

## 17. Relevant Tests and How to Run Them
- **Frontend Test**: `node --test tests/workspace-ui.test.mjs` (Verifies workspace metrics and loading states).
- **Backend Test**: `python -m pytest backend/tests/test_research_engine.py -q` (Verifies investigation querying and counting).
