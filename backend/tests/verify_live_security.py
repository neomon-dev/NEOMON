import requests
import uuid

BASE = "http://127.0.0.1:8000/api/v1"

# 1. Register Alice
uid_a = uuid.uuid4().hex[:6]
res_a = requests.post(f"{BASE}/auth/register", json={
    "email": f"live_alice_{uid_a}@neomon.ai", "password": "Password123!", "display_name": "Dr. Alice"
})
assert res_a.status_code == 201, res_a.text
token_a = res_a.json()["session_token"]
headers_a = {"Authorization": f"Bearer {token_a}"}

# Alice creates Workspace A
ws_a = requests.post(f"{BASE}/workspaces", json={"name": "Alice Secret Genomics"}, headers=headers_a).json()
ws_a_id = ws_a["id"]

# Alice uses an existing investigation in Workspace A
inv_a_id = "8ccabf7a-7a9a-4792-9c76-7d086750c831"
ws_a_id = "0e496f75-ae4c-42c3-98ab-9a1a5b489b93"
# Log in as Alice from the previous run
# Or register a fresh Alice and add her as researcher
print(f"Testing with investigation {inv_a_id} in workspace {ws_a_id}")

# 2. Register Bob
uid_b = uuid.uuid4().hex[:6]
res_b = requests.post(f"{BASE}/auth/register", json={
    "email": f"live_bob_{uid_b}@neomon.ai", "password": "Password123!", "display_name": "Dr. Bob"
})
assert res_b.status_code == 201, res_b.text
token_b = res_b.json()["session_token"]
headers_b = {"Authorization": f"Bearer {token_b}"}

# Bob creates Workspace B
ws_b = requests.post(f"{BASE}/workspaces", json={"name": "Bob Quantum Computing"}, headers=headers_b).json()
ws_b_id = ws_b["id"]
print(f"Bob created workspace {ws_b_id}")

# 3. Test Horizontal Privilege Escalation
# Bob tries to access Alice's workspace
r1 = requests.get(f"{BASE}/workspaces/{ws_a_id}", headers=headers_b)
print(f"Bob GET Alice's workspace: {r1.status_code} (Expected 403)")
assert r1.status_code == 403, f"Expected 403, got {r1.status_code}"

# Bob tries to access Alice's investigation
r2 = requests.get(f"{BASE}/research/investigations/{inv_a_id}", headers=headers_b)
print(f"Bob GET Alice's investigation: {r2.status_code} (Expected 403)")
assert r2.status_code == 403, f"Expected 403, got {r2.status_code}"

# Bob tries to access Alice's investigation sources
r3 = requests.get(f"{BASE}/research/investigations/{inv_a_id}/sources", headers=headers_b)
print(f"Bob GET Alice's sources: {r3.status_code} (Expected 403)")
assert r3.status_code == 403, f"Expected 403, got {r3.status_code}"

# Bob tries to access Alice's investigation graph
r4 = requests.get(f"{BASE}/research/investigations/{inv_a_id}/graph", headers=headers_b)
print(f"Bob GET Alice's graph: {r4.status_code} (Expected 403)")
assert r4.status_code == 403, f"Expected 403, got {r4.status_code}"

# Bob tries to generate a report on Alice's investigation
r5 = requests.post(f"{BASE}/research/investigations/{inv_a_id}/reports/generate", headers=headers_b)
print(f"Bob POST report generate on Alice's investigation: {r5.status_code} (Expected 403)")
assert r5.status_code == 403, f"Expected 403, got {r5.status_code}"

# Bob tries to export Alice's investigation markdown
r6 = requests.get(f"{BASE}/research/investigations/{inv_a_id}/export/markdown", headers=headers_b)
print(f"Bob GET export markdown on Alice's investigation: {r6.status_code} (Expected 403)")
assert r6.status_code == 403, f"Expected 403, got {r6.status_code}"

# Bob tries to add comment to Alice's workspace thread
r7 = requests.post(f"{BASE}/collaboration/threads?workspace_id={ws_a_id}", json={
    "target_entity_type": "investigation", "target_entity_id": inv_a_id, "content": "Unauthorized intrusion"
}, headers=headers_b)
print(f"Bob POST thread in Alice's workspace: {r7.status_code} (Expected 403)")
assert r7.status_code == 403, f"Expected 403, got {r7.status_code}"

# 4. Peer Review Self-Approval Guard Test
# Alice creates a review request on her own investigation
rev_res = requests.post(f"{BASE}/collaboration/reviews?workspace_id={ws_a_id}", json={
    "target_type": "investigation",
    "target_id": inv_a_id,
    "investigation_id": inv_a_id,
    "title": "Prime Editing Review",
    "required_approvals": 1,
    "summary": "Please review prime editing breakthroughs"
}, headers=headers_a)
assert rev_res.status_code == 201, rev_res.text
rev_id = rev_res.json()["id"]

# Alice tries to approve her own review request -> MUST RETURN 403
self_app_res = requests.post(f"{BASE}/collaboration/reviews/{rev_id}/decisions", json={
    "decision": "approved",
    "rationale": "I approve my own paper!"
}, headers=headers_a)
print(f"Alice self-approval attempt: {self_app_res.status_code} (Expected 403)")
assert self_app_res.status_code == 403, f"Expected 403, got {self_app_res.status_code}"

# 5. Session Logout & Revocation
out_res = requests.post(f"{BASE}/auth/logout", headers=headers_a)
print(f"Alice logout: {out_res.status_code} (Expected 200)")
assert out_res.status_code == 200

# Alice tries to use revoked token
revoked_res = requests.get(f"{BASE}/auth/me", headers=headers_a)
print(f"Alice access with revoked token: {revoked_res.status_code} (Expected 401)")
assert revoked_res.status_code == 401, f"Expected 401, got {revoked_res.status_code}"

print("=== ALL LIVE HORIZONTAL, RBAC, SELF-APPROVAL & REVOCATION CHECKS PASSED ON LOCALHOST ===")
