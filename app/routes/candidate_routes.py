import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session, send_file
from database import query_db, execute_db
from app.services.auth_service import get_current_user, login_required, onboarding_required
from app.services.resume_service import save_resume_file
from app.services.recommendation_service import (
    calculate_job_compatibility,
    get_career_transitions,
    get_verified_courses_for_skills,
    parse_skills_list
)
from app.services.readiness_service import calculate_career_readiness

candidate_bp = Blueprint("candidate", __name__, url_prefix="/api/candidate")


@candidate_bp.route("/onboarding", methods=["GET"])
@login_required(roles="candidate")
def get_onboarding():
    user = get_current_user()
    return jsonify({
        "status": "success",
        "onboarding_step": user.get("onboarding_step", 1),
        "onboarding_status": user.get("onboarding_status", "pending"),
        "user": user
    })


@candidate_bp.route("/onboarding/step", methods=["POST"])
@login_required(roles="candidate")
def save_onboarding_step():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    user_id = user["id"]
    step = int(data.get("step", 1))

    updates = {}
    if step == 1:
        if "name" in data:
            name = str(data["name"]).strip()
            if not name:
                return jsonify({"status": "error", "message": "Name cannot be empty."}), 400
            updates["name"] = name
            updates["full_name"] = name
        if "phone" in data:
            updates["phone"] = str(data["phone"]).strip()
        if "location" in data:
            updates["location"] = str(data["location"]).strip()
        next_step = 2

    elif step == 2:
        if "education" in data:
            edu = str(data["education"]).strip()
            if not edu:
                return jsonify({"status": "error", "message": "Education details are required."}), 400
            updates["education"] = edu
        next_step = 3

    elif step == 3:
        if "experience" in data:
            try:
                exp = int(data["experience"])
                if exp < 0 or exp > 60:
                    raise ValueError
                updates["experience"] = exp
            except Exception:
                return jsonify({"status": "error", "message": "Experience must be between 0 and 60 years."}), 400
        if "current_occupation" in data:
            occ = str(data["current_occupation"]).strip()
            if not occ:
                return jsonify({"status": "error", "message": "Current occupation is required."}), 400
            updates["current_occupation"] = occ
        next_step = 4

    elif step == 4:
        if "career_interest" in data:
            updates["career_interest"] = str(data["career_interest"]).strip()
        if "headline" in data:
            updates["headline"] = str(data["headline"]).strip()
        if "bio" in data:
            updates["bio"] = str(data["bio"]).strip()
        next_step = 5

    elif step == 5:
        # Skills step
        raw_skills = data.get("skills", [])
        if isinstance(raw_skills, list):
            execute_db("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
            clean_skills = []
            seen = set()
            for s in raw_skills:
                if isinstance(s, dict):
                    name = str(s.get("skill", "")).strip()
                    prof = str(s.get("proficiency", "Intermediate")).strip()
                    yrs = float(s.get("years_experience", 1.0))
                else:
                    name = str(s).strip()
                    prof = "Intermediate"
                    yrs = 1.0
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    clean_skills.append((user_id, name, prof, yrs))

            if clean_skills:
                with query_db.__globals__["get_connection"]() as conn:
                    conn.executemany("""
                        INSERT OR IGNORE INTO user_skills (user_id, skill, proficiency, years_experience)
                        VALUES (?, ?, ?, ?)
                    """, clean_skills)
                    conn.commit()
        next_step = 6

    elif step == 6:
        # Finalization step
        updates["onboarding_status"] = "completed"
        updates["onboarding_step"] = 6
        next_step = 6

    else:
        return jsonify({"status": "error", "message": "Invalid onboarding step."}), 400

    if next_step < 6 and user.get("onboarding_status") != "completed":
        updates["onboarding_step"] = max(user.get("onboarding_step", 1), next_step)

    if updates:
        set_str = ", ".join(f'"{k}" = ?' for k in updates.keys())
        execute_db(f'UPDATE users SET {set_str} WHERE id = ?', list(updates.values()) + [user_id])

    updated_user = get_current_user()
    return jsonify({
        "status": "success",
        "message": "Onboarding step saved.",
        "onboarding_step": updated_user.get("onboarding_step"),
        "onboarding_status": updated_user.get("onboarding_status"),
        "user": updated_user
    })


@candidate_bp.route("/profile", methods=["GET"])
@login_required(roles="candidate")
def get_profile():
    return jsonify({"status": "success", "profile": get_current_user()})


@candidate_bp.route("/profile", methods=["PUT"])
@login_required(roles="candidate")
def update_profile():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    user_id = user["id"]

    allowed = {
        "name": "name", "full_name": "full_name", "phone": "phone",
        "location": "location", "education": "education", "experience": "experience",
        "current_occupation": "current_occupation", "career_interest": "career_interest",
        "headline": "headline", "bio": "bio"
    }

    updates = {}
    for k, col in allowed.items():
        if k in data:
            if k == "experience":
                try:
                    exp = int(data[k])
                    if exp >= 0:
                        updates[col] = exp
                except Exception:
                    pass
            else:
                updates[col] = str(data[k]).strip()

    if "name" in updates:
        updates["full_name"] = updates["name"]

    if updates:
        set_str = ", ".join(f'"{k}" = ?' for k in updates.keys())
        execute_db(f'UPDATE users SET {set_str} WHERE id = ?', list(updates.values()) + [user_id])

    # Update skills
    if "skills" in data and isinstance(data["skills"], list):
        execute_db("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
        for s in data["skills"]:
            if isinstance(s, dict):
                s_name = str(s.get("skill", "")).strip()
                prof = str(s.get("proficiency", "Intermediate"))
                yrs = float(s.get("years_experience", 1.0))
            else:
                s_name = str(s).strip()
                prof = "Intermediate"
                yrs = 1.0
            if s_name:
                execute_db("""
                    INSERT OR IGNORE INTO user_skills (user_id, skill, proficiency, years_experience)
                    VALUES (?, ?, ?, ?)
                """, (user_id, s_name, prof, yrs))

    return jsonify({"status": "success", "message": "Profile updated successfully.", "profile": get_current_user()})


@candidate_bp.route("/resume/upload", methods=["POST"])
@login_required(roles="candidate")
def upload_resume():
    user = get_current_user()
    if "resume" not in request.files:
        return jsonify({"status": "error", "message": "No resume file attached."}), 400

    file_obj = request.files["resume"]
    ok, path_or_err, original_filename = save_resume_file(user["id"], file_obj)
    if not ok:
        return jsonify({"status": "error", "message": path_or_err}), 400

    execute_db("""
        UPDATE users
        SET resume_filename = ?, resume_path = ?, resume_updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (original_filename, path_or_err, user["id"]))

    return jsonify({
        "status": "success",
        "message": f"Resume '{original_filename}' uploaded and verified successfully.",
        "resume_filename": original_filename
    })


@candidate_bp.route("/resume/download", methods=["GET"])
@login_required()
def download_resume():
    current_user = get_current_user()
    requested_user_id = request.args.get("user_id", current_user["id"])

    # If asking for another user's resume, verify recruiter or admin role
    if int(requested_user_id) != current_user["id"] and current_user["role"] not in {"recruiter", "admin"}:
        return jsonify({"status": "error", "message": "Unauthorized to view this resume."}), 403

    user_row = query_db("SELECT resume_filename, resume_path FROM users WHERE id = ?", (requested_user_id,), one=True)
    if not user_row or not user_row.get("resume_path") or not os.path.exists(user_row["resume_path"]):
        return jsonify({"status": "error", "message": "Resume file not found."}), 404

    return send_file(
        user_row["resume_path"],
        as_attachment=True,
        download_name=user_row.get("resume_filename", "resume.pdf")
    )


@candidate_bp.route("/dashboard", methods=["GET"])
@login_required(roles="candidate")
def candidate_dashboard():
    user = get_current_user()
    user_id = user["id"]

    # 1. Profile Strength Calculation
    factors = [
        bool(user.get("name")),
        bool(user.get("phone")),
        bool(user.get("location")),
        bool(user.get("education")),
        bool(user.get("current_occupation") and user["current_occupation"] != "Not specified"),
        bool(user.get("career_interest")),
        bool(user.get("skills")),
        bool(user.get("resume_filename"))
    ]
    strength = round((sum(factors) / len(factors)) * 100)

    # 2. Counts
    app_cnt = query_db("SELECT COUNT(*) as c FROM applications WHERE candidate_id = ?", (user_id,), one=True)["c"]
    saved_cnt = query_db("SELECT COUNT(*) as c FROM saved_jobs WHERE candidate_id = ?", (user_id,), one=True)["c"]
    learning_cnt = query_db("SELECT COUNT(*) as c FROM user_learning_progress WHERE user_id = ? AND status = 'Completed'", (user_id,), one=True)["c"]

    # 3. Recommended Jobs
    open_jobs = query_db("""
        SELECT j.*, c.company_name, c.location as company_location
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.status = 'Open'
        ORDER BY j.created_at DESC
        LIMIT 6
    """)

    ranked_jobs = []
    for job in open_jobs:
        comp = calculate_job_compatibility(user, job)
        ranked_jobs.append({
            **job,
            "compatibility_score": comp["score"],
            "compatibility_explanation": comp["explanation"],
            "matched_skills": comp["matched_skills"],
            "missing_skills": comp["missing_skills"]
        })
    ranked_jobs.sort(key=lambda x: x["compatibility_score"], reverse=True)

    # 4. Career Readiness preview
    target_role = user.get("career_interest") or "Data Analyst"
    readiness = calculate_career_readiness(user, target_role)

    return jsonify({
        "status": "success",
        "profile_strength": strength,
        "active_applications": app_cnt,
        "saved_jobs_count": saved_cnt,
        "completed_learning_count": learning_cnt,
        "career_readiness": readiness,
        "recommended_jobs": ranked_jobs[:4],
        "user": user
    })


@candidate_bp.route("/jobs", methods=["GET"])
@login_required(roles="candidate")
def list_jobs():
    user = get_current_user()
    user_id = user["id"]
    query = request.args.get("q", "").strip().lower()
    location = request.args.get("location", "all").strip().lower()
    emp_type = request.args.get("type", "all").strip().lower()

    sql = """
        SELECT j.*, c.company_name, c.location as company_location,
               (SELECT COUNT(*) FROM saved_jobs WHERE candidate_id = ? AND job_id = j.id) as is_saved,
               (SELECT status FROM applications WHERE candidate_id = ? AND job_id = j.id) as applied_status
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.status = 'Open'
    """
    params = [user_id, user_id]

    if location != "all":
        sql += " AND (LOWER(j.location) LIKE ? OR LOWER(c.location) LIKE ?)"
        params.extend([f"%{location}%", f"%{location}%"])

    if emp_type != "all":
        sql += " AND LOWER(j.employment_type) = ?"
        params.append(emp_type)

    sql += " ORDER BY j.created_at DESC"
    rows = query_db(sql, params)

    results = []
    for r in rows:
        comp = calculate_job_compatibility(user, r)
        # Search filter
        if query:
            searchable = f"{r.get('title','')} {r.get('company_name','')} {r.get('description','')} {r.get('required_skills','')}".lower()
            if query not in searchable:
                continue

        results.append({
            **dict(r),
            "is_saved": bool(r["is_saved"]),
            "applied_status": r["applied_status"],
            "compatibility_score": comp["score"],
            "compatibility_explanation": comp["explanation"],
            "matched_skills": comp["matched_skills"],
            "missing_skills": comp["missing_skills"]
        })

    results.sort(key=lambda x: x["compatibility_score"], reverse=True)
    return jsonify({"status": "success", "count": len(results), "jobs": results})


@candidate_bp.route("/jobs/<int:job_id>/save", methods=["POST", "DELETE"])
@login_required(roles="candidate")
def toggle_save_job(job_id):
    user_id = session["user_id"]
    if request.method == "POST":
        execute_db("INSERT OR IGNORE INTO saved_jobs (candidate_id, job_id) VALUES (?, ?)", (user_id, job_id))
        return jsonify({"status": "success", "message": "Job bookmarked to saved jobs.", "is_saved": True})
    else:
        execute_db("DELETE FROM saved_jobs WHERE candidate_id = ? AND job_id = ?", (user_id, job_id))
        return jsonify({"status": "success", "message": "Job removed from saved jobs.", "is_saved": False})


@candidate_bp.route("/saved-jobs", methods=["GET"])
@login_required(roles="candidate")
def list_saved_jobs():
    user = get_current_user()
    user_id = user["id"]
    rows = query_db("""
        SELECT j.*, c.company_name, s.created_at as saved_at,
               (SELECT status FROM applications WHERE candidate_id = ? AND job_id = j.id) as applied_status
        FROM saved_jobs s
        JOIN jobs j ON s.job_id = j.id
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE s.candidate_id = ?
        ORDER BY s.created_at DESC
    """, (user_id, user_id))

    jobs = []
    for r in rows:
        comp = calculate_job_compatibility(user, r)
        jobs.append({
            **dict(r),
            "is_saved": True,
            "compatibility_score": comp["score"]
        })
    return jsonify({"status": "success", "count": len(jobs), "saved_jobs": jobs})


@candidate_bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required(roles="candidate")
def apply_job(job_id):
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json(silent=True) or {}
    cover_letter = str(data.get("cover_letter", "")).strip()

    job = query_db("SELECT * FROM jobs WHERE id = ?", (job_id,), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404
    if job.get("status") != "Open":
        return jsonify({"status": "error", "message": "This job is closed and no longer accepting applications."}), 400

    existing = query_db("SELECT id, status FROM applications WHERE job_id = ? AND candidate_id = ?", (job_id, user_id), one=True)
    if existing:
        return jsonify({
            "status": "error",
            "message": f"You have already applied for this role. Current status: {existing['status']}."
        }), 409

    comp = calculate_job_compatibility(user, job)
    resume_path = user.get("resume_path", "")

    res = execute_db("""
        INSERT INTO applications (job_id, candidate_id, resume_path, cover_letter, compatibility_score, status)
        VALUES (?, ?, ?, ?, ?, 'Applied')
    """, (job_id, user_id, resume_path, cover_letter, comp["score"]))

    app_id = res["lastrowid"]

    execute_db("""
        INSERT INTO application_status_history (application_id, old_status, new_status, changed_by, note)
        VALUES (?, NULL, 'Applied', ?, 'Application submitted by candidate.')
    """, (app_id, user_id))

    return jsonify({
        "status": "success",
        "message": "Application submitted successfully!",
        "application_id": app_id,
        "compatibility_score": comp["score"]
    }), 201


@candidate_bp.route("/applications", methods=["GET"])
@login_required(roles="candidate")
def get_applications():
    user_id = session["user_id"]
    apps = query_db("""
        SELECT a.*, j.title as job_title, j.location as job_location, j.employment_type,
               c.company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE a.candidate_id = ?
        ORDER BY a.applied_at DESC
    """, (user_id,))

    results = []
    for app in apps:
        history = query_db("""
            SELECT old_status, new_status, note, changed_at
            FROM application_status_history
            WHERE application_id = ?
            ORDER BY changed_at ASC
        """, (app["id"],))
        results.append({
            **dict(app),
            "status_history": [dict(h) for h in history]
        })

    return jsonify({"status": "success", "count": len(results), "applications": results})


@candidate_bp.route("/applications/<int:app_id>/withdraw", methods=["POST"])
@login_required(roles="candidate")
def withdraw_application(app_id):
    user_id = session["user_id"]
    app = query_db("SELECT * FROM applications WHERE id = ? AND candidate_id = ?", (app_id, user_id), one=True)
    if not app:
        return jsonify({"status": "error", "message": "Application not found."}), 404

    if app.get("status") in {"Withdrawn", "Rejected", "Selected"}:
        return jsonify({"status": "error", "message": f"Cannot withdraw an application that is already {app['status']}."}), 400

    execute_db("""
        UPDATE applications
        SET status = 'Withdrawn', withdrawn_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (app_id,))

    execute_db("""
        INSERT INTO application_status_history (application_id, old_status, new_status, changed_by, note)
        VALUES (?, ?, 'Withdrawn', ?, 'Application withdrawn by candidate.')
    """, (app_id, app["status"], user_id))

    return jsonify({"status": "success", "message": "Application withdrawn."})


@candidate_bp.route("/learning-paths", methods=["GET"])
@login_required(roles="candidate")
def get_learning_paths():
    user = get_current_user()
    user_id = user["id"]
    curr_occ = user.get("current_occupation") or "Data Analyst"
    transitions = get_career_transitions(curr_occ, candidate_skills=user.get("skills", []), top_n=3)

    # Fetch candidate tracked progress
    progress_rows = query_db("SELECT * FROM user_learning_progress WHERE user_id = ?", (user_id,))
    progress_map = {r["skill"].lower(): r["status"] for r in progress_rows}

    # Aggregate missing skills across transitions
    missing_skills = set()
    for t in transitions:
        for s in t.get("skills", []):
            missing_skills.add(s["skill"])

    courses = get_verified_courses_for_skills(list(missing_skills))

    return jsonify({
        "status": "success",
        "current_occupation": curr_occ,
        "transitions": transitions,
        "verified_courses": courses,
        "user_progress": progress_map
    })


@candidate_bp.route("/learning-progress", methods=["POST"])
@login_required(roles="candidate")
def update_learning_progress():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    skill = str(data.get("skill", "")).strip()
    status = str(data.get("status", "In Progress")).strip()

    if not skill:
        return jsonify({"status": "error", "message": "Skill name is required."}), 400
    if status not in {"Not Started", "In Progress", "Completed"}:
        return jsonify({"status": "error", "message": "Invalid learning status."}), 400

    completed_at = datetime.now() if status == "Completed" else None

    execute_db("""
        INSERT INTO user_learning_progress (user_id, skill, status, completed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, skill) DO UPDATE SET
            status = excluded.status,
            completed_at = excluded.completed_at
    """, (user_id, skill, status, completed_at))

    return jsonify({"status": "success", "message": f"Updated '{skill}' status to {status}."})


@candidate_bp.route("/assessment", methods=["GET", "POST"])
@login_required(roles="candidate")
def career_assessment():
    user = get_current_user()
    user_id = user["id"]

    if request.method == "GET":
        latest = query_db("""
            SELECT * FROM career_assessments
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,), one=True)
        return jsonify({
            "status": "success",
            "has_assessment": bool(latest),
            "assessment": dict(latest) if latest else None
        })

    # POST submit answers
    data = request.get_json(silent=True) or {}
    responses = data.get("responses", {})
    if not responses:
        return jsonify({"status": "error", "message": "Assessment responses required."}), 400

    # Categorize interests: Analytical vs Creative vs Technical vs Leadership
    strengths = []
    if responses.get("q_problem_solving") == "data":
        strengths.append("Quantitative Analysis")
    if responses.get("q_work_style") == "independent":
        strengths.append("Deep Focus & Research")
    if responses.get("q_interests") == "ai":
        strengths.append("Machine Learning & Algorithms")
    if not strengths:
        strengths = ["Structured Problem Solving", "Analytical Thinking"]

    cluster = "Data Science & Advanced Analytics"

    res = execute_db("""
        INSERT INTO career_assessments (user_id, responses_json, strengths_json, recommended_cluster)
        VALUES (?, ?, ?, ?)
    """, (user_id, json.dumps(responses), json.dumps(strengths), cluster))

    return jsonify({
        "status": "success",
        "message": "Career assessment completed.",
        "assessment_id": res["lastrowid"],
        "strengths": strengths,
        "recommended_cluster": cluster
    })
