from flask import Blueprint, request, jsonify, session
from database import query_db, execute_db
from app.services.auth_service import get_current_user, login_required
from app.services.notification_service import create_notification

recruiter_bp = Blueprint("recruiter", __name__, url_prefix="/api/recruiter")


@recruiter_bp.route("/company", methods=["GET", "POST"])
@login_required(roles="recruiter")
def recruiter_company():
    user = get_current_user()
    user_id = user["id"]

    if request.method == "GET":
        comp = query_db("SELECT * FROM companies WHERE user_id = ?", (user_id,), one=True)
        return jsonify({
            "status": "success",
            "has_company": bool(comp),
            "company": dict(comp) if comp else None
        })

    # POST create / update company profile
    data = request.get_json(silent=True) or {}
    c_name = str(data.get("company_name", "")).strip()
    if not c_name:
        return jsonify({"status": "error", "message": "Company name is required."}), 400

    desc = str(data.get("description", "")).strip()
    web = str(data.get("website", "")).strip()
    loc = str(data.get("location", "")).strip()
    ind = str(data.get("industry", "Information Technology")).strip()
    size = str(data.get("company_size", "10-50")).strip()

    existing = query_db("SELECT id FROM companies WHERE user_id = ?", (user_id,), one=True)
    if existing:
        execute_db("""
            UPDATE companies
            SET company_name = ?, description = ?, website = ?, location = ?, industry = ?, company_size = ?
            WHERE user_id = ?
        """, (c_name, desc, web, loc, ind, size, user_id))
        company_id = existing["id"]
    else:
        res = execute_db("""
            INSERT INTO companies (user_id, company_name, description, website, location, industry, company_size, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, c_name, desc, web, loc, ind, size))
        company_id = res["lastrowid"]

    # Mark recruiter onboarding as complete
    execute_db("UPDATE users SET onboarding_status = 'completed', onboarding_step = 6 WHERE id = ?", (user_id,))

    comp = query_db("SELECT * FROM companies WHERE id = ?", (company_id,), one=True)
    return jsonify({
        "status": "success",
        "message": "Company profile saved.",
        "company": dict(comp)
    })


@recruiter_bp.route("/dashboard", methods=["GET"])
@login_required(roles="recruiter")
def recruiter_dashboard():
    user = get_current_user()
    recruiter_id = user["id"]

    # Stats strictly scoped to this recruiter
    active_jobs = query_db("SELECT COUNT(*) as c FROM jobs WHERE recruiter_id = ? AND status = 'Open'", (recruiter_id,), one=True)["c"]
    total_apps = query_db("""
        SELECT COUNT(a.id) as c
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.recruiter_id = ?
    """, (recruiter_id,), one=True)["c"]

    pending_review = query_db("""
        SELECT COUNT(a.id) as c
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.recruiter_id = ? AND a.status IN ('Applied', 'Under Review')
    """, (recruiter_id,), one=True)["c"]

    shortlisted = query_db("""
        SELECT COUNT(a.id) as c
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.recruiter_id = ? AND a.status = 'Shortlisted'
    """, (recruiter_id,), one=True)["c"]

    # Recent applications
    recent = query_db("""
        SELECT a.id, a.status, a.applied_at, a.compatibility_score,
               u.full_name as candidate_name, u.email as candidate_email,
               j.title as job_title
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.candidate_id = u.id
        WHERE j.recruiter_id = ?
        ORDER BY a.applied_at DESC
        LIMIT 5
    """, (recruiter_id,))

    return jsonify({
        "status": "success",
        "metrics": {
            "active_jobs": active_jobs,
            "total_applications": total_apps,
            "pending_review": pending_review,
            "shortlisted": shortlisted
        },
        "recent_applications": [dict(r) for r in recent],
        "recruiter": user
    })


@recruiter_bp.route("/jobs", methods=["GET", "POST"])
@login_required(roles="recruiter")
def recruiter_jobs():
    user = get_current_user()
    recruiter_id = user["id"]

    if request.method == "GET":
        jobs = query_db("""
            SELECT j.*,
                   (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as application_count,
                   (SELECT COUNT(*) FROM applications WHERE job_id = j.id AND status = 'Shortlisted') as shortlist_count
            FROM jobs j
            WHERE j.recruiter_id = ?
            ORDER BY j.created_at DESC
        """, (recruiter_id,))
        return jsonify({"status": "success", "count": len(jobs), "jobs": [dict(j) for j in jobs]})

    # POST create new job
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    desc = str(data.get("description", "")).strip()
    if not title or not desc:
        return jsonify({"status": "error", "message": "Job title and description are required."}), 400

    comp = query_db("SELECT id FROM companies WHERE user_id = ?", (recruiter_id,), one=True)
    company_id = comp["id"] if comp else None

    loc = str(data.get("location", "Nagpur / Remote")).strip()
    emp_type = str(data.get("employment_type", "Full-time")).strip()
    s_min = float(data.get("salary_min", 400000))
    s_max = float(data.get("salary_max", 800000))
    exp_min = int(data.get("experience_years_min", 0))
    skills = str(data.get("required_skills", "")).strip()

    res = execute_db("""
        INSERT INTO jobs (
            recruiter_id, company_id, title, description, location, employment_type,
            salary_min, salary_max, experience_years_min, required_skills, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open')
    """, (recruiter_id, company_id, title, desc, loc, emp_type, s_min, s_max, exp_min, skills))

    job = query_db("SELECT * FROM jobs WHERE id = ?", (res["lastrowid"],), one=True)
    return jsonify({
        "status": "success",
        "message": f"Job '{title}' published successfully.",
        "job": dict(job)
    }), 201


@recruiter_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@login_required(roles="recruiter")
def update_job(job_id):
    recruiter_id = session["user_id"]
    job = query_db("SELECT * FROM jobs WHERE id = ? AND recruiter_id = ?", (job_id, recruiter_id), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found or unauthorized."}), 404

    data = request.get_json(silent=True) or {}
    allowed = ["title", "description", "location", "employment_type", "salary_min", "salary_max", "experience_years_min", "required_skills", "status"]
    updates = {}
    for k in allowed:
        if k in data:
            updates[k] = data[k]

    if updates:
        set_str = ", ".join(f'"{k}" = ?' for k in updates.keys())
        execute_db(f'UPDATE jobs SET {set_str}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', list(updates.values()) + [job_id])

    updated_job = query_db("SELECT * FROM jobs WHERE id = ?", (job_id,), one=True)
    return jsonify({"status": "success", "message": "Job updated.", "job": dict(updated_job)})


@recruiter_bp.route("/jobs/<int:job_id>/status", methods=["PATCH"])
@login_required(roles="recruiter")
def change_job_status(job_id):
    recruiter_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip()

    if new_status not in {"Open", "Closed", "Cancelled"}:
        return jsonify({"status": "error", "message": "Status must be 'Open', 'Closed', or 'Cancelled'."}), 400

    job = query_db("SELECT * FROM jobs WHERE id = ? AND recruiter_id = ?", (job_id, recruiter_id), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found or unauthorized."}), 404

    execute_db("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, job_id))
    return jsonify({"status": "success", "message": f"Job status changed to {new_status}."})


@recruiter_bp.route("/applications", methods=["GET"])
@login_required(roles="recruiter")
def recruiter_applications():
    recruiter_id = session["user_id"]
    job_id = request.args.get("job_id")
    status_filter = request.args.get("status", "all")

    sql = """
        SELECT a.*,
               j.title as job_title, j.location as job_location,
               u.full_name as candidate_name, u.email as candidate_email,
               u.phone as candidate_phone, u.location as candidate_location,
               u.education as candidate_education, u.experience as candidate_experience,
               u.current_occupation, u.resume_filename
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.candidate_id = u.id
        WHERE j.recruiter_id = ?
    """
    params = [recruiter_id]

    if job_id:
        sql += " AND a.job_id = ?"
        params.append(job_id)

    if status_filter != "all":
        sql += " AND a.status = ?"
        params.append(status_filter)

    sql += " ORDER BY a.applied_at DESC"
    rows = query_db(sql, params)

    apps = []
    for r in rows:
        skills = query_db("SELECT skill, proficiency FROM user_skills WHERE user_id = ?", (r["candidate_id"],))
        apps.append({
            **dict(r),
            "candidate_skills": [dict(s) for s in skills]
        })

    return jsonify({"status": "success", "count": len(apps), "applications": apps})


@recruiter_bp.route("/applications/<int:app_id>/status", methods=["PATCH"])
@login_required(roles="recruiter")
def update_application_status(app_id):
    recruiter_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip()
    note = str(data.get("note", "")).strip()

    valid_statuses = {"Under Review", "Shortlisted", "Selected", "Rejected"}
    if new_status not in valid_statuses:
        return jsonify({"status": "error", "message": f"Invalid status. Choose from: {', '.join(valid_statuses)}."}), 400

    app = query_db("""
        SELECT a.*, j.title as job_title, c.company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE a.id = ? AND j.recruiter_id = ?
    """, (app_id, recruiter_id), one=True)

    if not app:
        return jsonify({"status": "error", "message": "Application not found or unauthorized."}), 404

    old_status = app["status"]
    execute_db("UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, app_id))

    execute_db("""
        INSERT INTO application_status_history (application_id, old_status, new_status, changed_by, note)
        VALUES (?, ?, ?, ?, ?)
    """, (app_id, old_status, new_status, recruiter_id, note or f"Status changed to {new_status} by recruiter."))

    # In-app notification to candidate
    create_notification(
        app["candidate_id"],
        f"Application {new_status}",
        f"Your application for {app['job_title']} at {app['company_name']} is now: {new_status}.",
        "application"
    )

    return jsonify({
        "status": "success",
        "message": f"Application status updated to '{new_status}'.",
        "old_status": old_status,
        "new_status": new_status
    })


@recruiter_bp.route("/analytics", methods=["GET"])
@login_required(roles="recruiter")
def recruiter_analytics():
    recruiter_id = session["user_id"]

    status_counts = query_db("""
        SELECT a.status, COUNT(a.id) as count
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.recruiter_id = ?
        GROUP BY a.status
    """, (recruiter_id,))

    jobs_stats = query_db("""
        SELECT j.title, COUNT(a.id) as applications_count,
               AVG(a.compatibility_score) as avg_compatibility
        FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE j.recruiter_id = ?
        GROUP BY j.id
        ORDER BY applications_count DESC
    """, (recruiter_id,))

    avg_compat = query_db("""
        SELECT AVG(a.compatibility_score) as avg_comp
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.recruiter_id = ?
    """, (recruiter_id,), one=True)

    return jsonify({
        "status": "success",
        "status_distribution": {r["status"]: r["count"] for r in status_counts},
        "jobs_summary": [
            {
                "title": j["title"],
                "applications_count": j["applications_count"],
                "avg_compatibility": round(j["avg_compatibility"] or 0, 1)
            }
            for j in jobs_stats
        ],
        "overall_avg_compatibility": round(avg_compat["avg_comp"] or 0, 1) if avg_compat else 0
    })
