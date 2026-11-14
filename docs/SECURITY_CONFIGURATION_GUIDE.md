# NEOMON Security Configuration & Hardening Guide

## 1. Security Architecture & Principles

NEOMON adheres to the principle of least privilege and strict zero-trust tenant boundaries:
- **Zero Unauthenticated Fallback**: Every non-public API endpoint requires explicit cryptographic bearer authentication or valid session cookies. Missing or invalid credentials strictly return HTTP 401.
- **Tenant Isolation**: Data access is scoped strictly by workspace membership. Users cannot read, modify, or list resources in workspaces where they lack an active membership.
- **Role-Based Access Control (RBAC)**: Fine-grained hierarchical permissions (`owner` > `admin` > `researcher` > `reviewer` > `viewer`).
- **Cryptographic Auditability**: SHA-256 evidence hashing and immutable audit trails prevent tampering.

---

## 2. RBAC Permissions Matrix

| Capability / Action | Viewer | Reviewer | Researcher | Admin | Owner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| View Investigations & Graph | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Evidence & Sources | ✅ | ✅ | ✅ | ✅ | ✅ |
| Export Research Dossiers | ✅ | ✅ | ✅ | ✅ | ✅ |
| Post Discussion Comments | ❌ | ✅ | ✅ | ✅ | ✅ |
| Submit Review Decisions | ❌ | ✅ | ❌ | ✅ | ✅ |
| Create Investigations & Hypotheses | ❌ | ❌ | ✅ | ✅ | ✅ |
| Trigger Background Jobs | ❌ | ❌ | ✅ | ✅ | ✅ |
| Invite Workspace Members | ❌ | ❌ | ❌ | ✅ | ✅ |
| Remove Members / Change Roles | ❌ | ❌ | ❌ | ✅ | ✅ |
| Delete Workspace | ❌ | ❌ | ❌ | ❌ | ✅ |

> [!NOTE]
> Self-review guard: A researcher cannot approve their own review request, even if they hold admin or reviewer credentials on the workspace.

---

## 3. Sensitive Data Masking in Logs

To prevent accidental credential leaks into monitoring tools (Datadog, CloudWatch, ELK), the logging subsystem actively sanitizes strings:
- Passwords, bearer tokens, API keys, session tokens, and cryptographic secrets are redacted with `***REDACTED***`.
- HTTP Authorization headers are automatically scrubbed.

---

## 4. Production Security Checklist

- [ ] Change all default passwords (`POSTGRES_PASSWORD`, seeded admin password).
- [ ] Configure `NEOMON_SECRET_KEY` with a cryptographically secure random value (min 64 chars).
- [ ] Restrict `NEOMON_ALLOWED_ORIGINS` to exact trusted production domain names (never wildcard `*`).
- [ ] Ensure reverse proxy terminates TLS 1.3 with HSTS (`Strict-Transport-Security`).
- [ ] Set `NEOMON_TRUSTED_PROXIES` to your upstream proxy / CDN subnets.
- [ ] Verify rate limits on authentication (`NEOMON_RATE_LIMIT_AUTH_RPM=10`).
- [ ] Run automated vulnerability scanning on Docker images.
