# NEOMON Troubleshooting & Incident Response Guide

## 1. Quick Diagnostics Cheat Sheet

| Symptom | Diagnostic Command / Probe | Probable Cause | Remedy |
| :--- | :--- | :--- | :--- |
| **API returning 503** | `curl -i http://localhost:8000/ready` | Database pool exhausted or unreachable | Check database status, verify `NEOMON_DATABASE_URL`, review pool size. |
| **HTTP 429 Too Many Requests** | Check `Retry-After` header | Client exceeded sliding window rate limit | Back off client requests according to `Retry-After`. Tune `NEOMON_RATE_LIMIT_*`. |
| **HTTP 401 Unauthorized** | Inspect request `Authorization` header or cookie | Token missing, expired, or revoked | Re-authenticate via `/api/v1/auth/login`. Verify cookie `SameSite` & `Secure` settings. |
| **HTTP 403 Forbidden** | Inspect workspace ID and user role | Insufficient RBAC role in target workspace | Request workspace owner/admin to elevate role to `researcher` or `reviewer`. |
| **Jobs stuck in queued state** | `curl http://localhost:8000/api/v1/jobs/worker/status` | Worker disabled or concurrency saturated | Ensure `NEOMON_WORKER_ENABLED=true` or start dedicated worker container. |

---

## 2. Structured JSON Log Analysis

In production, all logs are structured JSON strings. Query them using `jq`:

### Filter Errors and Exceptions
```bash
docker compose logs -f backend | jq 'select(.level == "ERROR")'
```

### Trace Request by Correlation ID
```bash
docker compose logs backend | jq 'select(.request_id == "c97a82b3-d648-43e6-92c4-84d5901287e0")'
```

### Monitor Worker Execution
```bash
docker compose logs -f worker | jq 'select(.logger | startswith("neomon.jobs"))'
```

---

## 3. Database Connection Issues

### Connection Pool Starvation
- **Log message**: `QueuePool limit of size X overflow Y reached, connection timed out`
- **Root cause**: Long-running synchronous blocks holding DB connections or pool size too small.
- **Remedy**:
  1. Increase `NEOMON_DATABASE_POOL_SIZE` (e.g. from 10 to 25).
  2. Increase `NEOMON_DATABASE_MAX_OVERFLOW` (e.g. from 20 to 50).
  3. Ensure short session lifetimes and commit blocks.

---

## 4. Redis Failover & Fallback Behavior

NEOMON is built with zero-hard-dependency on Redis:
- If Redis becomes unavailable, `CacheService` automatically switches to in-process `MemoryCache`.
- Logs will emit: `WARNING: Redis connection error: ... Falling back to MemoryCache`.
- Rate limiting and caching continue functioning seamlessly on the local host.
- When Redis recovers, restarts or reconnects automatically restore distributed cache state.
