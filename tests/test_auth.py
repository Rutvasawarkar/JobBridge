from api import app
from database import query_db, execute_db


def test_registration_and_password_hashing(client):
    test_email = "new_test_candidate@jobbridge.local"
    execute_db("DELETE FROM users WHERE email = ?", (test_email,))

    res = client.post("/api/auth/register", json={
        "name": "Test Candidate",
        "email": test_email,
        "password": "securepassword123",
        "role": "candidate"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["user"]["email"] == test_email
    assert data["user"]["role"] == "candidate"

    # Verify password hash in database is NOT plaintext
    user_row = query_db("SELECT password_hash FROM users WHERE email = ?", (test_email,), one=True)
    assert user_row is not None
    assert user_row["password_hash"] != "securepassword123"
    assert user_row["password_hash"].startswith("scrypt:") or user_row["password_hash"].startswith("pbkdf2:")

    # Clean up
    execute_db("DELETE FROM users WHERE email = ?", (test_email,))


def test_login_and_session_restoration(client):
    # Login candidate
    res = client.post("/api/auth/login", json={
        "email": "user@gmail.com",
        "password": "user123",
        "role": "candidate"
    })
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

    # Verify /api/auth/me restores session
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 200
    assert res_me.get_json()["authenticated"] is True
    assert res_me.get_json()["user"]["email"] == "user@gmail.com"

    # Logout
    res_out = client.post("/api/auth/logout")
    assert res_out.status_code == 200

    # Verify session cleared
    res_me2 = client.get("/api/auth/me")
    assert res_me2.get_json()["authenticated"] is False


def test_role_enforcement(client):
    # Candidate should be forbidden from accessing admin endpoints
    client.post("/api/auth/login", json={"email": "user@gmail.com", "password": "user123", "role": "candidate"})
    res = client.get("/api/admin/metrics")
    assert res.status_code == 403

    # Candidate should be forbidden from accessing recruiter endpoints
    res_rec = client.get("/api/recruiter/dashboard")
    assert res_rec.status_code == 403

    # Admin can access admin endpoints
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "admin@jobbridge.local", "password": "admin123"})
    res_adm = client.get("/api/admin/metrics")
    assert res_adm.status_code == 200
    assert "metrics" in res_adm.get_json()


def test_candidate_onboarding_persistence(client):
    test_email = "onb_test@jobbridge.local"
    execute_db("DELETE FROM users WHERE email = ?", (test_email,))

    # Register candidate
    client.post("/api/auth/register", json={
        "name": "Onboarding Candidate",
        "email": test_email,
        "password": "password123",
        "role": "candidate"
    })

    # Initially step is 1 and status is pending
    res_onb = client.get("/api/candidate/onboarding")
    assert res_onb.status_code == 200
    assert res_onb.get_json()["onboarding_status"] == "pending"

    # Save Step 1
    res_s1 = client.post("/api/candidate/onboarding/step", json={
        "step": 1,
        "name": "Onboarding Candidate",
        "phone": "+91 99999 88888",
        "location": "Nagpur, India"
    })
    assert res_s1.status_code == 200
    assert res_s1.get_json()["onboarding_step"] == 2

    # Save Step 2 (Education)
    res_s2 = client.post("/api/candidate/onboarding/step", json={
        "step": 2,
        "education": "M.Sc Data Analytics"
    })
    assert res_s2.status_code == 200
    assert res_s2.get_json()["onboarding_step"] == 3

    # Clean up
    execute_db("DELETE FROM users WHERE email = ?", (test_email,))
