# NEOMON Environment Variables Reference

This document provides a comprehensive inventory of all configuration variables supported by NEOMON.

## 1. Application & Core Backend Settings

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEOMON_ENVIRONMENT` | `string` | `development` | Deployment environment (`development`, `staging`, `production`). |
| `NEOMON_API_VERSION` | `string` | `v1` | Base API routing version identifier. |
| `NEOMON_DEMO_MODE` | `boolean` | `true` | Allows synthetic simulations when external AI providers are offline. |
| `NEOMON_LOG_LEVEL` | `string` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`). |
| `NEOMON_LOG_FORMAT` | `string` | `console` | Format of log output: `json` (for log aggregators) or `console`. |
| `NEOMON_SECRET_KEY` | `string` | *(generated)* | Secret key used for cryptographic signing and session tokens. |
| `NEOMON_ALLOWED_ORIGINS` | `json list` | `["http://localhost:3000"]` | Whitelist of allowed origins for CORS policies. |
| `NEOMON_TRUSTED_PROXIES` | `list` | `["127.0.0.1"]` | IP CIDRs permitted to supply `X-Forwarded-For` headers. |

---

## 2. Database & Connection Pooling

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEOMON_DATABASE_URL` | `string` | `sqlite+aiosqlite:///backend/neomon.db` | Async SQLAlchemy URI. For PostgreSQL use `postgresql+asyncpg://...`. |
| `NEOMON_DATABASE_POOL_SIZE` | `integer` | `10` | Number of permanent database connections kept in pool. |
| `NEOMON_DATABASE_MAX_OVERFLOW` | `integer` | `20` | Max temporary connections allowed beyond pool size during surges. |
| `NEOMON_DATABASE_POOL_TIMEOUT` | `float` | `30.0` | Seconds to wait before failing to acquire a pool connection. |
| `NEOMON_DATABASE_POOL_RECYCLE` | `integer` | `1800` | Seconds before idle pooled connections are refreshed. |
| `NEOMON_DATABASE_POOL_PRE_PING` | `boolean` | `true` | Tests connection liveness before checking out from pool. |

---

## 3. Caching & Redis

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEOMON_REDIS_URL` | `string` | `None` | Redis connection URI (e.g. `redis://localhost:6379/0`). Gracefully falls back to thread-safe memory cache if unset. |

---

## 4. Background Job Worker

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEOMON_WORKER_ENABLED` | `boolean` | `true` | Whether the in-process worker task runs automatically in API lifespan. |
| `NEOMON_WORKER_CONCURRENCY` | `integer` | `4` | Maximum parallel background jobs processed concurrently. |
| `NEOMON_WORKER_POLL_INTERVAL` | `float` | `1.0` | Seconds to wait between polling for queued background tasks. |
| `NEOMON_WORKER_GRACEFUL_SHUTDOWN_TIMEOUT` | `float` | `15.0` | Max seconds to wait for active tasks on process shutdown. |

---

## 5. Rate Limiting

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEOMON_RATE_LIMIT_AUTH_RPM` | `integer` | `10` | Max requests per minute on login, registration, and password endpoints. |
| `NEOMON_RATE_LIMIT_RESEARCH_RPM` | `integer` | `30` | Max requests per minute on investigation creation and search execution. |
| `NEOMON_RATE_LIMIT_EXPORT_RPM` | `integer` | `20` | Max requests per minute on dossier exports (PDF, Markdown, JSON-LD). |
| `NEOMON_RATE_LIMIT_GENERAL_RPM` | `integer` | `120` | General rate limit per client IP across all other endpoints. |

---

## 6. Frontend Configuration

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_NAME` | `string` | `NEOMON` | Application branding name displayed in UI. |
| `NEXT_PUBLIC_API_URL` | `string` | `http://127.0.0.1:8000/api/v1` | URL where the frontend communicates with the backend API. |
| `DOCKER_BUILD` | `string` | `0` | When set to `1`, produces standalone bundle for Docker builds. |
