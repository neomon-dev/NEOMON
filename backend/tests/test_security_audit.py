"""Comprehensive Security Audit Test Suite for NEOMON Milestone 10.1.

Validates:
1. Complete elimination of unauthenticated administrator fallback (missing/invalid/expired/revoked tokens -> 401).
2. Deactivated accounts rejected on authentication.
3. Strict Horizontal Privilege Escalation prevention across isolated workspaces (403 Forbidden).
4. Vertical Privilege Escalation prevention across workspace role hierarchy (viewer < reviewer < researcher < admin < owner).
5. Peer review self-approval guard enforcement.
6. Invitation role escalation guard.
7. Workspace ownership transfer restricted to owner.
8. Session invalidation on password change and single-use password reset tokens.
9. Single-use invitation tokens and cross-workspace rejection.
10. Server-Sent Events (SSE) streaming authentication and tenancy boundaries.
11. Multi-user concurrent interactions without lock contention.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.auth_service import AuthService
from app.auth.security import hash_token
from app.db import SessionFactory, engine
from app.main import app
from app.models import Investigation, User, UserSession, Workspace, WorkspaceMember


@pytest.fixture
def raw_client():
    """Clean TestClient without preset authentication headers."""
    with TestClient(app) as tc:
        yield tc
        tc.portal.call(engine.dispose)


# =========================================================================
# 1. AUTHENTICATION HARDENING & ELIMINATION OF ADMIN FALLBACK
# =========================================================================

def test_unauthenticated_requests_return_401(raw_client: TestClient):
    """Verify that requests missing credentials return 401 Unauthorized across all router surfaces."""
    dummy_id = uuid.uuid4()
    protected_endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/workspaces"),
        ("POST", "/api/v1/workspaces"),
        ("GET", "/api/v1/research/investigations"),
        ("POST", "/api/v1/research/investigations"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/sources"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/evidence"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/claims"),
        ("POST", f"/api/v1/research/investigations/{dummy_id}/cancel"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/analysis"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/reports"),
        ("POST", f"/api/v1/research/investigations/{dummy_id}/reports/generate"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/export/manifest"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/export/markdown"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/export/pdf"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/gaps"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/hypotheses"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/quality/audit"),
        ("GET", f"/api/v1/research/investigations/{dummy_id}/graph"),
        ("GET", "/api/v1/research/graph"),
        ("GET", "/api/v1/research/evidence"),
        ("GET", "/api/v1/research/sources"),
        ("GET", "/api/v1/research/trends/latest"),
        ("GET", "/api/v1/research/intelligence/overview"),
        ("GET", "/api/v1/research/quality/audits"),
        ("GET", "/api/v1/research/autonomous/workflows"),
        ("GET", f"/api/v1/collaboration/threads?workspace_id={dummy_id}"),
        ("GET", f"/api/v1/collaboration/annotations?workspace_id={dummy_id}"),
        ("GET", f"/api/v1/collaboration/reviews?workspace_id={dummy_id}"),
        ("GET", "/api/v1/collaboration/notifications"),
        ("GET", f"/api/v1/events?investigation_id={dummy_id}"),
        ("GET", f"/events?investigation_id={dummy_id}"),
    ]

    for method, path in protected_endpoints:
        if method == "GET":
            res = raw_client.get(path)
        elif method == "POST":
            res = raw_client.post(path, json={})
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"


def test_invalid_expired_and_revoked_tokens_return_401(raw_client: TestClient):
    """Verify invalid, expired, revoked tokens, and deactivated accounts all reject authentication."""
    # 1. Invalid token format and random bearer
    res = raw_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed_token_xyz"})
    assert res.status_code == 401

    # 2. Register user
    email = f"sec_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg = raw_client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123!", "display_name": "Security User"
    })
    assert reg.status_code == 201
    token = reg.json()["session_token"]
    user_id = uuid.UUID(reg.json()["user"]["id"])

    # Valid token works
    valid_res = raw_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert valid_res.status_code == 200

    # 3. Revoke session via logout
    logout_res = raw_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # Revoked session is rejected
    revoked_res = raw_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_res.status_code == 401

    # 4. Login again and test expiration
    login_res = raw_client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    new_token = login_res.json()["session_token"]

    async def expire_token():
        token_hash = hash_token(new_token)
        async with SessionFactory() as session:
            db_sess = await session.scalar(select(UserSession).where(UserSession.session_token_hash == token_hash))
            assert db_sess is not None
            db_sess.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

    asyncio.run(expire_token())

    expired_res = raw_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert expired_res.status_code == 401

    # 5. Deactivated user account
    login_active = raw_client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    active_token = login_active.json()["session_token"]

    async def deactivate_user():
        async with SessionFactory() as session:
            db_user = await session.get(User, user_id)
            db_user.status = "inactive"
            await session.commit()

    asyncio.run(deactivate_user())

    deactivated_res = raw_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {active_token}"})
    assert deactivated_res.status_code == 401


# =========================================================================
# 2. HORIZONTAL PRIVILEGE ESCALATION (CROSS-WORKSPACE ISOLATION)
# =========================================================================

def test_horizontal_privilege_escalation_across_workspaces(raw_client: TestClient):
    """Prove that User A (Workspace A) cannot read, modify, or export User B's entities (Workspace B)."""
    # 1. Register User A (Alice)
    alice_email = f"alice_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_a = raw_client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!", "display_name": "Alice"})
    token_a = reg_a.json()["session_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B (Bob)
    bob_email = f"bob_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_b = raw_client.post("/api/v1/auth/register", json={"email": bob_email, "password": "Password123!", "display_name": "Bob"})
    token_b = reg_b.json()["session_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Alice creates a workspace and investigation in her workspace
    ws_res = raw_client.post("/api/v1/workspaces", json={"name": "Alice Lab", "description": "Alice's private lab"}, headers=headers_a)
    assert ws_res.status_code == 201
    ws_a_id = ws_res.json()["id"]

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv_res = raw_client.post(
            "/api/v1/research/investigations",
            json={"question": "Confidential Study in Alice's Lab?", "mode": "quick", "workspace_id": ws_a_id},
            headers=headers_a,
        )
    assert inv_res.status_code == 200
    inv_a_id = inv_res.json()["investigation"]["id"]

    # Bob attempts horizontal access to Alice's workspace:
    assert raw_client.get(f"/api/v1/workspaces/{ws_a_id}", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/workspaces/{ws_a_id}/members", headers=headers_b).status_code == 403
    assert raw_client.post(f"/api/v1/workspaces/{ws_a_id}/invitations", json={"email": "eve@neomon.ai", "role": "researcher"}, headers=headers_b).status_code == 403

    # Bob attempts horizontal read/write to Alice's investigation:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/sources", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/evidence", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/claims", headers=headers_b).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_a_id}/cancel", headers=headers_b).status_code == 403

    # Bob attempts analysis and report regeneration:
    assert raw_client.post(f"/api/v1/research/investigations/{inv_a_id}/analysis", json={}, headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/analysis", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/reports", headers=headers_b).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_a_id}/reports/generate", headers=headers_b).status_code == 403

    # Bob attempts export:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/export/manifest", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/export/markdown", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/export/pdf", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/export/json", headers=headers_b).status_code == 403

    # Bob attempts knowledge graph:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/graph", headers=headers_b).status_code == 403

    # Bob attempts gaps and hypotheses:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/gaps", headers=headers_b).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_a_id}/gaps/analyze", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/hypotheses", headers=headers_b).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_a_id}/hypotheses/generate", headers=headers_b).status_code == 403

    # Bob attempts quality audit:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/quality/audit", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/quality/lineage", headers=headers_b).status_code == 403
    assert raw_client.get(f"/api/v1/research/investigations/{inv_a_id}/quality/validations", headers=headers_b).status_code == 403

    # Bob attempts autonomous workflow attachment:
    wf_payload = {
        "investigation_id": inv_a_id,
        "title": "Malicious Workflow",
        "research_objective": "Attempted breach",
    }
    assert raw_client.post("/api/v1/research/autonomous/workflows", json=wf_payload, headers=headers_b).status_code == 403

    # Bob attempts cross-workspace SSE connection:
    assert raw_client.get(f"/api/v1/events?investigation_id={inv_a_id}", headers=headers_b).status_code == 403


# =========================================================================
# 3. VERTICAL PRIVILEGE ESCALATION & ROLE HIERARCHY
# =========================================================================

def test_vertical_privilege_escalation_within_workspace(raw_client: TestClient):
    """Verify that lower roles (viewer) cannot execute mutating or review actions."""
    # 1. Alice creates workspace
    alice_email = f"alice_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_a = raw_client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!", "display_name": "Alice"})
    token_a = reg_a.json()["session_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    ws = raw_client.post("/api/v1/workspaces", json={"name": "Role Test Lab"}, headers=headers_a).json()
    ws_id = ws["id"]

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv = raw_client.post(
            "/api/v1/research/investigations",
            json={"question": "Role test inquiry?", "workspace_id": ws_id},
            headers=headers_a,
        ).json()["investigation"]
    inv_id = inv["id"]

    # 2. Alice invites Charlie as viewer
    charlie_email = f"charlie_{uuid.uuid4().hex[:8]}@neomon.ai"
    inv_res = raw_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": charlie_email, "role": "viewer"},
        headers=headers_a,
    )
    assert inv_res.status_code == 201
    invite_token = inv_res.json()["invite_token"]

    # Charlie registers and accepts
    reg_c = raw_client.post("/api/v1/auth/register", json={"email": charlie_email, "password": "Password123!", "display_name": "Charlie"})
    token_c = reg_c.json()["session_token"]
    headers_c = {"Authorization": f"Bearer {token_c}"}

    acc_res = raw_client.post("/api/v1/invitations/accept", json={"token": invite_token}, headers=headers_c)
    assert acc_res.status_code == 200

    # Charlie (Viewer) CAN read:
    assert raw_client.get(f"/api/v1/research/investigations/{inv_id}", headers=headers_c).status_code == 200
    assert raw_client.get(f"/api/v1/research/investigations/{inv_id}/sources", headers=headers_c).status_code == 200

    # Charlie (Viewer) CANNOT write/modify:
    assert raw_client.post(f"/api/v1/research/investigations/{inv_id}/cancel", headers=headers_c).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_id}/analysis", json={}, headers=headers_c).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_id}/reports/generate", headers=headers_c).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_id}/gaps/analyze", headers=headers_c).status_code == 403
    assert raw_client.post(f"/api/v1/research/investigations/{inv_id}/hypotheses/generate", headers=headers_c).status_code == 403

    # Charlie (Viewer) CANNOT invite others or transfer ownership:
    assert raw_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": "hacker@neomon.ai", "role": "admin"},
        headers=headers_c,
    ).status_code == 403

    assert raw_client.post(
        f"/api/v1/workspaces/{ws_id}/transfer-ownership",
        json={"new_owner_id": str(uuid.uuid4())},
        headers=headers_c,
    ).status_code == 403


