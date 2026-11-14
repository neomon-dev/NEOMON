"""Comprehensive automated test suite for NEOMON Milestone 10: Auth & Workspaces."""

import uuid
import pytest
from fastapi.testclient import TestClient

from unittest.mock import patch
from app.db import engine, SessionFactory
from app.models import Source, Evidence
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
        test_client.portal.call(engine.dispose)


def test_auth_registration_and_login_lifecycle(client: TestClient):
    """Test 1: User registration, personal workspace generation, and login."""
    unique_email = f"lead_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_payload = {
        "email": unique_email,
        "password": "SecurePassword123!",
        "display_name": "Lead Scientist",
        "bio": "Principal researcher in AI evaluation",
    }
    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "session_token" in reg_data
    assert reg_data["user"]["email"] == unique_email
    assert reg_data["user"]["display_name"] == "Lead Scientist"
    token = reg_data["session_token"]

    # 2. Authenticated GET /api/v1/auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email

    # 3. Verify user's automatically created personal workspace
    ws_res = client.get("/api/v1/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) >= 1
    personal_ws = next((w for w in workspaces if "Lead Scientist's Workspace" in w["name"]), None)
    assert personal_ws is not None
    assert personal_ws["user_role"] == "owner"

    # 4. Login with same credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    assert "session_token" in login_res.json()

    # 5. Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200


def test_password_validation_and_reset(client: TestClient):
    """Test 2: Password strength enforcement and password reset flow."""
    # Weak password rejection
    bad_res = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@neomon.ai", "password": "short", "display_name": "Weak"},
    )
    assert bad_res.status_code in (400, 422)

    # Password without digits
    bad_res2 = client.post(
        "/api/v1/auth/register",
        json={"email": "nodigits@neomon.ai", "password": "weaklettersalone", "display_name": "No Digits"},
    )
    assert bad_res2.status_code == 400

    # Valid user creation
    reset_email = f"reset_{uuid.uuid4().hex[:8]}@neomon.ai"
    client.post(
        "/api/v1/auth/register",
        json={"email": reset_email, "password": "InitialPassword123!", "display_name": "Reset User"},
    )

    # Request reset
    req_res = client.post("/api/v1/auth/password/reset-request", json={"email": reset_email})
    assert req_res.status_code == 200
    reset_token = req_res.json()["reset_token"]
    assert reset_token is not None

    # Confirm reset
    conf_res = client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": reset_token, "new_password": "NewStrongPassword456!"},
    )
    assert conf_res.status_code == 200

    # Old password fails
    fail_login = client.post(
        "/api/v1/auth/login",
        json={"email": reset_email, "password": "InitialPassword123!"},
    )
    assert fail_login.status_code == 401

    # New password succeeds
    good_login = client.post(
        "/api/v1/auth/login",
        json={"email": reset_email, "password": "NewStrongPassword456!"},
    )
    assert good_login.status_code == 200


