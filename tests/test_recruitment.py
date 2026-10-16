from api import app
from database import query_db, execute_db


def test_recruiter_job_management(client):
    # Login recruiter
    client.post("/api/auth/login", json={"email": "recruiter@gmail.com", "password": "recruiter123", "role": "recruiter"})

    # Post new job
    res = client.post("/api/recruiter/jobs", json={
        "title": "Automated Test Engineer",
        "description": "Responsible for automated integration tests and QA.",
        "location": "Nagpur / Remote",
        "employment_type": "Full-time",
        "salary_min": 500000,
        "salary_max": 850000,
        "experience_years_min": 2,
        "required_skills": "Python, Pytest, SQL, Selenium"
    })
    assert res.status_code == 201
    job_id = res.get_json()["job"]["id"]

    # Change status to Closed
    res_status = client.patch(f"/api/recruiter/jobs/{job_id}/status", json={"status": "Closed"})
    assert res_status.status_code == 200
    assert "Closed" in res_status.get_json()["message"]

    # Reopen job
    client.patch(f"/api/recruiter/jobs/{job_id}/status", json={"status": "Open"})

    # Clean up
    execute_db("DELETE FROM jobs WHERE id = ?", (job_id,))


def test_job_application_and_duplicate_prevention(client):
    # Get an open job ID
    job = query_db("SELECT id FROM jobs WHERE status = 'Open' LIMIT 1", one=True)
    assert job is not None
    job_id = job["id"]

    # Login candidate
    client.post("/api/auth/login", json={"email": "user@gmail.com", "password": "user123", "role": "candidate"})

    # Delete any prior application for this job
    candidate = query_db("SELECT id FROM users WHERE email = 'user@gmail.com'", one=True)
    execute_db("DELETE FROM applications WHERE candidate_id = ? AND job_id = ?", (candidate["id"], job_id))

    # Apply
    res_apply = client.post(f"/api/candidate/jobs/{job_id}/apply", json={
        "cover_letter": "Automated test application letter."
    })
    assert res_apply.status_code == 201
    app_id = res_apply.get_json()["application_id"]

    # Attempt duplicate application
    res_dup = client.post(f"/api/candidate/jobs/{job_id}/apply", json={
        "cover_letter": "Duplicate attempt."
    })
    assert res_dup.status_code == 409
    assert "already applied" in res_dup.get_json()["message"]

    # Recruiter review and status change
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "recruiter@gmail.com", "password": "recruiter123", "role": "recruiter"})

    res_decide = client.patch(f"/api/recruiter/applications/{app_id}/status", json={
        "status": "Shortlisted",
        "note": "Candidate shows strong test qualifications."
    })
    assert res_decide.status_code == 200
    assert res_decide.get_json()["new_status"] == "Shortlisted"

    # Verify history entry
    hist = query_db("SELECT * FROM application_status_history WHERE application_id = ? ORDER BY id DESC LIMIT 1", (app_id,), one=True)
    assert hist is not None
    assert hist["new_status"] == "Shortlisted"

    # Clean up
    execute_db("DELETE FROM application_status_history WHERE application_id = ?", (app_id,))
    execute_db("DELETE FROM applications WHERE id = ?", (app_id,))