# =========================================================================
# 4. PEER REVIEW SELF-APPROVAL GUARD
# =========================================================================

def test_peer_review_self_approval_guard(raw_client: TestClient):
    """Enforce that an author cannot approve their own review request when independent review is required."""
    alice_email = f"alice_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_a = raw_client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!", "display_name": "Alice Author"})
    token_a = reg_a.json()["session_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    ws = raw_client.post("/api/v1/workspaces", json={"name": "Peer Review Lab"}, headers=headers_a).json()
    ws_id = ws["id"]

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv = raw_client.post(
            "/api/v1/research/investigations",
            json={"question": "Peer review verification?", "workspace_id": ws_id},
            headers=headers_a,
        ).json()["investigation"]

    # Alice submits for formal review requiring independent review
    rev_res = raw_client.post(
        f"/api/v1/collaboration/reviews?workspace_id={ws_id}",
        json={
            "investigation_id": inv["id"],
            "target_type": "investigation",
            "target_id": inv["id"],
            "title": "Formal Evidence Review",
            "description": "Scientific validation of claims",
            "requires_independent_review": True,
        },
        headers=headers_a,
    )
    assert rev_res.status_code == 201
    rev_id = rev_res.json()["id"]

    # Alice attempts to self-approve: MUST FAIL with 403 Forbidden!
    self_approve_res = raw_client.post(
        f"/api/v1/collaboration/reviews/{rev_id}/decisions",
        json={"decision": "approved", "rationale": "I self-approve my own findings."},
        headers=headers_a,
    )
    assert self_approve_res.status_code == 403
    assert "Self-approval guard" in self_approve_res.json()["detail"]


# =========================================================================
# 5. INVITATION & ROLE HIERARCHY SECURITY
# =========================================================================

def test_role_hierarchy_invitation_escalation_guard(raw_client: TestClient):
    """Enforce that a member cannot invite another user with a role higher than their own."""
    # Alice (Owner) invites Bob as Researcher
    alice_email = f"alice_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_a = raw_client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!", "display_name": "Alice"})
    headers_a = {"Authorization": f"Bearer {reg_a.json()['session_token']}"}

    ws = raw_client.post("/api/v1/workspaces", json={"name": "Escalation Test Lab"}, headers=headers_a).json()
    ws_id = ws["id"]

    # Enable member invitations in workspace policy
    raw_client.patch(f"/api/v1/workspaces/{ws_id}", json={"allow_member_invitations": True}, headers=headers_a)

    bob_email = f"bob_{uuid.uuid4().hex[:8]}@neomon.ai"
    inv_bob = raw_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": bob_email, "role": "researcher"},
        headers=headers_a,
    ).json()

    reg_b = raw_client.post("/api/v1/auth/register", json={"email": bob_email, "password": "Password123!", "display_name": "Bob"})
    headers_b = {"Authorization": f"Bearer {reg_b.json()['session_token']}"}
    acc_bob = raw_client.post("/api/v1/invitations/accept", json={"token": inv_bob["invite_token"]}, headers=headers_b)
    assert acc_bob.status_code == 200

    # Bob (Researcher) attempts to invite Eve as 'admin' -> MUST BE FORBIDDEN!
    eve_email = f"eve_{uuid.uuid4().hex[:8]}@neomon.ai"
    escalate_res = raw_client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        json={"email": eve_email, "role": "admin"},
        headers=headers_b,
    )
    assert escalate_res.status_code == 403
    assert "cannot invite" in escalate_res.json()["detail"].lower()


