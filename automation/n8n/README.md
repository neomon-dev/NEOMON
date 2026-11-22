# NEOMON — n8n Automation Workflows

This directory contains production-ready n8n workflow definitions for automated research intelligence, asynchronous event notifications, and human-in-the-loop report approval.

## Included Workflows

1. **`research_monitoring.json`** (Automated Research Monitoring)
   - Interval-based trigger (e.g. hourly or daily).
   - Retrieves active monitoring queries from NEOMON API (`GET /api/v1/monitoring`).
   - Dispatches incremental research search requests (`POST /api/v1/integrations/n8n/events` with `monitoring.trigger`).
   - Deduplicates sources and captures newly detected contradictions and evidence passages.
   - Idempotency-guarded to prevent duplicate executions.

2. **`investigation_completion.json`** (Investigation Completion Notification)
   - Listens on webhook `neomon-investigation-completed`.
   - Fetches scientific telemetry, source counts, and quality status from NEOMON.
   - Evaluates completion integrity and dispatches dispatch records.

3. **`report_approval_delivery.json`** (Human Approval & Report Delivery)
   - Triggered when research reports require formal peer or board sign-off.
   - Queries review request status from `GET /api/v1/collaboration/reviews/{id}`.
   - Enforces NEOMON's independent permission checks and self-approval guards.
   - Delivers report only upon verified reviewer authorization.

## Import Instructions

1. Open your running n8n instance (e.g., `http://localhost:5678` or hosted cloud instance).
2. Go to **Workflows** → Click **Add Workflow** → **Import from File**.
3. Select any of the JSON files in this directory.
4. Configure the following Environment Variables or Credentials in n8n:
   - `NEOMON_BACKEND_URL`: URL of the NEOMON FastAPI backend (e.g., `http://127.0.0.1:8001` or Render URL).
   - `NEOMON_SERVICE_TOKEN`: Shared service-to-service Bearer token matching `NEOMON_N8N_SERVICE_TOKEN`.
   - `NEOMON_WORKSPACE_ID`: UUID of the active research workspace.
5. Click **Activate** to turn on scheduling and webhook listeners.
