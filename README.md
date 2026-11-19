# NEOMON — Neural Evidence Orchestration & Multi-Agent Observation Network

[![Backend Test Suite](https://img.shields.io/badge/Backend%20Tests-226%20Passed-emerald.svg)](backend/tests)
[![Frontend Test Suite](https://img.shields.io/badge/Frontend%20Tests-15%20Passed-emerald.svg)](__tests__)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict%20Verified-blue.svg)](tsconfig.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16%20Turbopack-black.svg)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B%20Compatible-336791.svg)](backend/migrations)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Engine-003B57.svg)](backend/neomon.db)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> **NEOMON** is an enterprise-grade research intelligence platform engineered to transform unstructured scientific literature and real-time public web intelligence into structured, provenance-verified evidence graphs, dialectical multi-agent debates, and audit-ready scientific evaluations.

---

## Sign in email and password
Email: auditor_qa@neomon.ai or admin@neomon.ai
Password: Password123!

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [Target Audience & Comparative Distinction](#2-target-audience--comparative-distinction)
3. [Core Capabilities & Research Pillars](#3-core-capabilities--research-pillars)
4. [Technology Stack](#4-technology-stack)
5. [System Architecture](#5-system-architecture)
6. [Windows Installation & Getting Started](#6-windows-installation--getting-started)
7. [CRITICAL NOTICE: User-Supplied AI Provider Requirement](#7-critical-notice-user-supplied-ai-provider-requirement)
8. [CRITICAL NOTICE: Optional Tavily Search Configuration](#8-critical-notice-optional-tavily-search-configuration)
9. [Comprehensive Environment Variable Reference](#9-comprehensive-environment-variable-reference)
10. [Database Management & Migration Strategy](#10-database-management--migration-strategy)
11. [Production Deployment Architecture](#11-production-deployment-architecture)
12. [Security, Privacy & Compliance Architecture](#12-security-privacy--compliance-architecture)
13. [Troubleshooting Guide & Diagnostics](#13-troubleshooting-guide--diagnostics)
14. [Feature Documentation Index](#14-feature-documentation-index)
15. [License & Contribution Terms](#15-license--contribution-terms)

---

## 1. Executive Summary & Problem Statement

Modern scientific, biomedical, and technological discovery faces a severe reproducibility crisis. Over **3 million scientific articles** are published annually across thousands of journals, making comprehensive literature syntheses computationally intractable for human researchers alone. Concurrently, generative AI tools (such as standard chat LLMs) fail catastrophically in scientific domains due to three fundamental architectural flaws:

1. **Hallucination & Fabrication**: Generic LLMs hallucinate plausible-sounding mechanisms, statistical figures, and non-existent bibliographies.
2. **Confirmation Bias & Sycophancy**: Conversational models inherently optimize for agreeableness, uncritically validating biased research hypotheses rather than stress-testing causal claims.
3. **Absence of Provenance & Auditability**: LLM summaries lack exact text offsets, document hashes, and page provenance, rendering their outputs legally and scientifically non-reproducible.

**NEOMON solves this crisis.**

NEOMON rejects conversational "black-box" answering in favor of an **auditable, dialectical, and deterministic evidence orchestration pipeline**. Instead of generating ungrounded text, NEOMON queries real academic and web indices (arXiv, Crossref, OpenAlex, Unpaywall, Tavily), parses and hashes candidate documents, extracts exact character-offset evidence passages, and submits those passages to a structured debate between competing AI agents (Advocate vs. Skeptic vs. Methodologist). Every claim is linked directly to an immutable source passage, audited for methodological rigor (sample size, blinding, p-hacking risk), and placed onto an interactive, multi-relational knowledge graph.

---

## 2. Target Audience & Comparative Distinction

### Target Audience

* **Academic & Biomedical Researchers**: Conducting meta-analyses, systematic reviews, and grant proposal background investigations.
* **Clinical Trial Evaluators**: Verifying therapeutic efficacy claims, checking study power, and uncovering publication bias or funding conflicts.
* **Technology Intelligence & Due Diligence Analysts**: Evaluating emerging patents, semiconductor breakthroughs, or algorithm benchmarks before major capital allocation.
* **Policy Makers & Think Tanks**: Synthesizing contradictory scientific consensus across climate, energy, and epidemiology without political bias.

### How NEOMON Differs from Ordinary AI Chat

| Architectural Dimension | Generic Conversational LLM (e.g. ChatGPT, Claude) | NEOMON Research Intelligence Platform |
|---|---|---|
| **Primary Interaction Mode** | Conversational chat interface | Structured investigation workspace & knowledge observatory |
| **Evidence Grounding** | Parameterized memory with loose web search | Strict character-level provenance mapped to sha256-hashed documents |
| **Citation Authenticity** | Frequently hallucinates papers, DOIs, and authors | 100% verified against Crossref, OpenAlex, arXiv, and DOI registries |
| **Dialectical Stress-Testing** | Monolithic generation prone to sycophancy | Adversarial multi-agent debate (Advocate vs Skeptic with Moderator) |
| **Methodological Auditing** | None; accepts paper abstracts uncritically | Algorithmic scoring of statistical power, p-hacking, and blinding |
| **Contradiction Handling** | Smooths over conflicts with vague prose | Explicit contradiction graph mapping opposing claims and evidence |
| **Citation Genealogy** | Cannot detect circular citations | Algorithmic clustering of source lineages to verify study independence |
| **Data Privacy & Keys** | Transmits prompts to central cloud vendor | **BYOM Architecture**: API keys held in browser memory; local LLMs supported |
| **Export Formats** | Raw Markdown / Text chat | Audit-ready PDF, BibTeX, RIS citation manifests, CSV, and JSON |

---

## 3. Core Capabilities & Research Pillars

```
+---------------------------------------------------------------------------------------+
|                                    NEOMON ENGINE                                      |
+--------------------------+----------------------------+-------------------------------+
|  RETRIEVAL & DISCOVERY   |    EVIDENCE & INTEGRITY    |   MULTI-AGENT ADJUDICATION    |
|  - arXiv API             |  - Exact Passage Hashing   |  - Advocate Agent             |
|  - Crossref API          |  - Character Provenance    |  - Skeptic Agent              |
|  - OpenAlex API          |  - Methodological Auditing |  - Moderator Adjudication     |
|  - Unpaywall Integration |  - P-Hacking Risk Analysis |  - Methodology Auditor        |
|  - Tavily Web Crawler    |  - Citation Genealogy      |  - Domain Specialists         |
+--------------------------+----------------------------+-------------------------------+
|   LONGITUDINAL INSIGHTS  |     KNOWLEDGE TOPOLOGY     |     GOVERNANCE & WORKFLOW     |
|  - Contradiction Engine  |  - React Flow Entity Graph |  - Multi-User Workspaces      |
|  - Research Gap Mining   |  - 16 Relational Entity IDs|  - Role-Based Access Control  |
|  - Hypothesis Generation |  - Claim-to-Evidence Links |  - Autonomous Convergence     |
|  - Trend Trajectories   |  - Interactive Filtering   |  - Multi-Format Knowledge Exp |
+--------------------------+----------------------------+-------------------------------+
```

### 1. Autonomous Hypothesis & Query Decomposition
Given an arbitrary research topic or clinical query, NEOMON decomposes the prompt into four orthogonal research vectors: causal mechanisms, counter-evidence, empirical benchmarks, and critical perspectives. It preserves technical acronyms (e.g., *GLP-1*, *DDR5*, *LoRA*, *CRISPR*) to prevent semantic drift.

### 2. Multi-Source Academic & Web Retrieval
Simultaneously interrogates arXiv, Crossref, and OpenAlex for peer-reviewed literature, preprints, and open-access PDFs via Unpaywall. When configured, the engine dispatches concurrent, rate-controlled queries to Tavily Search for real-time web discovery without delaying academic passes.

### 3. Provenance-Preserving Evidence Extraction
Documents are downloaded via SSRF-safe HTTP clients, stripped of markup, hashed via SHA-256, and indexed into distinct passages. Passages retain exact `character_start`, `character_end`, section headers, page numbers, and URL provenance.

### 4. Scientific Methodology Audit & Quality Calibration
Evaluates papers using formal criteria: statistical sample sizes ($N$), presence of double-blinding, randomization protocols, effect sizes ($d$, $R^2$), and p-hacking indicators. Documents are calibrated into confidence intervals rather than arbitrary popularity metrics.

### 5. Dialectical Multi-Agent Debate Engine
Once evidence is indexed, specialized agents engage in a formal debate:
* **The Advocate Agent**: Formulates the strongest evidence-backed argument supporting the hypothesis.
* **The Skeptic Agent**: Identifies methodological flaws, conflicting evidence, sample bias, and funding conflicts.
* **The Moderator Agent**: Adjudicates claims, evaluates strength of arguments, and computes final synthesis consensus scores.

### 6. Contradiction Intelligence & Resolution
Automatically detects conflicting claims across disparate research teams. Distinguishes direct factual contradictions from temporal shifts, methodological variances, and differing cohort definitions.

### 7. Citation Genealogy & Study Independence
Analyzes citation networks to detect circular citation loops and paper lineages. Identifies whether ten supporting papers are independent trials or merely citing a single unverified initial study.

### 8. Interactive Knowledge Graph Explorer
Visualizes the entire research domain using an interactive React Flow graph. Nodes represent Claims, Evidence, Sources, Agents, and Decisions, connected by typed relational edges (`SUPPORTS`, `REFUTES`, `CITES`, `AUDITS`).

### 9. Longitudinal Trend & Research Gap Discovery
Tracks shifting scientific consensus over time. Detects underexplored intersections, structural voids, and blind spots in existing research corpora, and computes prioritized research gap vectors.

### 10. Autonomous Hypothesis Generation & Experimental Design
Synthesizes gap analyses into testable, mathematically falsifiable scientific hypotheses complete with recommended experimental methodologies, sample sizes, and control designs.

### 11. Multi-Cycle Autonomous Research Loops
Supports hands-off or human-in-the-loop autonomous research cycles. The engine executes multiple iterations of query refinement, source discovery, and debate until target confidence thresholds are achieved.

### 12. Multi-Format Knowledge Export
Exports complete audit trails in six production formats: publication-ready PDF, structured Markdown, machine-readable JSON, BibTeX citation databases, RIS library files, and tabular CSV evidence ledgers.

### 13. Collaborative Multi-User Workspaces & Ground-Truth Benchmarks
Enables multi-user institutional collaboration with granular Role-Based Access Control (Admin, Member, Viewer). Built-in benchmark datasets allow teams to measure extraction accuracy against human ground truth.

---

## 4. Technology Stack

| Layer | Technologies & Libraries | Architectural Role |
|---|---|---|
| **Frontend Framework** | **Next.js 16** (App Router, Turbopack) | Modern server and client components, fast incremental rendering |
| **UI Library** | **React 19**, **TypeScript** (Strict Mode) | Type-safe state management, reactive interfaces, modern hooks |
| **Styling & Icons** | **Tailwind CSS**, **Lucide React** | Responsive, accessible dark/light theme design system |
| **Knowledge Graph** | **React Flow** (`@xyflow/react`) | Interactive, hardware-accelerated node-and-edge graph visualization |
| **Backend Framework** | **FastAPI** (Python 3.12+, 3.13, 3.14 verified) | High-performance asynchronous REST API with OpenAPI specifications |
| **Validation & Settings** | **Pydantic v2**, **Pydantic-Settings** | Strict data schemas, runtime request validation, environment configuration |
| **Data Persistence** | **SQLAlchemy 2.0 (Asyncio)** | Unified asynchronous ORM across SQLite and PostgreSQL |
| **Database Engines** | **PostgreSQL 15+** (Production) / **SQLite WAL** (Dev) | Cloud-scale relational persistence with atomic local fallback |
| **Schema Migrations** | **Alembic** | Version-controlled, deterministic database migrations |
| **Async Networking** | **HTTPX (AsyncClient)** | Non-blocking, connection-pooled academic retrieval with SSRF guards |
| **Cryptographic Security** | **PBKDF2-HMAC-SHA256 (600k iter)**, **Secrets** | NIST-compliant password hashing, constant-time token verification |
| **AI Integration** | **OpenAI-Compatible REST Spec** | Universal bring-your-own-model protocol (Ollama, LM Studio, Groq, etc.) |
| **Web Intelligence** | **Tavily Search API (Optional)** | Domain-isolated, concurrent real-time public web intelligence |
| **Testing Harnesses** | **Pytest**, **Pytest-Asyncio**, **Vitest**, **React Testing Library** | 226 backend tests and 15 frontend unit tests ensuring complete stability |

---

## 5. System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer["User Interface (Next.js 16 / React 19)"]
        BrowserUI["Next.js App Router (localhost:3000 / Vercel)"]
        AuthContext["Auth & Workspace Context (Session Tokens)"]
        ModelContext["AI Provider Config (React In-Memory State)"]
        GraphExplorer["React Flow Knowledge Graph"]
    end

    subgraph BackendGateway["FastAPI Gateway (backend/app/main.py)"]
        CORSMiddleware["CORS & Proxy Middleware"]
        RateLimiter["Token-Bucket Rate Limiter"]
        RouterAuth["Auth & Tenancy Router (/api/v1/auth)"]
        RouterResearch["Research & Investigation Router (/api/v1/research)"]
        RouterAgents["Multi-Agent Analysis Router (/api/v1/analysis)"]
        RouterAutonomous["Autonomous Loop Router (/api/v1/autonomous)"]
        SSEBroker["Durable Event Broker (Server-Sent Events)"]
    end

    subgraph StorageLayer["Data Persistence & State Management"]
        AlembicEngine["Alembic Migrations (0001 - 0017)"]
        SQLAlchemyAsync["SQLAlchemy 2.0 Async Session Engine"]
        SQLiteDB[("SQLite 3 (WAL Mode)\nbackend/neomon.db")]
        PostgresDB[("Render PostgreSQL 15+\n(Production Database)")]
    end

    subgraph RetrievalEngine["Academic & Web Discovery Pipeline"]
        arXivClient["arXiv API Client"]
        CrossrefClient["Crossref DOI Client"]
        OpenAlexClient["OpenAlex Meta-Science Client"]
        UnpaywallClient["Unpaywall Open Access Client"]
        TavilyClient["Tavily Search Client (Optional API Key)"]
        SSRFGuard["SSRF & DNS Rebinding Validator"]
    end

    subgraph AgentEngine["Multi-Agent Adjudication Pool"]
        AdvocateAgent["Advocate Agent (Pro-Hypothesis)"]
        SkepticAgent["Skeptic Agent (Counter-Evidence & Bias)"]
        MethodologyAgent["Methodology Auditor (Power & P-Hacking)"]
        ModeratorAgent["Moderator (Consensus & Synthesis)"]
    end

    subgraph ExternalAI["User-Supplied AI Models (Zero Bundled Credits)"]
        LocalOllama["Local Ollama (http://localhost:11434)"]
        LocalLMStudio["Local LM Studio (http://localhost:1234)"]
        RemoteOpenAI["OpenAI-Compatible Remote API (Groq, Together, OpenAI)"]
    end

    %% Connections
    BrowserUI --> CORSMiddleware
    AuthContext --> RouterAuth
    ModelContext --> RouterAgents
    CORSMiddleware --> RateLimiter
    RateLimiter --> RouterAuth
    RateLimiter --> RouterResearch
    RateLimiter --> RouterAgents
    RateLimiter --> RouterAutonomous

    RouterResearch --> SSRFGuard
    SSRFGuard --> arXivClient
    SSRFGuard --> CrossrefClient
    SSRFGuard --> OpenAlexClient
    SSRFGuard --> UnpaywallClient
    SSRFGuard --> TavilyClient

    RouterAgents --> AdvocateAgent
    RouterAgents --> SkepticAgent
    RouterAgents --> MethodologyAgent
    RouterAgents --> ModeratorAgent

    AdvocateAgent -.-> LocalOllama
    SkepticAgent -.-> LocalLMStudio
    MethodologyAgent -.-> RemoteOpenAI
    ModeratorAgent -.-> RemoteOpenAI

    RouterResearch --> SQLAlchemyAsync
    RouterAgents --> SQLAlchemyAsync
    RouterAutonomous --> SQLAlchemyAsync
    SQLAlchemyAsync --> SQLiteDB
    SQLAlchemyAsync --> PostgresDB
    AlembicEngine --> SQLiteDB
    AlembicEngine --> PostgresDB
    RouterResearch --> SSEBroker
    SSEBroker --> BrowserUI
```

---

## 6. Windows Installation & Getting Started

### Prerequisites

* **Operating System**: Windows 10/11, macOS, or Linux.
* **Node.js**: Version `18.18.0` or higher (verified on Node 20 / 22).
* **Python**: Version `3.12` or higher (verified on Python 3.12, 3.13, 3.14).
* **Git**: Installed and configured.
* **PowerShell**: Windows PowerShell 5.1 or PowerShell Core 7+.

---

### Step 1: Clone the Repository

Open Windows PowerShell and clone the codebase:

```powershell
git clone https://github.com/neomon-dev/NEOMON.git
Set-Location NEOMON
```

---

### Step 2: Frontend Setup & Dependencies

Install Node.js dependencies:

```powershell
npm install
```

Configure local environment variables:

```powershell
Copy-Item .env.example .env.local
```

Ensure `NEXT_PUBLIC_API_URL` in `.env.local` points to your backend instance:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Verify frontend compilation and test suite:

```powershell
# Run frontend unit tests
npm test

# Run ESLint check
npm run lint

# Run TypeScript typecheck
npx tsc --noEmit
```

---

### Step 3: Backend Setup & Python Virtual Environment

Create and activate a clean Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Verify backend byte-compilation:

```powershell
python -m compileall backend/app backend/migrations
```

---

### Step 4: Database Migrations

Apply the complete Alembic migration sequence to initialize the database:

```powershell
Set-Location backend
python -m alembic upgrade head
Set-Location ..
```

*Note: By default, NEOMON utilizes an atomic SQLite database configured with Write-Ahead Logging (`WAL` mode) located at `backend/neomon.db`. To target PostgreSQL instead, set `NEOMON_DATABASE_URL` as detailed in [Section 9](#9-comprehensive-environment-variable-reference).*

---

### Step 5: Execute Regression Test Suites

Confirm full system integrity before launching the servers:

```powershell
# Run backend pytest suite (226 tests)
python -m pytest backend/tests -q
```

All 226 tests should pass cleanly in ~30 seconds.

---

### Step 6: Launch Development Servers

Launch both servers in parallel:

**Terminal 1 — FastAPI Backend (Port 8000):**
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js Frontend (Port 3000):**
```powershell
npm run dev
```

Navigate to `http://localhost:3000` in your web browser. The backend API specification is accessible at `http://localhost:8000/api/v1/docs`.

---

## 7. CRITICAL NOTICE: User-Supplied AI Provider Requirement

> [!IMPORTANT]
> **NEOMON PROVIDES ZERO FREE MODEL ACCESS OR BUNDLED API CREDITS.**
> 
> NEOMON is built on a strict **Bring-Your-Own-Model (BYOM)** architecture. The platform does not host proprietary LLM infrastructure, does not bundle API credits, and does not charge subscription fees for token generation. Users must supply their own local model runner (such as LM Studio or Ollama) or configure their own API keys for remote OpenAI-compatible providers.

### Supported Provider Types

```
                                  +---------------------------------------+
                                  |         NEOMON Provider Engine        |
                                  +-------------------+-------------------+
                                                      |
                   +----------------------------------+----------------------------------+
                   |                                                                     |
         +---------v---------+                                                 +---------v---------+
         |   LOCAL RUNNERS   |                                                 |    REMOTE APIS    |
         |  (100% Free & PVT)|                                                 | (User's Own Keys) |
         +---------+---------+                                                 +---------+---------+
                   |                                                                     |
         +---------+---------+                                                 +---------+---------+
         |                   |                                                 |                   |
   +-----v-----+       +-----v-----+                                     +-----v-----+       +-----v-----+
   | LM Studio |       |  Ollama   |                                     |  OpenAI   |       | Groq /    |
   | Port 1234 |       |Port 11434 |                                     |  Direct   |       | Together  |
   +-----------+       +-----------+                                     +-----------+       +-----------+
```

### Option A: Local LM Studio Setup (Recommended for Local Privacy)

1. Download and install **LM Studio** from [lmstudio.ai](https://lmstudio.ai).
2. Download an instruction-tuned model (e.g., `Meta-Llama-3.1-8B-Instruct`, `Mistral-7B-Instruct-v0.3`, or `Qwen2.5-7B-Instruct`).
3. Navigate to the **Local Server** tab in LM Studio.
4. Set port to `1234` and start the server.
5. In NEOMON, open **Settings (`/settings`)** -> **AI Provider Configuration**:
   * **Provider Type**: `LM Studio`
   * **Base URL**: `http://localhost:1234/v1`
   * **Model Identifier**: Enter your loaded model name (e.g., `meta-llama-3.1-8b-instruct`).
   * **API Key**: Leave blank or enter `lm-studio`.
6. Click **Test Provider Connection** to verify end-to-end communication.

### Option B: Local Ollama Setup

1. Install **Ollama** from [ollama.com](https://ollama.com).
2. Pull a recommended research model from your terminal:
   ```powershell
   ollama pull llama3.1:8b
   ```
3. Set the environment variable to allow web origin requests before starting Ollama:
   ```powershell
   $env:OLLAMA_ORIGINS = "*"
   ollama serve
   ```
4. In NEOMON **Settings (`/settings`)**:
   * **Provider Type**: `Ollama`
   * **Base URL**: `http://localhost:11434/v1`
   * **Model Identifier**: `llama3.1:8b`
   * **API Key**: Leave empty.
5. Click **Test Provider Connection**.

### Option C: Remote OpenAI-Compatible Providers

NEOMON supports any provider that adheres to the standard OpenAI `/v1/chat/completions` specification:

* **OpenAI Direct**: `https://api.openai.com/v1` (Models: `gpt-4o`, `gpt-4o-mini`)
* **Groq Cloud (Ultra-Fast Inference)**: `https://api.groq.com/openai/v1` (Models: `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`)
* **Together AI**: `https://api.together.xyz/v1`
* **Mistral AI**: `https://api.mistral.ai/v1`
* **Self-Hosted vLLM / TGI**: `http://your-server-ip:8000/v1`

### Hardware Sizing Considerations for Local Inference

* **Minimum (7B/8B Models, 4-bit Quantization)**: 16 GB System RAM, or 6 GB VRAM GPU (NVIDIA RTX 3060/4060 or Apple Silicon M1/M2/M3 with 16GB unified memory).
* **Recommended (14B/32B Models)**: 32 GB System RAM, or 16 GB VRAM GPU (NVIDIA RTX 3090/4080/4090 or Apple Silicon with 36GB+ memory).
* **Commercial Scale (70B+ Models)**: Remote inference API (Groq, Together, OpenAI) or multi-GPU workstation (48GB+ VRAM).

### Zero-Cost Rule-Based Fallback
If no AI provider is configured or available, NEOMON **does not fail**. It automatically falls back to deterministic, rule-based algorithmic extraction and debate synthesis. These outputs are clearly badged as `rule_based` across all interfaces, guaranteeing complete transparency.

---

## 8. CRITICAL NOTICE: Optional Tavily Search Configuration

> [!NOTE]
> **TAVILY SEARCH IS AN OPTIONAL CAPABILITY FOR GENERAL PUBLIC WEB RETRIEVAL.**
> 
> Out of the box, NEOMON connects to **arXiv, Crossref, and OpenAlex** with **ZERO API keys required**. Academic literature discovery, full-text open-access retrieval, and peer-review normalization operate fully without Tavily.

### How Tavily Search Functions in NEOMON

Tavily Search provides supplemental public web indexing for investigations where contemporary news, clinical press releases, institutional whitepapers, or industrial technical reports are required alongside academic publications.

* **Key Provisioning**: Sign up at [tavily.com](https://tavily.com) to obtain a free or commercial API key.
* **Environment Configuration**: Set either `TAVILY_API_KEY` or `NEOMON_TAVILY_API_KEY` in your backend `.env` file:
  ```env
  TAVILY_API_KEY=tvly-prod-your-actual-api-key-here
  ```
* **Concurrent Execution**: When configured, Tavily executes concurrently with academic providers, executing domain-isolated queries without blocking academic passes.
* **Graceful Degradation**: If Tavily is not configured, is disabled (`NEOMON_TAVILY_ENABLED=false`), or exhausts its monthly quota, NEOMON logs a telemetry event and proceeds seamlessly using academic providers alone. No requests fail or crash due to an absent Tavily key.

---

## 9. Comprehensive Environment Variable Reference

All backend settings support the `NEOMON_` prefix and are defined in `backend/app/config.py`.

### Backend Settings Reference

| Variable Name | Type | Default Value | Description & Production Recommendations |
|---|---|---|---|
| `NEOMON_APP_NAME` | `string` | `"NEOMON API"` | Display name for the API service reported in health endpoints. |
| `NEOMON_ENVIRONMENT` | `string` | `"development"` | Environment profile: `"development"`, `"staging"`, or `"production"`. |
| `NEOMON_DEBUG` | `boolean` | `false` | Enable verbose debugging information and stack traces. |
| `NEOMON_API_VERSION` | `string` | `"v1"` | URL path versioning prefix for all API routes. |
| `NEOMON_DATABASE_URL` | `string` | `sqlite+aiosqlite:///backend/neomon.db` | SQLAlchemy connection string. Set to `postgresql+asyncpg://...` in production. |
| `NEOMON_ALLOWED_ORIGINS` | `csv` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS allowed origin list. In production, set to your Vercel URL. |
| `NEOMON_ALLOWED_LOCAL_PROVIDER_HOSTS`| `csv` | `localhost,127.0.0.1,::1` | Permitted hostnames for local AI provider endpoints (SSRF guard). |
| `NEOMON_DEMO_MODE` | `boolean` | `true` | When true, marks synthesized test investigations with explicit demo banners. |
| `NEOMON_REQUEST_TIMEOUT_SECONDS` | `float` | `15.0` | Default network request timeout for general external HTTP calls. |
| `NEOMON_LOCAL_INFERENCE_TIMEOUT_SECONDS` | `float` | `300.0` | Extended timeout (up to 1800s) for long local LLM inference batches. |
| `NEOMON_PROVIDER_QUEUE_MAX_SIZE` | `integer` | `50` | Maximum queue depth for pending provider analysis jobs. |
| `NEOMON_LOCAL_PROVIDER_MAX_CONCURRENCY` | `integer` | `1` | Concurrency ceiling for local models to prevent GPU/CPU memory thrashing. |
| `NEOMON_REMOTE_PROVIDER_MAX_CONCURRENCY`| `integer` | `4` | Concurrency ceiling for remote cloud API providers. |
| `NEOMON_DATABASE_POOL_SIZE` | `integer` | `10` | SQLAlchemy connection pool size for PostgreSQL connections. |
| `NEOMON_DATABASE_MAX_OVERFLOW` | `integer` | `20` | Maximum overflow connections allowed above `pool_size`. |
| `NEOMON_DATABASE_POOL_TIMEOUT` | `float` | `30.0` | Seconds to wait before failing to acquire a database pool connection. |
| `NEOMON_DATABASE_POOL_RECYCLE` | `integer` | `1800` | Seconds before recycling connections to avoid stale socket drops. |
| `NEOMON_REDIS_URL` | `string` | `None` | Optional Redis URL (`redis://...`) for distributed caching and rate-limiting. |
| `NEOMON_WORKER_ENABLED` | `boolean` | `true` | Whether background job orchestration worker threads run within the process. |
| `NEOMON_WORKER_CONCURRENCY` | `integer` | `4` | Maximum concurrent background research tasks executed by worker. |
| `NEOMON_RATE_LIMIT_ENABLED` | `boolean` | `true` | Enables token-bucket IP/session rate-limiting middleware. |
| `NEOMON_RATE_LIMIT_AUTH_RPM` | `integer` | `10` | Rate limit for `/api/v1/auth` endpoints (brute-force defense). |
| `NEOMON_RATE_LIMIT_RESEARCH_RPM` | `integer` | `30` | Rate limit for investigation creation and research retrieval. |
| `NEOMON_RATE_LIMIT_EXPORT_RPM` | `integer` | `20` | Rate limit for PDF and data export generation. |
| `NEOMON_RATE_LIMIT_DEFAULT_RPM` | `integer` | `120` | Default rate limit across all standard REST routes. |
| `NEOMON_LOG_LEVEL` | `string` | `"INFO"` | Logging verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`. |
| `NEOMON_LOG_FORMAT` | `string` | `"auto"` | Format: `"auto"`, `"json"` (for production aggregators), or `"human"`. |
| `NEOMON_TAVILY_API_KEY` | `string` | `None` | Optional Tavily API key for web search. Also accepts `TAVILY_API_KEY`. |
| `NEOMON_TAVILY_ENABLED` | `boolean` | `true` | Master toggle for Tavily Web Retrieval. |
| `NEOMON_TAVILY_SEARCH_DEPTH` | `string` | `"advanced"` | Tavily search depth: `"basic"` (fast) or `"advanced"` (deep context). |
| `NEOMON_TAVILY_MAX_RESULTS` | `integer` | `10` | Maximum results fetched per Tavily query vector (1-20). |
| `NEOMON_UNPAYWALL_EMAIL` | `string` | `None` | Contact email for Unpaywall Open Access API compliance. |
| `NEOMON_UNPAYWALL_API_KEY` | `string` | `None` | Optional commercial API key for Unpaywall infrastructure. |
| `NEOMON_RESEARCH_USER_AGENT` | `string` | `"NEOMON/0.3 (+https://github.com/neomon-dev/NEOMON)"` | Polite HTTP User-Agent header sent to academic registries. |
| `NEOMON_RESEARCH_MAX_DOCUMENT_BYTES` | `integer` | `5000000` | Max document size (5 MB default) downloaded by crawler to prevent DoS. |

### Frontend Settings Reference (`.env.local`)

| Variable Name | Default Value | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Public backend URL accessible from the client browser. |

---

## 10. Database Management & Migration Strategy

NEOMON uses an enterprise-grade migration architecture managed through **Alembic** and **SQLAlchemy 2.0 Asyncio**.

### Database Engine Dual-Compatibility

* **Local Development & Offline Air-Gapped Mode**: SQLite 3 with Write-Ahead Logging (`WAL`), multi-process busy handlers, and immediate transaction pragmas. The baseline database is committed at `backend/neomon.db` with historical test records.
* **Production Deployment**: PostgreSQL 15+ on **Render PostgreSQL** using the high-performance `asyncpg` driver, connection pooling, and strict UTF-8 text sanitization (NUL-character stripping).

### Common Alembic Commands

Run all commands from the `backend/` directory:

```powershell
Set-Location backend

# Apply all migrations to the latest revision
python -m alembic upgrade head

# Inspect the current database schema revision
python -m alembic current

# View complete migration history
python -m alembic history --verbose

# Roll back by one migration revision (use with caution in staging)
python -m alembic downgrade -1
```

### Key Migration Milestones

* `20261112_0001` to `20261112_0008`: Core research entities, investigations, claims, sources, and documents.
* `20261113_0009` to `20261113_0012`: Multi-agent debate rounds, evidence calibration, credibility assessments, and methodology audits.
* `20261114_0013` to `20261114_0015`: Study independence clusters, citation lineages, collaborative workspaces, and RBAC tables.
* `20261115_0016`: Dialect-aware cleanups and production indexing.
* `20261115_0017`: Widen `evidence_type` and `extraction_method` column lengths for Render PostgreSQL compatibility.

---

## 11. Production Deployment Architecture

NEOMON is deployed on a dedicated cloud architecture:
* **Frontend**: Vercel (Next.js 16 App Router)
* **Backend API**: Render Web Service (FastAPI Python 3.12+)
* **Production Database**: Render PostgreSQL (Managed PostgreSQL 15+)

```
+-----------------------------------------------------------------------------------------+
|                                PRODUCTION DEPLOYMENT                                    |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +------------------------------------+          +---------------------------------+   |
|   |          VERCEL PLATFORM           |          |        RENDER WEB SERVICE       |   |
|   |  - Next.js 16 (App Router)         |          |  - FastAPI (Python 3.12+)       |   |
|   |  - Edge CDN & Asset Optimization   |          |  - Background Worker Threads    |   |
|   |  - Server-Side Rendering (SSR)     |          |  - Port Binding: 0.0.0.0:$PORT  |   |
|   |  - URL: neomon-beryl.vercel.app    |          |  - URL: neomon-api.onrender.com |   |
|   +-----------------+------------------+          +----------------+----------------+   |
|                     |                                              |                    |
|                     | HTTPS REST / Typed SSE Streams               |                    |
|                     +----------------------------------------------+                    |
|                                                                    |                    |
|                                                   +----------------v----------------+   |
|                                                   |     RENDER POSTGRESQL 15+       |   |
|                                                   |  - Managed PostgreSQL Service   |   |
|                                                   |  - asyncpg Connection Pool      |   |
|                                                   |  - Automated Backups            |   |
|                                                   +---------------------------------+   |
+-----------------------------------------------------------------------------------------+
```

### Backend (Render Web Service)

* **Build Command**:
  ```bash
  pip install -r backend/requirements.txt && cd backend && alembic upgrade head
  ```
* **Start Command**:
  ```bash
  cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
* **Environment Variables**:
  ```env
  NEOMON_ENVIRONMENT=production
  NEOMON_DEMO_MODE=false
  NEOMON_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/neomon
  NEOMON_ALLOWED_ORIGINS=https://neomon-beryl.vercel.app
  ```

### Frontend (Vercel)

* **Framework Preset**: Next.js
* **Build Command**: `npm run build`
* **Output Directory**: `.next`
* **Environment Variables**:
  ```env
  NEXT_PUBLIC_API_URL=https://neomon-api.onrender.com/api/v1
  ```

---

## 12. Security, Privacy & Compliance Architecture

Security is designed into NEOMON's architectural foundation:

### 1. In-Memory AI Key Isolation
API keys for external AI providers (such as OpenAI, Anthropic, or Groq) are stored **strictly in React client memory** for the duration of the browser session. Keys are:
* **Never** written to browser `localStorage` or `sessionStorage`.
* **Never** appended to URLs or logged in telemetry.
* **Never** stored in the backend database or backend filesystem.
* Passed ephemeral per-request in the `X-Provider-Key` header or sanitized payload body.

### 2. NIST-Compliant Authentication & Cryptography
* User passwords are encrypted using salted **PBKDF2-HMAC-SHA256 with 600,000 iterations**.
* Session authentication tokens are 256-bit cryptographically secure strings generated via Python's `secrets` module.
* Stored tokens are hashed using SHA-256 before database insertion; plain tokens are never saved.
* Constant-time comparison (`secrets.compare_digest`) protects against timing attacks.

### 3. Server-Side Request Forgery (SSRF) Defense
All outbound document downloads and user-configured model endpoints pass through a strict SSRF validation layer:
* DNS names are resolved to IPv4/IPv6 addresses immediately prior to socket connection.
* Private network ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` AWS metadata, carrier-grade NAT) are rejected with HTTP 400.
* Loopback addresses (`127.0.0.1`, `localhost`, `::1`) are permitted **exclusively** for verified local AI runners (`LM Studio`, `Ollama`) via strict whitelist filtering.

### 4. Tenant Isolation & Granular RBAC
All investigations, sources, evidence, workflows, and debate records are bound to specific `workspace_id` foreign keys. Cross-tenant access is validated at the database query layer, enforcing permissions across three distinct roles:
* **Admin**: Workspace management, member invitations, API configuration, deletion rights.
* **Member**: Create and execute investigations, debate rounds, gap analyses, and exports.
* **Viewer**: Read-only access to completed research dossiers, reports, and knowledge graphs.

---

## 13. Troubleshooting Guide & Diagnostics

### Common Issues & Immediate Resolutions

#### 1. "Failed to connect to AI provider / Connection Refused"
* **Symptom**: Red badge in Settings or investigation view stating provider unreachable.
* **Cause**: Local server is not running, listening on wrong port, or blocking CORS.
* **Resolution**:
  * For **LM Studio**: Open the Local Server tab, confirm the green "Running" light is active, port is `1234`, and CORS is enabled.
  * For **Ollama**: Ensure Ollama was started with `OLLAMA_ORIGINS="*"`:
    ```powershell
    $env:OLLAMA_ORIGINS = "*"
    ollama serve
    ```

#### 2. "CORS Error: No 'Access-Control-Allow-Origin' header present"
* **Symptom**: Browser console logs CORS error when frontend requests backend endpoints.
* **Cause**: Frontend origin not included in backend `NEOMON_ALLOWED_ORIGINS`.
* **Resolution**: Add your frontend URL (e.g., `http://localhost:3000` or `https://your-domain.vercel.app`) to `NEOMON_ALLOWED_ORIGINS` in your backend `.env` file.

#### 3. "database is locked" (SQLite)
* **Symptom**: SQLite database error during high-concurrency test runs or parallel investigations.
* **Cause**: Database file accessed in standard rollback journal mode without WAL pragmas.
* **Resolution**: Ensure SQLite WAL mode is enabled:
  ```powershell
  python -c "import sqlite3; con = sqlite3.connect('backend/neomon.db'); con.execute('PRAGMA journal_mode=WAL;'); print(con.execute('PRAGMA journal_mode;').fetchone())"
  ```

#### 4. "Target database is not up to date" (Alembic)
* **Symptom**: Backend startup warning or crash indicating missing schema tables.
* **Cause**: Pending database migrations have not been applied.
* **Resolution**: Run `python -m alembic upgrade head` inside the `backend/` directory.

---

## 14. Feature Documentation Index

For exhaustive, section-by-section architectural documentation of every platform capability, consult the [Feature Documentation Index](docs/features/README.md):

* **Observatory & Investigations**: [Dashboard](docs/features/dashboard.md) | [Investigation Lifecycle](docs/features/investigations.md) | [Research Orchestration](docs/features/research-orchestration.md)
* **Intelligence Engines**: [Multi-Agent Analysis](docs/features/multi-agent-analysis.md) | [Advocate-Skeptic Debate](docs/features/advocate-skeptic.md) | [Methodology Audit](docs/features/methodology-audit.md)
* **Evidence & Literature**: [Source Discovery](docs/features/source-discovery.md) | [Evidence Workspace](docs/features/evidence-workspace.md) | [Quality Calibration](docs/features/evidence-quality.md)
* **Advanced Synthesis**: [Contradiction Intelligence](docs/features/contradiction-intelligence.md) | [Citation Genealogy](docs/features/citation-genealogy.md) | [Knowledge Graph](docs/features/knowledge-graph.md) | [Research Synthesis](docs/features/research-synthesis.md)
* **Longitudinal Discovery**: [Research Trends](docs/features/research-trends.md) | [Research Gaps](docs/features/research-gaps.md) | [Hypothesis Generation](docs/features/hypothesis-generation.md) | [Autonomous Workflows](docs/features/autonomous-workflows.md)
* **Platform & Infrastructure**: [Workspaces & RBAC](docs/features/workspace-collaboration.md) | [Authentication](docs/features/authentication-and-roles.md) | [Notifications](docs/features/notifications.md) | [Scientific Benchmarks](docs/features/benchmarks.md) | [Settings & Telemetry](docs/features/settings-and-configuration.md)
* **Technical Specifications**: [Complete REST API Reference](docs/features/api-reference.md) | [Database & Data Model (68 Tables)](docs/features/database-and-data-model.md)

---

## 15. License & Contribution Terms

NEOMON is released under the **Apache License 2.0**.

```
Copyright 2026 NEOMON Development Team.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### Contribution Standards

1. **Zero Unverified Assertions**: All contributions modifying research synthesis, debate adjudication, or source indexing must include corresponding automated unit tests.
2. **Strict Provenance Guarantee**: Features touching evidence handling must maintain character-level provenance without exception.
3. **SSRF Guard Invariance**: Under no circumstances should SSRF protections or URL validation routines be relaxed for non-whitelisted addresses.
4. **Clean Regression Pass**: Pull requests must pass 100% of backend tests (`pytest backend/tests`), frontend tests (`npm test`), ESLint (`npm run lint`), and TypeScript verification (`npx tsc --noEmit`).

---

*NEOMON — Neural Evidence Orchestration & Multi-Agent Observation Network*
*Engineered for scientific integrity, reproducibility, and transparent dialectical intelligence.*