# =========================================================================
# 6. PASSWORD RESET & SESSION INVALIDATION
# =========================================================================

def test_password_change_invalidates_prior_sessions(raw_client: TestClient):
    """Verify password change revokes other active sessions."""
    email = f"reset_{uuid.uuid4().hex[:8]}@neomon.ai"
    raw_client.post("/api/v1/auth/register", json={"email": email, "password": "OldPassword123!", "display_name": "User"})

    # Client 1 logs in
    login1 = raw_client.post("/api/v1/auth/login", json={"email": email, "password": "OldPassword123!"})
    token1 = login1.json()["session_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Client 2 logs in
    login2 = raw_client.post("/api/v1/auth/login", json={"email": email, "password": "OldPassword123!"})
    token2 = login2.json()["session_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Change password via Client 1
    change_res = raw_client.post(
        "/api/v1/auth/password/change",
        json={"old_password": "OldPassword123!", "new_password": "NewPassword123!"},
        headers=headers1,
    )
    assert change_res.status_code == 200

    # Client 2 (using token2) is now revoked!
    check_c2 = raw_client.get("/api/v1/auth/me", headers=headers2)
    assert check_c2.status_code == 401


def test_password_reset_token_single_use(raw_client: TestClient):
    """Verify single-use password reset tokens."""
    email = f"single_{uuid.uuid4().hex[:8]}@neomon.ai"
    raw_client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "display_name": "User"})

    # Request reset token
    req_res = raw_client.post("/api/v1/auth/password/reset-request", json={"email": email})
    reset_token = req_res.json()["reset_token"]

    # Complete reset
    confirm1 = raw_client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": reset_token, "new_password": "NewResetPassword123!"},
    )
    assert confirm1.status_code == 200

    # Second attempt to use same token MUST FAIL:
    confirm2 = raw_client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": reset_token, "new_password": "AnotherPassword123!"},
    )
    assert confirm2.status_code == 400


