# NEOMON REST API Reference Specification

## 1. Overview
The NEOMON backend exposes a versioned, asynchronous REST API under the `/api/v1` prefix, supplemented by Server-Sent Events (SSE) for real-time telemetry streaming. All endpoints adhere to standard HTTP status codes, JSON request and response serialization, and stateless token-based authentication.

---

## 2. Authentication & Headers

Protected endpoints require the standard `Authorization` header:

```http
Authorization: Bearer <session_token>
```

When session tokens are issued via `/api/v1/auth/login` or `/api/v1/auth/register`, they are passed in client requests and verified against SHA-256 session token hashes in the database.

---

## 3. Complete Endpoint Directory

### Authentication & Account (`/api/v1/auth`)
- `POST /api/v1/auth/register`: Register a new user account and provision default personal workspace.
- `POST /api/v1/auth/login`: Authenticate email/password credentials and receive bearer session token.
- `POST /api/v1/auth/logout`: Revoke active session token.
- `GET /api/v1/auth/me`: Retrieve current authenticated user profile.
- `POST /api/v1/auth/change-password`: Update password and revoke existing sessions.
- `POST /api/v1/auth/password-reset/request`: Generate password reset token.
- `POST /api/v1/auth/password-reset/confirm`: Apply new password using reset token.
- `POST /api/v1/auth/stream-ticket`: Issue single-use, 60-second token for authenticated SSE connections.

### Health & Diagnostics (`/api/v1/health`)
- `GET /api/v1/health`: Returns service name, version, operational status, database dialect, and latency.
- `GET /health`: Unversioned health probe for container orchestrators and Render load balancers.

### Research & Investigations (`/api/v1/research`)
- `POST /api/v1/research/investigations`: Initiate a new research investigation (triggers query decomposition, literature retrieval, and claim extraction).
- `GET /api/v1/research/investigations`: List paginated investigations accessible to the user.
- `GET /api/v1/research/investigations/{id}`: Retrieve detailed investigation record, metrics, and linked counts.
- `GET /api/v1/research/investigations/{id}/sources`: List sources retrieved for a specific investigation.
- `GET /api/v1/research/investigations/{id}/evidence`: List factual evidence extracted for a specific investigation.
- `GET /api/v1/research/investigations/{id}/claims`: List scientific claims formulated for an investigation.
- `GET /api/v1/research/sources`: Search and filter literature sources across the active workspace.
- `GET /api/v1/research/evidence`: Search and filter factual evidence passages across the active workspace.

### Real-Time Event Streaming (`/api/v1/events`)
- `GET /api/v1/events/investigations/{id}`: SSE stream broadcasting live research events (`query_generated`, `source_discovered`, `evidence_extracted`, `agent_thought`, `investigation_completed`).
  - Authenticated via `?ticket=<stream_ticket>` or `?token=<session_token>`.

### Multi-Agent Analysis & Debate (`/api/v1/analysis` and `/api/v1/agents`)
- `GET /api/v1/agents`: List all registered autonomous agents, identifiers, and operational statuses.
- `GET /api/v1/agents/{id}`: Retrieve single agent definition.
- `POST /api/v1/analysis/jobs`: Dispatch a multi-agent analysis or adversarial debate job.
- `GET /api/v1/analysis/jobs`: List analysis jobs for the workspace.
- `GET /api/v1/analysis/jobs/{id}`: Retrieve status, debate rounds, and arbitrator adjudication rulings.

### Knowledge Graph (`/api/v1/research/graph`)
- `GET /api/v1/research/graph`: Retrieve nodes and edges for the interactive knowledge graph (scoped to investigation or entire workspace).
- `GET /api/v1/research/graph/node/{type}/{id}`: Retrieve deep provenance and traceability metadata for a specific graph node.

### Quality Audit & Calibration (`/api/v1/research/quality-audit`)
- `GET /api/v1/research/quality-audit/{investigation_id}`: Retrieve multi-dimensional quality calibration breakdown.
- `POST /api/v1/research/quality-audit/{investigation_id}/recalibrate`: Recompute quality scores and calibrated tiers.

### Contradiction Intelligence (`/api/v1/research/contradictions`)
- `GET /api/v1/research/contradictions`: List detected contradictions with optional severity and status filters.
- `POST /api/v1/research/contradictions/detect`: Trigger autonomous contradiction detection across claims.
- `POST /api/v1/research/contradictions/{id}/resolve`: Submit formal human resolution decision with explanation.
- `GET /api/v1/research/contradictions/{id}/logs`: Retrieve resolution audit history.

