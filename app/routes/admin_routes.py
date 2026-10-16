from flask import Blueprint, request, jsonify, session
from database import query_db, execute_db
from app.services.auth_service import get_current_user, login_required
from app.services.audit_service import log_audit

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/metrics", methods=["GET"])
@login_required(roles="admin")
def admin_metrics():
    user_counts = query_db("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    role_map = {r["role"]: r["count"] for r in user_counts}

    total_jobs = query_db("SELECT COUNT(*) as c FROM jobs", one=True)["c"]
    active_jobs = query_db("SELECT COUNT(*) as c FROM jobs WHERE status = 'Open'", one=True)["c"]
    total_apps = query_db("SELECT COUNT(*) as c FROM applications", one=True)["c"]
    total_companies = query_db("SELECT COUNT(*) as c FROM companies", one=True)["c"]
    suspended_users = query_db("SELECT COUNT(*) as c FROM users WHERE status = 'suspended'", one=True)["c"]

    return jsonify({
        "status": "success",
        "metrics": {
            "total_candidates": role_map.get("candidate", 0),
            "total_recruiters": role_map.get("recruiter", 0),
            "total_admins": role_map.get("admin", 0),
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applications": total_apps,
            "total_companies": total_companies,
            "suspended_users": suspended_users
        }
    })


@admin_bp.route("/users", methods=["GET"])
@login_required(roles="admin")
def admin_users():
    role_filter = request.args.get("role", "all")
    search = request.args.get("q", "").strip().lower()

    sql = "SELECT id, name, full_name, email, role, location, status, created_at FROM users"
    params = []
    clauses = []

    if role_filter != "all":
        clauses.append("role = ?")
        params.append(role_filter)

    if search:
        clauses.append("(LOWER(name) LIKE ? OR LOWER(email) LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY created_at DESC"
    users = query_db(sql, params)

    return jsonify({"status": "success", "count": len(users), "users": [dict(u) for u in users]})


@admin_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@login_required(roles="admin")
def update_user_status(user_id):
    current_admin = get_current_user()
    if user_id == current_admin["id"]:
        return jsonify({"status": "error", "message": "Administrators cannot suspend their own account."}), 400

    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip().lower()
    if new_status not in {"active", "suspended"}:
        return jsonify({"status": "error", "message": "Status must be 'active' or 'suspended'."}), 400

    target_user = query_db("SELECT email, role, status FROM users WHERE id = ?", (user_id,), one=True)
    if not target_user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    execute_db("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
    log_audit(
        current_admin["id"],
        f"USER_STATUS_CHANGE_{new_status.upper()}",
        "user",
        user_id,
        f"Changed status of {target_user['email']} from {target_user['status']} to {new_status}"
    )

    return jsonify({
        "status": "success",
        "message": f"User status updated to {new_status}.",
        "user_id": user_id,
        "status": new_status
    })


@admin_bp.route("/jobs", methods=["GET"])
@login_required(roles="admin")
def admin_jobs():
    jobs = query_db("""
        SELECT j.*, c.company_name, u.email as recruiter_email,
               (SELECT COUNT(*) FROM applications WHERE job_id = j.id) as applications_count
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        LEFT JOIN users u ON j.recruiter_id = u.id
        ORDER BY j.created_at DESC
    """)
    return jsonify({"status": "success", "count": len(jobs), "jobs": [dict(j) for j in jobs]})


@admin_bp.route("/jobs/<int:job_id>/status", methods=["PATCH"])
@login_required(roles="admin")
def moderate_job(job_id):
    current_admin = get_current_user()
    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip()

    if new_status not in {"Open", "Closed", "Cancelled"}:
        return jsonify({"status": "error", "message": "Status must be 'Open', 'Closed', or 'Cancelled'."}), 400

    job = query_db("SELECT title, status FROM jobs WHERE id = ?", (job_id,), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404

    execute_db("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, job_id))
    log_audit(
        current_admin["id"],
        f"JOB_MODERATION_{new_status.upper()}",
        "job",
        job_id,
        f"Moderated job '{job['title']}' status to {new_status}"
    )

    return jsonify({"status": "success", "message": f"Job status updated to {new_status}."})


@admin_bp.route("/audit-logs", methods=["GET"])
@login_required(roles="admin")
def get_audit_logs():
    logs = query_db("""
        SELECT l.*, u.email as actor_email
        FROM audit_logs l
        LEFT JOIN users u ON l.actor_id = u.id
        ORDER BY l.created_at DESC
        LIMIT 50
    """)
    return jsonify({"status": "success", "count": len(logs), "logs": [dict(l) for l in logs]})
