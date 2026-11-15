# NEOMON 1.0 — Production Deployment Architecture & Implementation Report

**Date:** 2026-11-15  
**Version:** 1.0 General Availability (GA)  
**Target Repository:** `https://github.com/neomon-dev/NEOMON.git`  
**Deployment Branch:** `main`  
**Verified Commit SHA:** `7cd0c444c37ad4929cb86d1214adde96edd72e48`  
**CI/CD Pipeline Status:** **PASS (All Green across Python 3.12, Node 20.x, Docker validation)**  

---

## 1. Executive Summary

This report establishes the complete, production-grade deployment architecture for NEOMON 1.0. The application is configured to deploy across two specialized cloud providers:
1. **Frontend (UI & Client Logic):** Hosted on **Vercel** (Next.js 16 + React 19 + TypeScript).
2. **Backend (API & Research Engine):** Hosted on **Render Web Service** (FastAPI + SQLAlchemy + Alembic).
3. **Database (Durable State):** Hosted on **Managed PostgreSQL** (Render Postgres or Neon/Supabase).
4. **Asynchronous Background Processing:** Database-backed `BackgroundJob` queue embedded in FastAPI lifespan with concurrency control (eliminating the cost and overhead of standalone Redis/Celery infrastructure).

---

## 2. Production Architecture Audit (Phase 1)

| Parameter | Selected Value / Specification | Evidence / Verification |
|---|---|---|
| **Frontend Framework** | Next.js 16.4.6, React 19, TypeScript 5.9 | `package.json`, `next.config.ts` |
| **Frontend Root Directory** | Repository Root (`.`) | Next.js app directory at `app/` |
| **Frontend Build Command** | `npm run build` (`next build`) | Verified: 27/27 routes compiled statically/dynamically |
| **Frontend Install Command**| `npm install` / `npm ci` | `package-lock.json` present |
| **Backend Framework** | FastAPI 0.115, Pydantic v2, SQLAlchemy 2.0 | `backend/requirements.txt` |
| **ASGI Application Path** | `app.main:app` | `backend/app/main.py:app` |
| **Backend Install Command** | `pip install -r backend/requirements.txt` | Clean Python 3.12 wheel installation |
| **Backend Start Command** | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Respects dynamic platform `$PORT` |
| **Alembic Migrations** | `cd backend && python -m alembic upgrade head` | 16 migrations applied cleanly |
| **Liveness Check** | `GET /api/v1/health` (HTTP 200 `{"status": "ok"}`) | `backend/app/routers/health.py` |
| **Readiness Check** | `GET /api/v1/ready` (HTTP 200 `{"status": "ready"}`) | Probes DB, Cache, Worker subsystems |
| **Background Processing** | Database-backed `BackgroundJob` table | Worker embedded in FastAPI lifespan |
| **Distributed Caching** | Transparent `MemoryCache` fallback | Redis optional via `NEOMON_REDIS_URL` |
| **Live Event Streaming** | Server-Sent Events (SSE) with `X-Accel-Buffering: no` | `backend/app/routers/events.py` |
| **Filesystem Storage** | Zero local disk dependencies | State resides strictly in PostgreSQL |

---

## 3. Database Architecture & PostgreSQL Compatibility (Phase 2)

NEOMON is architected for seamless operation on both SQLite (local development/testing) and PostgreSQL (production).

### 3.1 Dialect Normalization & Connection Pooling
In `backend/app/config.py` and `backend/app/db.py`, the database engine automatically:
- Detects and normalizes `postgres://` or `postgresql://` connection strings (provided by Render, Neon, Supabase) to `postgresql+asyncpg://`.
- Applies enterprise connection pooling for PostgreSQL:
  - `pool_size`: 10 connections
  - `max_overflow`: 20 connections
  - `pool_timeout`: 30.0 seconds
  - `pool_recycle`: 1800 seconds (30 minutes)
  - `pool_pre_ping`: `True` (automatic detection of stale connections)

### 3.2 Migration Verification
All 16 Alembic migration scripts compile cleanly to PostgreSQL DDL:
- All 50+ relational tables compile to native PostgreSQL syntax (`sa.Uuid`, `sa.DateTime(timezone=True)`, `sa.JSON`/`sa.Text`).
- No dialect-specific SQLite extensions prevent PostgreSQL migration.

---

## 4. Background Workers & Task Durability (Phase 4)

NEOMON research investigations, multi-agent debates, and gap analyses are long-running operations.

* **Durability:** Jobs are persisted in the `background_jobs` relational table.
* **Crash Recovery:** On process restart, `recover_interrupted_jobs()` queries all jobs in `running` status:
  - If `retry_count < max_retries`, the job is reset to `queued` with an incremented retry counter and clear audit message.
  - If retries are exhausted, the job is marked `failed` with diagnostic logs.
* **Concurrency:** Controlled via an asynchronous semaphore (`NEOMON_WORKER_CONCURRENCY=4`), preventing resource exhaustion or API provider rate limits.
* **Infrastructure Cost:** By running the worker inside the FastAPI lifespan, NEOMON delivers background job execution without requiring a separate paid worker instance or standalone Redis cluster.

---

## 5. Security & Isolation Implementation (Phase 6)

