# Feature Specification: Settings, AI Configuration & Telemetry

## 1. Feature Overview
The **Settings & Configuration Workspace** (`/settings`) provides centralized control over local and cloud AI model providers, search engine credentials, inference parameters (temperature, max tokens, reasoning effort), notification delivery channels, and platform system diagnostics. It features live connectivity testing for all connected providers.

## 2. Purpose and Problem Solved
Managing disparate endpoints (LM Studio on port 1234, Ollama on port 11434, OpenAI cloud APIs, and Tavily search keys) in ad-hoc configuration files is error-prone and insecure. The Settings interface unifies system configuration:
- Allows switching between local private models and cloud APIs with a single click.
- Tests connectivity to model runtimes before initiating heavy research runs.
- Adjusts inference temperature and token ceilings to match specific scientific tasks.
- Verifies search provider operational status in real time.

## 3. Where Users Access It
- **Dedicated Route**: `/settings` (Settings Dashboard).
- **Navigation**: "Settings" link in the bottom section of the primary sidebar (`components/app-shell.tsx`).
- **Profile Menu**: Direct link from the user profile dropdown in the top header.

## 4. Step-by-Step User Workflow
1. Navigate to `/settings`.
2. Inspect the **System Health & Connectivity Status**:
   - Backend API status (`healthy`, `latency_ms`, `version`).
   - Active database dialect (`SQLite WAL` or `PostgreSQL`).
   - Connection pool statistics (pool size, checked-in, overflow).
3. Configure **AI Model Providers**:
   - Choose provider tab: `LM Studio (Local)`, `Ollama (Local)`, `OpenAI / Custom Cloud`, `Anthropic`.
   - Enter API base URL (e.g. `http://localhost:1234/v1`).
   - Specify loaded model identifier (e.g. `meta-llama-3-8b-instruct`, `mistral:7b`).
   - If using cloud models, enter the API key (persisted securely; masked in the UI).
   - Click **"Test Connection"**: Confirms model responsiveness and displays roundtrip latency.
4. Adjust **Inference Hyperparameters**:
   - **Temperature Slider**: Lower values (0.0 to 0.2) for strict factual verification; higher values (0.5 to 0.8) for open-ended hypothesis generation.
   - **Max Token Output**: Limit between 512 and 8192 tokens.
5. Configure **Search Providers**:
   - View Tavily API status; enter optional `TAVILY_API_KEY`.
   - Click **"Test Search Provider"**: Sends a lightweight search probe to verify quota and operational health.
6. Configure **Notification Preferences**:
   - Toggle In-App Alerts and Email Digests.
7. Click **"Save Preferences"** to apply changes across the platform.

## 5. How the Feature Works Internally
1. The settings page queries:
   - `GET /api/v1/providers`: Lists saved model configurations.
   - `GET /api/v1/health`: Fetches active backend diagnostic telemetry.
   - `GET /api/v1/collaboration/notification-preferences`: Loads user alert toggles.
2. When testing a provider (`POST /api/v1/providers/{id}/test`), the backend instantiates a temporary client, executes a minimal completion probe (e.g. `"ping"`), measures execution latency, and returns the active model identity.
3. Provider settings are saved in the `model_configurations` database table with foreign key linkage to the user's workspace.

## 6. Relevant Frontend Pages and Components
- `app/settings/page.tsx`: Complete settings page layout and tabbed panels.
- `components/provider-context.tsx`: React Context providing reactive provider state to components.
- `components/backend-status.tsx`: Navbar badge reflecting live health from `/api/v1/health`.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/health`: Live health and telemetry endpoint.
- `GET /api/v1/providers`: Returns registered provider configurations.
- `POST /api/v1/providers`: Creates or updates a provider configuration.
- `POST /api/v1/providers/{id}/test`: Tests connectivity to a specific model provider.
- `POST /api/v1/providers/test-search`: Tests search provider (Tavily) connectivity.
- `GET /api/v1/collaboration/notification-preferences`: Reads user alert delivery preferences.
- `PUT /api/v1/collaboration/notification-preferences`: Updates user alert delivery preferences.

## 8. Relevant Services and Agents
- `app.providers.factory.ProviderFactory`: Dynamic provider client instantiator.
- `app.ops.health`: Active database and pool health inspection service.

## 9. Database Tables and Relationships
- `model_configurations`: Stores provider configurations (`id`, `name`, `provider`, `endpoint`, `model`, `created_at`).
- `notification_preferences`: Stores user delivery preferences.

## 10. Inputs and Outputs
- **Provider Test Request**:
  `POST /api/v1/providers/{id}/test`
- **Provider Test Response**:
  ```json
  {
    "healthy": true,
    "latency_ms": 112.4,
    "model": "llama3:latest",
    "message": "Connection verified successfully."
  }
  ```

## 11. AI Provider Dependencies
Self-referential: Tests and manages all AI provider connections.

## 12. External API Dependencies
Optionally tests Tavily API (`https://api.tavily.com`) if configured.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.
- `NEOMON_ALLOWED_LOCAL_PROVIDER_HOSTS`: Whitelist of permitted local provider hostnames (`localhost`, `127.0.0.1`, `::1`).

## 14. Error Handling and Limitations
- **Local Server Closed**: If LM Studio or Ollama is not running, displays an actionable error message with port check instructions.
- **Invalid API Keys**: Returns clean HTTP 401/403 with advice to check account quotas or key validity.

## 15. Security and Permission Considerations
- API keys are write-only / masked; the backend never returns raw API keys in response payloads.
- Testing endpoints enforce strict timeout boundaries to prevent server hang attacks.

## 16. Related Features and Dependencies
- **Investigations** (`docs/features/investigations.md`): Uses the default model configured in Settings.
- **Autonomous Workflows** (`docs/features/autonomous-workflows.md`): Respects concurrency and token limits set in Settings.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_providers.py -q`
  - `python -m pytest backend/tests/test_provider_concurrency.py -q`