def test_workspace_crud_and_archival(client: TestClient):
    """Test 3: Workspace creation, retrieval, updates, and archival."""
    email = f"owner_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "OwnerPassword123!", "display_name": "Workspace Owner"},
    ).json()
    headers = {"Authorization": f"Bearer {reg['session_token']}"}

    # Create dedicated project workspace
    create_res = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": "Quantum Neural Computing Lab",
            "description": "Collaborative research on hybrid quantum-classical algorithms.",
            "settings": {"require_independent_review": True, "max_autonomous_budget": 100},
        },
    )
    assert create_res.status_code == 201
    ws = create_res.json()
    ws_id = ws["id"]
    assert ws["name"] == "Quantum Neural Computing Lab"
    assert ws["settings"]["require_independent_review"] is True

    # Update workspace
    patch_res = client.patch(
        f"/api/v1/workspaces/{ws_id}",
        headers=headers,
        json={"description": "Updated lab description.", "settings": {"max_autonomous_budget": 150}},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated lab description."
    assert patch_res.json()["settings"]["max_autonomous_budget"] == 150

    # Archive workspace
    arch_res = client.post(f"/api/v1/workspaces/{ws_id}/archive", headers=headers)
    assert arch_res.status_code == 200

    # Restore workspace
    rest_res = client.post(f"/api/v1/workspaces/{ws_id}/restore", headers=headers)
    assert rest_res.status_code == 200


def test_workspace_invitations_and_role_management(client: TestClient):
    """Test 4: Member invitation, acceptance, role change, and RBAC enforcement."""
    # User 1: Workspace Owner
    owner_email = f"lead_{uuid.uuid4().hex[:8]}@neomon.ai"
    owner_reg = client.post(
        "/api/v1/auth/register",
        json={"email": owner_email, "password": "OwnerPassword123!", "display_name": "Lead Architect"},
    ).json()
    owner_headers = {"Authorization": f"Bearer {owner_reg['session_token']}"}

    ws = client.post(
        "/api/v1/workspaces",
        headers=owner_headers,
        json={"name": "Collaborative AI Lab"},
    ).json()
    ws_id = ws["id"]

    # User 2: New Reviewer
    reviewer_email = f"rev_{uuid.uuid4().hex[:8]}@neomon.ai"
    rev_reg = client.post(
        "/api/v1/auth/register",
        json={"email": reviewer_email, "password": "ReviewerPass123!", "display_name": "Senior Reviewer"},
    ).json()
    rev_headers = {"Authorization": f"Bearer {rev_reg['session_token']}"}

    # Owner invites User 2 as 'reviewer'
    invite_res = client.post(
        f"/api/v1/workspaces/{ws_id}/invitations",
        headers=owner_headers,
        json={"email": reviewer_email, "role": "reviewer"},
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    token = invite_data["invite_token"]

    # Lookup invitation
    lookup_res = client.get(f"/api/v1/invitations/lookup?token={token}")
    assert lookup_res.status_code == 200
    assert lookup_res.json()["workspace_name"] == "Collaborative AI Lab"
    assert lookup_res.json()["role"] == "reviewer"

    # User 2 accepts invitation
    accept_res = client.post(
        "/api/v1/invitations/accept",
        headers=rev_headers,
        json={"token": token},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "reviewer"

    # List members
    members_res = client.get(f"/api/v1/workspaces/{ws_id}/members", headers=owner_headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 2
    rev_member = next(m for m in members if m["email"] == reviewer_email)
    assert rev_member["role"] == "reviewer"

    # Owner promotes User 2 to 'admin'
    role_patch = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{rev_member['user_id']}",
        headers=owner_headers,
        json={"role": "admin"},
    )
    assert role_patch.status_code == 200


def test_threaded_discussions_and_mentions(client: TestClient):
    """Test 5: Discussion threads on investigations, replies, mentions, and resolution."""
    # User 1 & Workspace
    u1 = client.post(
        "/api/v1/auth/register",
        json={"email": f"u1_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Alice Researcher"},
    ).json()
    h1 = {"Authorization": f"Bearer {u1['session_token']}"}

    ws = client.post("/api/v1/workspaces", headers=h1, json={"name": "Discussion Lab"}).json()
    ws_id = ws["id"]

    # User 2 in workspace
    u2 = client.post(
        "/api/v1/auth/register",
        json={"email": f"u2_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Bob Reviewer"},
    ).json()
    h2 = {"Authorization": f"Bearer {u2['session_token']}"}
    inv = client.post(f"/api/v1/workspaces/{ws_id}/invitations", headers=h1, json={"email": u2["user"]["email"], "role": "reviewer"}).json()
    client.post("/api/v1/invitations/accept", headers=h2, json={"token": inv["invite_token"]})

    # Create thread targeting an entity (e.g. hypothesis)
    thread_res = client.post(
        f"/api/v1/collaboration/threads?workspace_id={ws_id}",
        headers=h1,
        json={
            "target_entity_type": "hypothesis",
            "target_entity_id": "hypo-101",
            "title": "Methodological validity of Hypothesis 1",
            "content": "Can we double-check the sampling bias @Bob?",
        },
    )
    assert thread_res.status_code == 201
    thread = thread_res.json()
    thread_id = thread["id"]
    assert thread["title"] == "Methodological validity of Hypothesis 1"
    assert len(thread["comments"]) == 1

    # Bob should have received an in-app mention notification!
    notif_res = client.get("/api/v1/collaboration/notifications", headers=h2)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert any("mentioned you" in n["message"] for n in notifs)

    # Bob replies to thread
    reply_res = client.post(
        f"/api/v1/collaboration/threads/{thread_id}/comments",
        headers=h2,
        json={"content": "I reviewed the dataset. Sampling bias is controlled for."},
    )
    assert reply_res.status_code == 201

    # Check thread comments
    get_thread = client.get(f"/api/v1/collaboration/threads/{thread_id}", headers=h1).json()
    assert len(get_thread["comments"]) == 2

    # Resolve thread
    res_res = client.post(f"/api/v1/collaboration/threads/{thread_id}/resolve", headers=h2)
    assert res_res.status_code == 200


def test_evidence_annotations_preserves_provenance(client: TestClient):
    """Test 6: Collaborative evidence annotations do NOT overwrite evidence.evidence_type."""
    # Setup user & workspace
    user_reg = client.post(
        "/api/v1/auth/register",
        json={"email": f"annotator_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Evidence Specialist"},
    ).json()
    headers = {"Authorization": f"Bearer {user_reg['session_token']}"}

    ws = client.post("/api/v1/workspaces", headers=headers, json={"name": "Annotation Workspace"}).json()
    ws_id = ws["id"]

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv_res = client.post(
            "/api/v1/research/investigations",
            headers=headers,
            json={"question": "Does fine-tuning reduce hallucination in medical reasoning LLMs?", "workspace_id": ws_id},
        )
        assert inv_res.status_code == 200
        inv_data = inv_res.json()["investigation"]
        inv_id = uuid.UUID(inv_data["id"])

        async def _seed_evidence():
            async with SessionFactory() as session:
                src = Source(
                    id=uuid.uuid4(),
                    investigation_id=inv_id,
                    title="Empirical Assessment of LLM Hallucinations",
                    canonical_url="https://doi.org/10.1000/182",
                    original_url="https://doi.org/10.1000/182",
                    source_type="peer_reviewed_journal",
                    publisher="Nature Machine Intelligence",
                    authors_json='["Smith et al."]',
                    relevance_score=0.95,
                    relevance_reasons_json='["Direct evidence"]',
                    inclusion_status="included",
                )
                session.add(src)
                ev = Evidence(
                    id=uuid.uuid4(),
                    source_id=src.id,
                    exact_text="Fine-tuning with synthetic verification reduced hallucinations by 42%.",
                    evidence_type="empirical_result",
                    extraction_method="direct_extraction",
                    relevance_score=0.88,
                )
                session.add(ev)
                await session.commit()
                return ev.id

        ev_id = client.portal.call(_seed_evidence)

    # Add annotation
    ann_res = client.post(
        f"/api/v1/collaboration/annotations?workspace_id={ws_id}",
        headers=headers,
        json={
            "investigation_id": str(inv_id),
            "evidence_id": str(ev_id),
            "annotation_type": "methodological_concern",
            "comment": "Sample size is relatively small (n=45), recommend cautious interpretation.",
            "reviewer_rationale": "High p-value risk.",
        },
    )
    assert ann_res.status_code == 201
    ann_data = ann_res.json()
    assert ann_data["annotation_type"] == "methodological_concern"

    # Verify underlying evidence.evidence_type was NOT overwritten!
    check_ev_res = client.get(f"/api/v1/research/evidence?investigation_id={inv_id}")
    assert check_ev_res.status_code == 200, f"Failed: {check_ev_res.text}"
    check_ev = check_ev_res.json()["items"][0]
    assert check_ev["evidence_type"] == "empirical_result", "Evidence original type must remain unchanged!"


def test_peer_review_self_approval_guard(client: TestClient):
    """Test 7: Formal review requests and self-approval block enforcement."""
    # User 1: Author
    u1 = client.post(
        "/api/v1/auth/register",
        json={"email": f"author_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Author Scientist"},
    ).json()
    h1 = {"Authorization": f"Bearer {u1['session_token']}"}

    ws = client.post(
        "/api/v1/workspaces",
        headers=h1,
        json={"name": "Peer Review Lab", "settings": {"require_independent_review": True}},
    ).json()
    ws_id = ws["id"]

    # User 2: Independent Reviewer
    u2 = client.post(
        "/api/v1/auth/register",
        json={"email": f"peer_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Peer Reviewer"},
    ).json()
    h2 = {"Authorization": f"Bearer {u2['session_token']}"}
    inv = client.post(f"/api/v1/workspaces/{ws_id}/invitations", headers=h1, json={"email": u2["user"]["email"], "role": "reviewer"}).json()
    client.post("/api/v1/invitations/accept", headers=h2, json={"token": inv["invite_token"]})

    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv_data = client.post(
            "/api/v1/research/investigations",
            headers=h1,
            json={"question": "What is the impact of synthetic data on neural network scaling laws?", "workspace_id": ws_id},
        ).json()["investigation"]
        inv_id = inv_data["id"]

    # Author submits review request
    rev_req = client.post(
        f"/api/v1/collaboration/reviews?workspace_id={ws_id}",
        headers=h1,
        json={
            "investigation_id": inv_id,
            "target_type": "investigation",
            "target_id": inv_id,
            "title": "Synthesis Report and Empirical Findings Review",
            "description": "Please evaluate evidence strength and contradiction resolution.",
            "requires_independent_review": True,
        },
    ).json()
    req_id = rev_req["id"]
    assert rev_req["status"] == "submitted"

    # CRITICAL SECURITY TEST: Author attempts to approve their own request -> MUST BE REJECTED 403!
    self_approve_res = client.post(
        f"/api/v1/collaboration/reviews/{req_id}/decisions",
        headers=h1,
        json={"decision": "approved", "rationale": "I think my own work is great!"},
    )
    assert self_approve_res.status_code == 403, "Self-approval guard must block author from approving own review!"
    assert "Self-approval guard" in self_approve_res.json()["detail"]

    # Independent Reviewer approves -> SUCCEEDS 200
    peer_approve_res = client.post(
        f"/api/v1/collaboration/reviews/{req_id}/decisions",
        headers=h2,
        json={
            "decision": "approved",
            "rationale": "Evidence chain is sound, data sources verified, and conclusions well-calibrated.",
        },
    )
    assert peer_approve_res.status_code == 200
    assert peer_approve_res.json()["status"] == "approved"
    assert len(peer_approve_res.json()["decisions"]) == 1


def test_notifications_and_activity_audit_feed(client: TestClient):
    """Test 8: Workspace activity logging and user notifications management."""
    u = client.post(
        "/api/v1/auth/register",
        json={"email": f"audit_{uuid.uuid4().hex[:8]}@neomon.ai", "password": "Password123!", "display_name": "Audit Officer"},
    ).json()
    headers = {"Authorization": f"Bearer {u['session_token']}"}

    ws = client.post("/api/v1/workspaces", headers=headers, json={"name": "Audit Logging Workspace"}).json()
    ws_id = ws["id"]

    # Workspace creation should have produced activity
    act_res = client.get(f"/api/v1/workspaces/{ws_id}/activity", headers=headers)
    assert act_res.status_code == 200
    activities = act_res.json()
    assert len(activities) >= 1
    assert any(a["action_type"] == "workspace_created" for a in activities)

    # Notifications unread count
    count_res = client.get("/api/v1/collaboration/notifications/unread-count", headers=headers)
    assert count_res.status_code == 200
    assert "unread_count" in count_res.json()

    # Mark all read
    mark_all = client.post("/api/v1/collaboration/notifications/mark-all-read", headers=headers)
    assert mark_all.status_code == 200
