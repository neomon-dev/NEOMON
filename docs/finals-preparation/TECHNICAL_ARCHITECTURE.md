# NEOMON — Deep Technical Architecture Reference
**Engineering Specification & Subsystem Architecture**

---

## 1. System Topology Overview

NEOMON is architected as an asynchronous, event-driven, decoupled micro-monolith designed for deterministic reproducibility, high inference throughput, and zero-loss telemetry streaming.

```
+----------------------------------------------------------------------------------------------------+
|                                    NEOMON APPLICATION TOPOLOGY                                     |
+----------------------------------------------------------------------------------------------------+
                                      [ CLIENT LAYER ]
                     Next.js 16.4.6 (Turbopack) | React 19 | TypeScript
                     Cyberpunk Scientific UI | @xyflow/react | motion/react
                                             |
                     REST (JSON) + Native EventSource (SSE via tickets)
                                             v
                                  [ REVERSE PROXY / API GW ]
                               Render Host / Vercel Edge Router
                                             |
                                             v
                                   [ BACKEND CORE ENGINE ]
                      FastAPI (Python 3.12+) | AsyncIO Task Orchestrator
                      CORS Middleware | Request-ID & Structured Logging
                      Dual Route Mounting: `/api/v1/*` & `/*`
                                             |
             +-------------------------------+-------------------------------+
             |                               |                               |
             v                               v                               v
   [ PROVIDER SUBSYSTEM ]          [ RESEARCH & RETRIEVAL ]        [ PERSISTENCE LAYER ]
   InferenceLimiter (Semaphores)   Crossref API (DOI / Biblio)     Async SQLAlchemy 2.0
   OpenAI / OpenRouter / Anthropic OpenAlex API (Citations / OA)   SQLite 3.45+ (WAL Mode)
   Local LLM: Ollama / LM Studio   arXiv API (Preprints / Math)    PostgreSQL (Asyncpg driver)
   LAN Private IPv4 (192.168.x.x)  Unpaywall API (Open PDF links)  66 Relational Entity Models
   Structured Output Schemas       Tavily Search (Real-time web)   In-Memory / Redis Cache
                                   SSRF-Guarded Document Scraper   Background Worker Service
             |                               |                               |
             +-------------------------------+-------------------------------+
                                             |
                                             v
                             [ MULTI-AGENT INFERENCE ENGINE ]
                               - Intelligence Planner (Claims)
                               - Specialized Adversarial Agents:
                                 * Advocate (Positive Grounding)
                                 * Skeptic (Challenges & Gaps)
                                 * Methodology Auditor (Bias & Design)
                                 * Source Intelligence (Provenance)
                                 * Citation Genealogy (Lineage)
                                 * Temporal Intelligence (Consensus Drift)
                               - Debate Moderator (Dialectical Rounds)
                               - Conflict Adjudicator (Verdicts & Trade-offs)
                               - Report Intelligence (18 Structured Sections)
                               - EventBroker (Pub/Sub SSE Replay)
```

---

## 2. Frontend Architecture & Motion Design

### 2.1 Technology Stack
- **Framework**: Next.js 16.4.6 using Turbopack and the App Router architecture.
- **UI Library**: React 19 with Server Components for layout shells and Client Components for high-interactivity visualization.
- **Language**: TypeScript with strict type checking and zero implicit any.
- **Styling**: Tailwind CSS utilizing an optimized Cyberpunk Scientific palette (`#050914` void background, `#25D9F2` cyan, `#2787FF` electric blue, `#8564FF` violet, `#35E0B1` mint).
- **Interactive Graphing**: `@xyflow/react` v12 (React Flow) providing dynamic node layout, branch collapsing, search highlighting, and custom SVG connectors.
- **Motion Engine**: `motion` (`motion/react`) with spring physics for micro-interactions (150ms), panel transitions (250ms), and scientific scanning animations.

### 2.2 Key Frontend Components
1. `app/investigations/[id]/page.tsx`: Core command center orchestrating investigation telemetry, agent executions, claim cards, debate rounds, and report views.
2. `components/knowledge-graph-workspace.tsx` & `lib/graph.ts`: Renders an interactive directed acyclic graph mapping 16 entity types (investigations, claims, sources, documents, evidence, arguments, decisions, etc.).
3. `components/autonomous-research-workspace.tsx`: Manages autonomous research loops, iterative cycles, adaptive query refinement, and human approval gates.
4. `components/scientific-reliability-workspace.tsx`: Surfaces the Milestone 12 scientific reliability suite: 8-class evidence verification, study independence clustering, 15-dimension methodology audits, and reproducibility manifests.
5. `components/collaboration-panel.tsx` & `lib/collaboration.ts`: Real-time multi-user workspace tools including threaded discussions, inline evidence annotations, formal peer reviews, and notification center.

### 2.3 Resilient URL Resolution (`lib/api.ts`)
The frontend communicates via an adaptive URL resolver `resolveApiUrl(path: string)`:
- If `NEXT_PUBLIC_API_URL` is set to a base domain without `/api/v1` (common in Vercel/Render deployments), the resolver automatically prepends `/api/v1`.
- If the base already includes `/api/v1`, redundant prefixes in relative paths are cleanly deduplicated.
- Absolute external URLs (`http://`, `https://`) pass through unchanged.
- Guarantees seamless compatibility across local development (`http://127.0.0.1:8000/api/v1`) and cloud production deployments (`https://neomon-api-ro62.onrender.com`).

---

## 3. Backend Architecture & FastAPI Core

### 3.1 Server Lifecycle & Initialization (`backend/app/main.py`)
FastAPI utilizes an `asynccontextmanager` lifespan handler:
1. **Schema Synchronization**: Executes `conn.run_sync(Base.metadata.create_all)` to guarantee all tables exist on startup.
2. **Event Broker Initialization**: Instantiates `EventBroker` backed by `SessionFactory` for persistent event replay.
3. **State Recovery**: Triggers `AnalysisManager.recover()` and `autonomous_workflow_service.recover_workflows()` to resume active tasks interrupted by server restarts.
4. **Admin Seeding**: Configures production administrator credentials if `NEOMON_INITIAL_ADMIN_PASSWORD` is supplied.
5. **Background Worker**: Starts `worker_service` if `settings.worker_enabled` is active.

### 3.2 Dual Route Mounting Strategy
To eliminate deployment discrepancies between cloud environments (Render, Vercel) and legacy clients:
```python
# Mounted both at /api/v1 and root /
app.include_router(health.router)
app.include_router(health.router, prefix=prefix)
app.include_router(providers.router, prefix=prefix)
app.include_router(providers.router)
app.include_router(agents.router, prefix=prefix)
app.include_router(agents.router)
app.include_router(research.router, prefix=prefix)
app.include_router(research.router)
app.include_router(auth.router, prefix=prefix)
app.include_router(auth.router)
# (repeated across all 18 core routers)
```
- Direct access to `https://neomon-api-ro62.onrender.com/` returns HTTP 200 OK with service metadata, documentation links, and health status.
- Requests to both `/agents` and `/api/v1/agents` resolve to identical route handlers.

---

## 4. Database Schema & Persistence Architecture

NEOMON uses SQLAlchemy 2.0 async ORM with complete support for both **SQLite (WAL Mode)** for zero-dependency local runs and **PostgreSQL** for enterprise scale.

```
                           +------------------------+
                           |      INVESTIGATION     |
                           | id, title, question,   |
                           | status, created_at     |
                           +-----------+------------+
                                       | 1:N
         +-----------------------------+-----------------------------+
         |                             |                             |
         v                             v                             v
+------------------+          +------------------+          +------------------+
|      SOURCE      |          |      CLAIM       |          |   ANALYSIS_JOB   |
| id, title, url,  |          | id, text,        |          | id, status,      |
| doi, venue, year |          | priority, order  |          | started_at       |
+--------+---------+          +--------+---------+          +--------+---------+
         | 1:N                         | 1:N                         | 1:N
         v                             v                             v
+------------------+          +------------------+          +------------------+
|     DOCUMENT     |          |  CLAIM_EVIDENCE  |          | AGENT_EXECUTION  |
| id, raw_text,    |          |  RELATIONSHIP    |          | id, agent_name,  |
| hash, word_count |          | classification,  |          | status, tokens   |
+--------+---------+          | confidence, reasoning       +--------+---------+
         | 1:N                +--------+---------+                   | 1:N
         v                             ^                             v
+------------------+                   |                    +------------------+
|     EVIDENCE     +-------------------+                    |  AGENT_ARGUMENT  |
| id, exact_text,  |                                        | id, argument_type|
| start_idx, end   |                                        | text, evidence_ids
+------------------+                                        +--------+---------+
                                                                     | 1:N
                                                                     v
                                                            +------------------+
                                                            |   DEBATE_ROUND   |
                                                            | & ADJUDICATION   |
                                                            | round_num, verdict
                                                            +------------------+
```

### 4.1 Key Relational Entities (66 Models)
- **Investigation Layer**: `Investigation`, `ResearchQuery`, `Source`, `Document`, `OpenAccessLocation`, `DocumentVersionRelationship`.
- **Evidence Layer**: `Evidence`, `Claim`, `ClaimEvidenceRelationship`, `EvidenceVerificationRecord`.
- **Inference & Debate Layer**: `AnalysisJob`, `AnalysisAgentExecution`, `AgentArgument`, `DebateRound`, `AdjudicationDecision`.
- **Synthesis & Reports**: `ResearchReport`, `ReportSection` (18 structured types), `ReportVersion`.
- **Milestone 12 Integrity Models**:
  - `StudyIndependenceCluster`: Maps duplicate publications and shared study lineage.
  - `MethodologyAuditFinding`: Records findings across 15 audit dimensions.
  - `ResearchExecutionManifest`: Cryptographically frozen SHA-256 execution snapshot.
  - `BenchmarkDataset` & `BenchmarkRun`: Ground-truth evaluations and regression tracking.
  - `HumanEvidenceCorrection`: Immutable audit log of human expert overrides.
- **Collaboration & Tenancy Layer**: `User`, `UserSession`, `Workspace`, `WorkspaceMember`, `WorkspaceInvitation`, `CommentThread`, `Comment`, `EvidenceAnnotation`, `ReviewRequest`, `ReviewDecision`, `Notification`, `WorkspaceActivity`.

---

## 5. AI Provider Abstraction & Concurrency Control

### 5.1 Provider Architecture (`backend/app/providers/`)
All AI providers implement `AIProvider` base class (`base.py`):
- `generate_text(prompt, model, system_prompt, ...)`
- `generate_json(prompt, model, response_model, ...)`

Supported implementations:
1. `OpenAICompatibleProvider`: Interfaces with OpenAI (GPT-4o, o1), OpenRouter, Groq, Together, LM Studio, and Ollama's OpenAI compatibility endpoint.
2. `OllamaProvider`: Direct client for Ollama's native `/api/generate` and `/api/chat` endpoints.
3. `MockProvider`: Deterministic, zero-network rule-based provider ensuring 100% test coverage without external API keys.

### 5.2 Concurrency & Rate Limiting (`backend/app/providers/limiter.py`)
Local models and cloud APIs have strict concurrency and rate constraints:
- `InferenceLimiter`: Implements an `asyncio.Semaphore` combined with an in-memory token bucket.
- Tracks dynamic states: `waiting_in_queue` -> `generating` -> `completed` / `failed`.
- Emits real-time state change events via `InferenceStateCallback` so frontend agent cards display live progress rings and elapsed seconds.
- Handles queue timeouts (`ProviderQueueTimeoutError`) and prevents GPU VRAM exhaustion when running local 70B/8B parameter models.

### 5.3 Local Model & Private LAN Security
- Supports local endpoints (`http://localhost:11434`, `http://127.0.0.1:1234`, `http://192.168.1.7:1345`).
- Preserves strict SSRF (Server-Side Request Forgery) protection:
  - Private IP addresses (`127.0.0.1`, `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`) are **strictly blocked** for remote document retrieval and web scrapers (`app/research/retrieval.py`).
  - Private LAN IPs are allowed **only** when explicitly configured in AI Provider settings (`allow_local_runtime=True`).
  - Automatic URL sanitization: Prevents duplicate `/v1/v1` path concatenation when connecting to LM Studio or Ollama.

---

## 6. Real-Time Telemetry & SSE Streaming Security

### 6.1 Server-Sent Events Architecture (`backend/app/events.py`)
- Real-time client updates are powered by an in-memory `EventBroker` pub/sub bus.
- Supports gapless reconnection: Clients pass `Last-Event-ID` header, and the broker replays persisted events stored in `ResearchEvent` table.

### 6.2 Transient Stream Tickets (`POST /api/v1/auth/stream-ticket`)
- **Vulnerability Addressed**: Native browser `EventSource` cannot pass custom HTTP headers (`Authorization: Bearer <jwt>`). Passing long-lived JWTs in URL query parameters (`/events?token=...`) exposes credentials in proxy logs, browser histories, and referrer headers.
- **NEOMON Solution**:
  1. Frontend performs an authenticated POST to `/api/v1/auth/stream-ticket`.
  2. Backend generates a cryptographically random, high-entropy ticket (`st_<uuid>`) with a 60-second TTL.
  3. Ticket is stored in cache/DB and associated with the user ID and investigation ID.
  4. Frontend connects to `EventSource` with `?ticket=st_...`.
  5. The backend validates the ticket, immediately deletes it (atomic single-use consumption), and promotes the connection to an active SSE stream.
  6. Replay attacks using intercepted tickets fail immediately with HTTP 401 Unauthorized.

---

## 7. Multi-Agent Orchestration Pipeline

```
[ User Input: Research Question ]
               |
               v
     [ Intelligence Planner ]
       - Extracts core research subject
       - Decomposes into 1-5 atomic claims
       - Formulates search objectives
               |
               v
     [ Document Acquisition ]
       - OpenAlex, Crossref, arXiv, Unpaywall, Tavily
       - HTML/PDF download & text extraction
       - Sentence-level evidence extraction
               |
               v
     [ Evidence-to-Claim Mapping ]
       - Vector/Lexical similarity & classification
       - Direct support / Context / Contradiction
               |
               v
     [ Concurrent Specialist Agents ] (Controlled by Semaphore)
       +-----------------------+-----------------------+-----------------------+
       |       Advocate        |        Skeptic        |  Methodology Auditor  |
       |  Builds strongest     | Hunts for flaws, gaps | Checks sample size,   |
       |  evidence-backed case | and counter-evidence  | controls, and biases  |
       +-----------------------+-----------------------+-----------------------+
       |  Source Intelligence  |  Citation Genealogy   | Temporal Intelligence |
       |  Publisher credibility| Citation loops and    | Chronological consensus|
       |  and peer-review tier | foundational lineage  | drift over time       |
       +-----------------------+-----------------------+-----------------------+
               |
               v
     [ Debate Moderator ]
       - Compares persisted specialist arguments
       - Identifies unresolved tensions and missing evidence
       - Conducts structured debate rounds (1 to max_rounds)
               |
               v
     [ Conflict Adjudicator ]
       - Evaluates claim-by-claim dialectic
       - Renders verdict: strongly supported, contradictory, insufficient
       - Assigns calibrated confidence scores
               |
               v
     [ Report Intelligence ]
       - Generates 18 structured research sections
       - Generates executive summary and methodology audit
       - Creates immutable SHA-256 reproducibility manifest
```

### 7.1 Strict Grounding & Schema Validation
In `backend/app/analysis/service.py`:
- All specialist agents are required to return strict Pydantic JSON schemas.
- `_validate_role_payload`:
  - Enforces that arguments reference **only** evidence UUIDs that actually exist in the investigation.
  - Ensures cited `source_ids` strictly match the parent `source_id` of the cited evidence.
  - Rejects hallucinated citations before any database persistence occurs.
  - If a model hallucinates a non-existent evidence ID, NEOMON automatically strips the phantom ID and downgrades the confidence to `"insufficient"` rather than trusting unverified claims.

---

## 8. Failure Handling & Resilience Matrix

| Component | Failure Mode | Mitigation / Fallback Mechanism |
|---|---|---|
| **Cloud AI Provider** | Rate limit, timeout, or quota exhaustion | `InferenceLimiter` retries with exponential backoff; falls back to deterministic rule-based grounding if provider unreachable. |
| **Local LLM Server** | Out of VRAM or process crash | Connection diagnostics detect failure immediately; reports exact IP/port error with actionable user fix. |
| **Academic API** | 429 Too Many Requests (OpenAlex/Crossref) | Circuit breaker catches 429; continues investigation using available ingested sources and cached metadata. |
| **Document Scraper** | Paywalled paper, 403 Forbidden, or bot check | Document marked `retrieval_failed`; OpenAccess fallback checks Unpaywall for legal open PDFs; if unavailable, uses published abstract. |
| **Backend Server** | Sudden restart / OS reboot during analysis | `lifespan` triggers `AnalysisManager.recover()`; resumes interrupted investigations and autonomous cycles from last DB checkpoint. |
| **Client Browser** | Tab closed or network disconnect during SSE | `Last-Event-ID` header allows gapless catch-up upon reconnection; full state is durably persisted in SQLite/PostgreSQL. |
