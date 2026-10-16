from api import app
from database import query_db, execute_db


def test_admin_metrics_and_user_moderation(client):
    # Login admin
    client.post("/api/auth/login", json={"email": "admin@jobbridge.local", "password": "admin123"})

    # Check metrics
    res_m = client.get("/api/admin/metrics")
    assert res_m.status_code == 200
    m = res_m.get_json()["metrics"]
    assert m["total_candidates"] >= 1
    assert m["total_recruiters"] >= 1
    assert m["total_jobs"] >= 1

    # List users
    res_u = client.get("/api/admin/users")
    assert res_u.status_code == 200
    users = res_u.get_json()["users"]
    assert len(users) >= 2

    # Find candidate
    cand = next((u for u in users if u["role"] == "candidate"), None)
    assert cand is not None
    cand_id = cand["id"]

    # Suspend user
    res_susp = client.patch(f"/api/admin/users/{cand_id}/status", json={"status": "suspended"})
    assert res_susp.status_code == 200
    assert res_susp.get_json()["status"] == "suspended"

    # Verify audit log was recorded
    log = query_db("SELECT * FROM audit_logs WHERE target_id = ? ORDER BY id DESC LIMIT 1", (cand_id,), one=True)
    assert log is not None
    assert "SUSPENDED" in log["action"]

    # Reactivate user
    res_act = client.patch(f"/api/admin/users/{cand_id}/status", json={"status": "active"})
    assert res_act.status_code == 200

    # Self-suspension prevention
    admin_row = query_db("SELECT id FROM users WHERE email = 'admin@jobbridge.local'", one=True)
    res_self = client.patch(f"/api/admin/users/{admin_row['id']}/status", json={"status": "suspended"})
    assert res_self.status_code == 400
    assert "cannot suspend their own account" in res_self.get_json()["message"]