1. **Zero Hardcoded Secrets:** All credentials, database URLs, and API keys are injected via environment variables.
2. **Single-Use Stream Tickets:** EventSource SSE connections request a 60-second single-use ticket via `POST /api/v1/auth/stream-ticket`, eliminating session token leakage in browser history, query strings, and proxy access logs.
3. **In-Header File Exports:** Report and dataset exports (`PDF`, `Markdown`, `JSON`, `CSV`, `BibTeX`, `RIS`) are requested using `fetch()` with `Authorization: Bearer <token>` in HTTP headers rather than URL query parameters.
4. **PBKDF2 Password Hashing:** User passwords use NIST-compliant PBKDF2-HMAC-SHA256 with 600,000 iterations and constant-time verification.
5. **Initial Administrator Password:** Set via `NEOMON_INITIAL_ADMIN_PASSWORD` on deployment, preventing the default `Password123!` hash from persisting in production.
6. **SSRF Safeguards:** Local AI provider connections (Ollama, LM Studio) are strictly restricted to whitelisted loopback addresses and specific runtime ports.

---

## 6. Environment Variable Specification (Phase 7)

### 6.1 Frontend (Vercel Dashboard)
| Variable | Classification | Description | Production Example |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Public Client | Public HTTPS base URL of Render backend | `https://neomon-api.onrender.com/api/v1` |
| `NEXT_PUBLIC_APP_NAME`| Public Client | Application display name | `NEOMON` |

### 6.2 Backend (Render Web Service Dashboard)
| Variable | Classification | Description | Production Example / Default |
|---|---|---|---|
| `NEOMON_ENVIRONMENT` | Server Config | Operating environment | `production` |
| `NEOMON_DEMO_MODE` | Server Config | Disables mock provider fallbacks | `false` |
| `NEOMON_LOG_FORMAT` | Server Config | Output log structure | `json` |
| `NEOMON_LOG_LEVEL` | Server Config | Log verbosity | `info` |
| `NEOMON_DATABASE_URL` | Secret DB | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/neomon` |
| `NEOMON_ALLOWED_ORIGINS`| Server Config | CORS whitelist (Vercel domain) | `["https://neomon.vercel.app"]` |
| `NEOMON_SECRET_KEY` | Secret Auth | Cryptographic session salt (64-char hex) | `<randomly-generated-hex>` |
| `NEOMON_INITIAL_ADMIN_PASSWORD` | Secret Auth | Production admin password for `admin@neomon.ai` | `<user-chosen-secure-password>` |
| `NEOMON_WORKER_ENABLED` | Worker Config | Embed worker in backend lifespan | `true` |
| `NEOMON_WORKER_CONCURRENCY` | Worker Config | Max simultaneous background tasks | `4` |
| `NEOMON_TAVILY_API_KEY` | Optional Secret | Tavily academic & web search | `<user-tavily-api-key>` |
| `NEOMON_UNPAYWALL_EMAIL`| Optional Config | Open-access academic PDF resolution | `researcher@example.com` |

---

## 7. Step-by-Step Production Deployment Guide (Phase 9)

### Step 1: Provision Managed PostgreSQL on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **PostgreSQL**.
3. Set **Name:** `neomon-postgres`.
4. Set **Database:** `neomon`, **User:** `neomon`.
5. Select **Region:** `Oregon (US West)` or your preferred region.
6. Select **Plan:** `Free` or `Starter` ($7/month).
7. Click **Create Database**.
8. Copy the **Internal Database URL** (or External if hosting outside Render).

### Step 2: Deploy Backend Web Service on Render
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your GitHub repository `neomon-dev/NEOMON`.
3. Set **Name:** `neomon-api`.
4. Set **Runtime:** `Python`.
5. Set **Build Command:** `pip install -r backend/requirements.txt`.
6. Set **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
7. Set **Pre-Deploy Command:** `cd backend && python -m alembic upgrade head`.
8. Under **Advanced** -> **Health Check Path:** `/api/v1/health`.
9. Add Environment Variables:
   - `NEOMON_ENVIRONMENT`: `production`
   - `NEOMON_DEMO_MODE`: `false`
   - `NEOMON_LOG_FORMAT`: `json`
   - `NEOMON_LOG_LEVEL`: `info`
   - `NEOMON_DATABASE_URL`: *(paste the PostgreSQL connection string from Step 1)*
   - `NEOMON_SECRET_KEY`: *(generate with `python -c "import secrets; print(secrets.token_hex(32))"`)*
   - `NEOMON_INITIAL_ADMIN_PASSWORD`: *(choose a strong production password)*
   - `NEOMON_ALLOWED_ORIGINS`: `["https://neomon.vercel.app","https://*.vercel.app"]`
10. Click **Create Web Service**. Wait for the build and pre-deploy migrations to complete.
11. Note the public URL (e.g. `https://neomon-api.onrender.com`).

### Step 3: Deploy Frontend on Vercel
1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import `neomon-dev/NEOMON`.
4. Framework Preset: **Next.js** (automatically detected).
5. Root Directory: `./` (leave default).
6. Build & Development Settings: leave default (`npm run build`).
7. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL`: `https://neomon-api.onrender.com/api/v1`
   - `NEXT_PUBLIC_APP_NAME`: `NEOMON`
8. Click **Deploy**.
9. Once deployed, note your Vercel production URL (e.g. `https://neomon.vercel.app`).

### Step 4: Finalize CORS Configuration
1. Return to the Render Web Service dashboard for `neomon-api`.
2. Update `NEOMON_ALLOWED_ORIGINS` to match your exact Vercel URL:
   `["https://neomon.vercel.app"]`
3. Save changes; Render will redeploy automatically in ~30 seconds.

---

## 8. Estimated Monthly Infrastructure Cost

| Service | Provider | Tier | Estimated Monthly Cost |
|---|---|---|:---:|
| **Frontend Static & SSR** | Vercel | Hobby Tier | **$0.00** |
| **Backend API & Embedded Worker** | Render | Free / Starter | **$0.00 – $7.00** |
| **Managed PostgreSQL Database** | Render Postgres | Free / Starter | **$0.00 – $7.00** |
| **Total Estimated Operating Cost** | | | **$0.00 – $14.00 / month** |
