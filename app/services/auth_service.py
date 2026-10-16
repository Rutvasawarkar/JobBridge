from functools import wraps
from flask import session, jsonify, request
from database import query_db


def get_current_user():
    """Fetch current authenticated user from session, verifying active status."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    user = query_db("""
        SELECT id, name, full_name, email, role, phone, location, education, experience,
               current_occupation, career_interest, headline, bio, onboarding_status,
               onboarding_step, status, resume_filename, resume_path, resume_updated_at, created_at
        FROM users
        WHERE id = ? AND status = 'active'
    """, (user_id,), one=True)

    if not user:
        session.clear()
        return None

    # Fetch user skills
    skills = query_db("SELECT skill, proficiency, years_experience FROM user_skills WHERE user_id = ? ORDER BY skill", (user_id,))
    user["skills"] = [dict(s) for s in skills]

    # If recruiter, attach company
    if user["role"] == "recruiter":
        comp = query_db("SELECT * FROM companies WHERE user_id = ?", (user_id,), one=True)
        user["company"] = dict(comp) if comp else None

    return user


def login_required(roles=None):
    """
    Decorator requiring authentication and optional role authorization.
    roles can be a string ('candidate') or list of strings (['recruiter', 'admin']).
    """
    if isinstance(roles, str):
        roles = [roles]

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({
                    "status": "error",
                    "code": "UNAUTHORIZED",
                    "message": "Please log in to access this resource."
                }), 401

            if roles and user["role"] not in roles:
                return jsonify({
                    "status": "error",
                    "code": "FORBIDDEN",
                    "message": f"Access denied. Requires role: {', '.join(roles)}."
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def onboarding_required(fn):
    """Decorator ensuring candidate has completed essential onboarding before dashboard."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Please log in."}), 401

        if user["role"] == "candidate" and user.get("onboarding_status") != "completed":
            return jsonify({
                "status": "error",
                "code": "ONBOARDING_REQUIRED",
                "message": "Please complete your initial profile onboarding first.",
                "onboarding_step": user.get("onboarding_step", 1)
            }), 403

        if user["role"] == "recruiter" and not user.get("company"):
            return jsonify({
                "status": "error",
                "code": "COMPANY_SETUP_REQUIRED",
                "message": "Please complete your company profile before publishing or managing jobs."
            }), 403

        return fn(*args, **kwargs)
    return wrapper
