# NEOMON — MANDATORY DEVELOPMENT AND LOCALHOST QA POLICY

This policy applies to EVERY milestone starting from Milestone 10 onward, including all sub-milestones and future feature implementations.

## NON-NEGOTIABLE REQUIREMENT

Completing code implementation does NOT mean a milestone is complete.

Every milestone must undergo actual localhost functional testing before it can be declared complete.

---

### 1. Implementation
- Inspect existing architecture before modifying code.
- Implement the requested milestone.
- Preserve existing functionality and backward compatibility.
- Avoid unnecessary rewrites and duplicated services.

### 2. Automated verification
Run all relevant:
- Backend tests (`pytest backend/tests/ -v`).
- Frontend tests (`npm test`).
- ESLint (`npm run lint`).
- TypeScript checks (`npx tsc --noEmit`).
- Python compilation (`python -m py_compile`).
- Alembic migration checks (`alembic current`, `alembic check`).
- Production builds (`npm run build`).

### 3. Mandatory localhost startup
Start the actual FastAPI backend (`uvicorn app.main:app --app-dir backend --port 8000`) and Next.js frontend (`npm run dev` or `npm start`).

Verify:
- Backend availability (`http://127.0.0.1:8000/api/v1/health`).
- Frontend availability (`http://localhost:3000`).
- Database connectivity (`neomon.db` / SQLite / PostgreSQL).
- API connectivity.
- Background workers and job processing.
- SSE and event streaming where applicable (`/events/stream`).
- Provider connections where applicable.

Do not substitute mocked application startup for real localhost execution.

### 4. Mandatory real-browser functional testing
Use browser automation or an equivalent real-browser testing approach.

For EVERY new or modified feature:
- Open its actual localhost page.
- Test every relevant button and interactive control.
- Submit forms using valid and invalid data.
- Test loading, empty, success and error states.
- Verify filters, search, sorting and pagination.
- Verify navigation and cross-links.
- Verify displayed data matches backend responses.
- Verify actions actually execute rather than merely displaying success messages.
- Inspect browser console errors and failed network requests.

For major existing workflows affected by the milestone, repeat the relevant end-to-end tests.

### 5. API, database and integration verification
- Exercise real API operations.
- Verify database persistence.
- Verify relationships and foreign keys.
- Verify data survives application restarts.
- Test error handling and validation.
- Test relevant external provider integrations.
- Test queue, retry, timeout and cancellation behavior where applicable.

### 6. Regression verification
Test all existing functionality that could be affected by the changes.

Never assume that an earlier milestone's successful tests guarantee current functionality.

Preserve existing investigations and user data.

### 7. Bug fixing
Every reproducible bug must be entered into a bug register.

Include:
- Bug ID.
- Affected module.
- Reproduction steps.
- Expected behavior.
- Actual behavior.
- Root cause.
- Severity.
- Fix applied.
- Retest result.

Fix root causes and rerun relevant tests.

Do not hide failures, introduce fake success states, or silently substitute mock data.

### 8. Final restart verification
After fixes:
- Stop and restart backend and frontend.
- Verify database migrations.
- Reopen the application.
- Recheck critical workflows.
- Confirm persisted data is intact.

### 9. Required milestone report

Create or update the milestone report with:
1. Features implemented.
2. Files changed.
3. Frontend pages tested.
4. Interactive controls tested.
5. API endpoint families tested.
6. Database operations verified.
7. Integration tests performed.
8. Browser console errors.
9. Network failures.
10. Automated test results.
11. Bugs discovered and fixed.
12. Bugs still unresolved.
13. Features not tested and why.
14. Regression results.
15. Application restart results.
16. Final localhost startup status.

Use only these statuses:
- **PASS** — Actually executed and verified.
- **FAIL** — Reproducible failure.
- **PARTIAL** — Works with limitations.
- **NOT TESTED** — Not verified, with reason.

### 10. Milestone completion gate

A milestone can be declared COMPLETE only when:
- Its requested implementation is finished.
- Automated checks pass or exceptions are explicitly documented.
- The application runs on localhost.
- Every new or modified feature has been tested in a real browser.
- Relevant APIs and database operations have been verified.
- Relevant existing functionality passes regression testing.
- Critical and high-severity bugs are fixed or explicitly documented.
- The final report is produced.

If a feature cannot be tested because a provider, credential, hardware resource or external service is unavailable, mark it **NOT TESTED**. Never claim it passed.

Do not proceed to the next milestone until this verification phase is complete.

### 11. Git policy

**Never commit or push to GitHub unless explicitly instructed by the user.**