### Citation Lineage & Study Independence (`/api/v1/research/study-independence`)
- `GET /api/v1/research/study-independence/{investigation_id}`: Retrieve study independence score and primary dataset clusters.
- `GET /api/v1/research/study-independence/lineage/{source_id}`: Fetch direct citation lineage links for a source.

### Cross-Study Synthesis (`/api/v1/research/synthesis`)
- `POST /api/v1/research/synthesis`: Execute multi-study consensus synthesis across selected investigations.
- `GET /api/v1/research/synthesis/reports`: List cross-investigation synthesis reports.
- `GET /api/v1/research/synthesis/claims/search`: Global claim search across all workspace investigations.

### Research Trend Intelligence (`/api/v1/research/trends`)
- `GET /api/v1/research/trends/latest`: Retrieve latest longitudinal research trend intelligence report.
- `POST /api/v1/research/trends/analyze`: Execute longitudinal trend velocity and momentum analysis.
- `GET /api/v1/research/trends`: List historical trend analyses.

### Research Gap Discovery (`/api/v1/research/investigations/{id}/gaps`)
- `GET /api/v1/research/investigations/{id}/gaps`: Retrieve latest gap analysis and evidence coverage score.
- `POST /api/v1/research/investigations/{id}/gaps/analyze`: Run a new versioned research gap analysis.
- `GET /api/v1/research/investigations/{id}/gaps/versions`: List historical gap analysis versions.

### Hypothesis Generation (`/api/v1/research/investigations/{id}/hypotheses`)
- `GET /api/v1/research/investigations/{id}/hypotheses`: Retrieve generated hypotheses for an investigation.
- `POST /api/v1/research/investigations/{id}/hypotheses/generate`: Formulate novel, testable scientific hypotheses.
- `POST /api/v1/research/hypotheses/{id}/evaluate`: Evaluate experimental protocol feasibility.

### Autonomous Workflows (`/api/v1/autonomous`)
- `GET /api/v1/autonomous/workflows`: List autonomous workflows in active workspace.
- `POST /api/v1/autonomous/workflows`: Create and initialize an autonomous multi-cycle workflow.
- `POST /api/v1/autonomous/workflows/{id}/start`: Start or resume cycle execution.
- `POST /api/v1/autonomous/workflows/{id}/pause`: Pause workflow execution.
- `POST /api/v1/autonomous/workflows/{id}/actions/{action_id}/approve`: Operator approval for pending research actions.
- `POST /api/v1/autonomous/workflows/{id}/actions/{action_id}/reject`: Operator rejection for pending research actions.
- `GET /api/v1/autonomous/workflows/{id}/report`: Fetch final synthesized workflow report.

### Workspaces & Collaboration (`/api/v1/workspaces` and `/api/v1/collaboration`)
- `GET /api/v1/workspaces`: List accessible workspaces for the user.
- `POST /api/v1/workspaces`: Create a new collaborative workspace.
- `GET /api/v1/workspaces/{id}/members`: List workspace members and roles.
- `POST /api/v1/workspaces/{id}/invitations`: Invite a new colleague by email.
- `GET /api/v1/workspaces/{id}/activities`: Paginated chronological scientific audit stream.
- `POST /api/v1/collaboration/reviews`: Request a formal peer review on an investigation.
- `POST /api/v1/collaboration/reviews/{id}/decisions`: Submit peer review ruling (`approved`, `rejected`).
- `GET /api/v1/collaboration/notifications`: List user notifications.
- `POST /api/v1/collaboration/notifications/read-all`: Mark all notifications as read.

### Scientific Benchmarks (`/api/v1/benchmarks`)
- `GET /api/v1/benchmarks/datasets`: List available gold-standard benchmark datasets.
- `POST /api/v1/benchmarks/run`: Execute an empirical benchmark evaluation run.
- `GET /api/v1/benchmarks/runs`: List historical benchmark evaluation runs and metrics.
- `POST /api/v1/benchmarks/corrections`: Submit a human evidence correction record.

### Knowledge Export (`/api/v1/research/export`)
- `GET /api/v1/research/export/investigations/{id}/markdown`: Download formatted Markdown research dossier.
- `GET /api/v1/research/export/investigations/{id}/json`: Download full structured JSON research dataset.

### AI Model Providers (`/api/v1/providers`)
- `GET /api/v1/providers`: List configured model provider endpoints.
- `POST /api/v1/providers`: Create or update a model provider configuration.
- `POST /api/v1/providers/{id}/test`: Execute active latency and connectivity probe.
- `POST /api/v1/providers/test-search`: Test Tavily web search provider connectivity.