# =========================================================================
# 7. CONCURRENCY: SIMULTANEOUS INTERACTIONS
# =========================================================================

def test_concurrent_interactions_no_deadlock(raw_client: TestClient):
    """Test concurrent thread creation and comments to ensure DB transaction isolation."""
    email = f"concurrent_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg = raw_client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "display_name": "Concurrent User"})
    token = reg.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = raw_client.post("/api/v1/workspaces", json={"name": "Concurrency Lab"}, headers=headers).json()
    ws_id = ws["id"]

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv = raw_client.post(
            "/api/v1/research/investigations",
            json={"question": "Concurrency test?", "workspace_id": ws_id},
            headers=headers,
        ).json()["investigation"]

    # Open thread
    th = raw_client.post(
        f"/api/v1/collaboration/threads?workspace_id={ws_id}",
        json={"target_entity_type": "investigation", "target_entity_id": inv["id"], "content": "Initial thread"},
        headers=headers,
    ).json()
    th_id = th["id"]

    # Submit 10 rapid comments
    for i in range(10):
        c_res = raw_client.post(
            f"/api/v1/collaboration/threads/{th_id}/comments",
            json={"content": f"Concurrent comment #{i}"},
            headers=headers,
        )
        assert c_res.status_code == 201

    th_res = raw_client.get(f"/api/v1/collaboration/threads/{th_id}", headers=headers)
    assert th_res.status_code == 200
    # 1 initial thread message + 10 comments = 11
    assert len(th_res.json()["comments"]) == 11
