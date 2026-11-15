# Feature Specification: Multi-Provider AI Abstraction Engine

## 1. Feature Overview
NEOMON features a vendor-neutral, multi-provider AI abstraction layer. It supports both local private model runtimes (e.g., **LM Studio**, **Ollama**) and cloud AI providers (**OpenAI**, **Anthropic**, or any OpenAI-compatible endpoint). The platform enforces deterministic structured outputs via JSON schema constraints, explicit timeout boundaries, and automated fallback to rule-based algorithms if AI providers are unreachable.

> [!IMPORTANT]
> **USER MUST PROVIDE THEIR OWN AI PROVIDER**: NEOMON is self-hosted software and does NOT come bundled with free AI credits, model subscriptions, or hosted LLM access. Users must configure their own local model runtime or provide their own API credentials.

## 2. Purpose and Problem Solved
Commercial research tools lock users into proprietary cloud LLMs, exposing sensitive research inquiries to third-party model providers and incurring high recurring API costs. NEOMON solves this by:
- Allowing researchers to run 100% confidential research workloads using local open-weight models (e.g. Llama 3, Mistral, Qwen, DeepSeek) via Ollama or LM Studio.
- Providing a unified abstraction for completion, structured JSON parsing, and temperature controls.
- Eliminating vendor lock-in through support for OpenAI-compatible APIs.

## 3. Where Users Access It
- **Settings Interface**: `/settings` (Primary provider configuration and health probe).
- **Investigation Advanced Launcher**: `/investigations/new` (Model selection dropdown).
- **Autonomous Workflow Launcher**: `/autonomous` (Agent model override).

## 4. Step-by-Step User Workflow
1. Navigate to `/settings`.
2. Locate the **AI Provider Configuration** panel.
3. Select the preferred provider architecture:
   - **LM Studio**: Set endpoint to `http://localhost:1234/v1`, specify loaded model name (e.g. `meta-llama-3-8b-instruct`).
   - **Ollama**: Set endpoint to `http://localhost:11434/v1`, specify pulled model (e.g. `llama3:latest`).
   - **OpenAI / Remote**: Input custom API base URL, model name, and API key.
4. Configure inference parameters:
   - **Temperature**: Float slider from `0.0` (deterministic scientific analysis) to `1.0` (creative hypothesis generation). Recommended: `0.1` to `0.3`.
   - **Max Tokens**: Token generation ceiling (default: 2048, max: 8192).
   - **Request Timeout**: Per-inference timeout in seconds (default: 300s).
5. Click **"Test Provider Connection"**: The platform sends an active ping probe and reports latency, model name, and health status.
6. Click **"Save Configuration"** to persist settings.

## 5. How the Feature Works Internally
1. Provider configurations are encapsulated in the `ModelConfiguration` SQLAlchemy model and loaded via `app.providers.factory`.
2. All provider clients implement the unified `BaseAIProvider` protocol with methods:
   - `generate_text(prompt, system_prompt, temperature, max_tokens)`
   - `generate_structured(prompt, response_schema, system_prompt)`
   - `check_health()`
3. **Structured Outputs**: When `generate_structured` is called, the provider enforces JSON response formatting. If the model outputs extraneous text or markdown fences, the `app.analysis.structured_output` parser strips wrapping fences and validates the payload against the Pydantic schema.
4. **Fallback Handling**: If an inference call times out or fails, the orchestrator triggers deterministic fallback heuristics without crashing the parent investigation.

## 6. Relevant Frontend Pages and Components
- `app/settings/page.tsx`: Provider configuration forms and live test triggers.
- `components/provider-context.tsx`: Client-side context distributing active provider state.
- `components/agent-observatory.tsx`: Displays active model provider and token usage per agent execution.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/providers`: Lists configured model providers and active defaults.
- `POST /api/v1/providers`: Creates or updates a model configuration.
- `POST /api/v1/providers/{id}/test`: Executes an active health probe against the target provider.
- `GET /api/v1/providers/active`: Returns currently selected provider for the active workspace.

## 8. Relevant Services and Agents
- `app.providers.factory.ProviderFactory`: Instantiates provider clients dynamically based on type.
- `app.providers.openai_compatible.OpenAICompatibleProvider`: Client for LM Studio, Ollama, and OpenAI.
- `app.providers.anthropic.AnthropicProvider`: Dedicated client for Anthropic Claude models.
- `app.analysis.structured_output`: JSON extraction and Pydantic validation engine.

## 9. Database Tables and Relationships
- `model_configurations`: Stores provider type (`lmstudio`, `ollama`, `openai`, `anthropic`, `custom`), endpoint URL, model name, encrypted API key reference, and default flag.
- `agent_executions`: Links each executed agent task to the `model_configuration_id` used for traceability.

## 10. Inputs and Outputs
- **Configuration Request**:
  ```json
  {
    "name": "Local LM Studio",
    "provider": "lmstudio",
    "endpoint": "http://localhost:1234/v1",
    "model": "meta-llama-3-8b-instruct",
    "temperature": 0.2,
    "max_tokens": 2048,
    "api_key": null
  }
  ```
- **Test Response**:
  ```json
  {
    "healthy": true,
    "latency_ms": 142.5,
    "model": "meta-llama-3-8b-instruct",
    "message": "Provider responded successfully."
  }
  ```

## 11. AI Provider Dependencies
Self-referential: This feature provides the runtime bridge for all AI capabilities across NEOMON.

## 12. External API Dependencies
- None for local runtimes (LM Studio, Ollama).
- Upstream cloud provider endpoints for OpenAI or Anthropic if configured.

## 13. Configuration Requirements
- `NEOMON_LOCAL_PROVIDER_MAX_CONCURRENCY`: Limits parallel inferences to prevent local GPU OOM (default: 1).
- `NEOMON_REMOTE_PROVIDER_MAX_CONCURRENCY`: Maximum parallel inferences for cloud APIs (default: 4).
- `NEOMON_LOCAL_INFERENCE_TIMEOUT_SECONDS`: Maximum seconds to wait for local model completion (default: 300s).

## 14. Error Handling and Limitations
- **Model Offline / Port Closed**: Returns a clean HTTP 503 error with an actionable troubleshooting guide: *"Check that LM Studio or Ollama is running and listening on the specified port."*
- **JSON Parsing Errors**: If a model produces invalid JSON, the parser attempts recovery via regex extraction before falling back to rule-based defaults.
- **Hardware Limitations**: Local inference speed depends entirely on user hardware (VRAM and CPU capacity).

## 15. Security and Permission Considerations
- API keys are never returned in plaintext to the frontend; values are masked as `••••••••`.
- SSRF safeguards: Connections to private networks or localhost are restricted to explicitly whitelisted hostnames (`localhost`, `127.0.0.1`, `::1`).

## 16. Related Features and Dependencies
- **Multi-Agent Analysis** (`docs/features/multi-agent-analysis.md`): Consumes configured models for dialectical debate.
- **Hypothesis Generation** (`docs/features/hypothesis-generation.md`): Uses models for abduction and induction.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_providers.py -q`
  - `python -m pytest backend/tests/test_structured_output.py -q`
  - `python -m pytest backend/tests/test_provider_concurrency.py -q`
