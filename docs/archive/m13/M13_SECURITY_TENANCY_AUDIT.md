# M13 Phase 0.1 Security and Tenancy Audit

## Authorization architecture

Protected routes use `get_current_user`, which rejects missing, invalid,
expired, revoked, and inactive sessions with HTTP 401. Resource access is
delegated to `PermissionService`, which resolves active workspace membership
and applies the viewer/reviewer/researcher/admin/owner hierarchy.

Investigation access resolves an explicit workspace. Legacy records with a
null `workspace_id` resolve to the global workspace **only for users who are
explicit members of that workspace**. There is no unauthenticated or
administrator fallback.

## Route-to-authorization matrix

| Surface | Authentication | Tenancy/role check | Result |
|---|---|---|---|
| Auth/session | `get_current_user` | Session hash, expiry, revocation, user status | PASS |
| Workspace/member/invitation APIs | `get_current_user` | Workspace membership and owner/admin capability | PASS in existing audit |
| Investigation CRUD/access | `get_current_user` | `check_investigation_access` | PASS |
| Sources/evidence/claims | `get_current_user` | Investigation or workspace scope | PASS |
| Analysis/reports/exports | `get_current_user` | Investigation read/write capability | PASS |
| SSE events | `get_current_user` | Investigation access before stream | PASS |
| Jobs/workflows/observatory | `get_current_user` | Investigation/workspace scope | PASS after fallback fix |
| Comments/annotations/reviews | `get_current_user` | Workspace plus role/self-approval checks | PASS in existing audit |
| Graph/quality/global listings | `get_current_user` | Explicit membership; no-membership empty result | PASS after regression fix |

## Defect found and fixed

Several unfiltered list routes substituted the global workspace when a user
had no memberships. That could expose unassigned legacy investigations and
related derived data through graph, quality, evidence, source, observatory, or
autonomous-workflow listings. The routes now return an empty scoped result when
no memberships exist. Direct investigation access continues to require
explicit global membership.

## Adversarial validation

- `test_security_audit.py`: 10 passed, including missing/invalid/expired/
  revoked sessions, horizontal isolation, role restrictions, invitations,
  SSE, and the new legacy-global regression.
- Targeted security/workspace/SSE selection: 18 passed.
- Existing role tests cover viewer, reviewer, researcher, admin, and owner
  server-side restrictions.
- Full clean-database backend run: 202 passed and 21 failed from SQLite
  locking in unrelated integration tests; full release certification is
  blocked.

## Limitations

Browser automation, PostgreSQL/Redis, Docker, and production multi-process
SSE verification were not available. The malformed development SQLite file
also prevents claiming safe migration of the existing database. Recovery and
re-validation are required before Phase 0.1 can pass its exit gate.
