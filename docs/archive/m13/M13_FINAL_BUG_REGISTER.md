# NEOMON M13 — FINAL BUG REGISTER

**Platform:** NEOMON 1.0  
**Tracking Period:** Milestone 13 Final Live Browser Acceptance Testing  
**Auditor:** Google Antigravity QA Suite  
**Date:** November 15, 2026  
**Status:** ALL DISCOVERED ISSUES REMEDIATED & VERIFIED

---

## 1. Defect Register & Resolution Log

| Bug ID | Severity | Component | Summary | Root Cause | Remediation | Verification Status |
|---|---|---|---|---|---|---|
| **BUG-M13-001** | High | Realtime / SSE | Native browser `EventSource` disconnected with HTTP 401 | Browser `EventSource` API cannot attach custom HTTP `Authorization` headers | Appended `&token=${encodeURIComponent(token)}` to SSE URL in `app/investigations/[id]/page.tsx`; backend accepts query token | **VERIFIED FIXED** (Status: `connected`) |
| **BUG-M13-002** | High | Knowledge Exports | Direct browser export link clicks returned HTTP 401 | Native `<a href="..." download>` navigation does not transmit Bearer header | Appended `?token=${encodeURIComponent(token)}` to export URLs in export panel; direct one-click downloads succeed | **VERIFIED FIXED** (All 8 formats downloadable) |
| **BUG-M13-003** | Medium | Investigation Detail | Starting analysis with 0 sources triggered unhandled error / generic CORS failure | Lack of client-side guard allowed clicking "Start Analysis" before sources loaded | Disabled "Start Analysis" button when `sources.length === 0 && !analysis` with informative tooltip | **VERIFIED FIXED** (Button properly disabled with tooltip) |
| **BUG-M13-004** | High | Quality Audit | `/quality-audit` client re-render loop froze browser thread | `useEffect` in `QualityAuditWorkspace` listed `[selectedId]` in dependencies, triggering re-fetch loop on unselected initial state | Refactored `loadAudits` to depend on `[initialInvestigationId]` and added `let active = true` cancellation flags | **VERIFIED FIXED** (Smooth load across all 4 tabs) |
| **BUG-M13-005** | Medium | Scientific Benchmarks | Querying benchmark runs returned HTTP 404 in console | Route `/api/v1/benchmarks/{id}/runs` was missing in `backend/app/routers/benchmarks.py` | Implemented `@router.get("/{benchmark_id_or_slug}/runs")` querying `BenchmarkRun` records ordered by date | **VERIFIED FIXED** (Returns 200 OK with run list) |
| **BUG-M13-006** | Low | New Investigation | Newly created investigations defaulted to global workspace 2 | New investigation payload did not include active workspace ID from `localStorage` | Attached `workspace_id: activeWsId || undefined` in `app/investigations/new/page.tsx` submit handler | **VERIFIED FIXED** (Investigations create inside active workspace) |
| **BUG-M13-007** | Medium | Error Handling / CORS | Backend 500 errors stripped CORS headers, causing "Cannot reach backend" toast | FastAPI exception handlers returned plain JSONResponse without `Access-Control-Allow-Origin` on unhandled errors | Added CORS header propagation to `unexpected_error_handler` in `backend/app/errors.py` | **VERIFIED FIXED** (CORS preserved on all error responses) |

---

## 2. Open Defect Summary

- **Critical Blocker Defects:** 0
- **High Severity Defects:** 0
- **Medium Severity Defects:** 0
- **Low Severity / Cosmetic Defects:** 0
- **Outstanding Technical Debt:** Zero regressions against baseline; all 223 backend tests and 15 frontend tests pass.

**Registry Status: CLOSED & CERTIFIED FOR 1.0 RELEASE.**
