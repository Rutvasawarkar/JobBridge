import re
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db
from app.services.auth_service import get_current_user, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", "candidate")).strip().lower()

    if not name:
        return jsonify({"status": "error", "message": "Full name is required."}), 400
    if len(name) > 120:
        return jsonify({"status": "error", "message": "Name must be 120 characters or fewer."}), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"status": "error", "message": "Enter a valid email address."}), 400

    if len(password) < 8:
        return jsonify({"status": "error", "message": "Password must contain at least 8 characters."}), 400

    # Public registration can only create candidate or recruiter accounts
    if role not in {"candidate", "recruiter"}:
        return jsonify({"status": "error", "message": "Invalid account role. Administrator accounts must be provisioned."}), 400

    # Check email duplicate
    existing = query_db("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,), one=True)
    if existing:
        return jsonify({"status": "error", "message": "An account with this email already exists."}), 409

    pw_hash = generate_password_hash(password)
    default_occ = "Not specified" if role == "candidate" else "Recruiter"

    res = execute_db("""
        INSERT INTO users (
            name, full_name, email, password_hash, role, current_occupation,
            onboarding_status, onboarding_step, status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, 'active')
    """, (name, name, email, pw_hash, role, default_occ))

    user_id = res["lastrowid"]

    # If recruiter, initialize company stub
    if role == "recruiter":
        execute_db("""
            INSERT OR IGNORE INTO companies (user_id, company_name)
            VALUES (?, ?)
        """, (user_id, f"{name}'s Company"))

    session.clear()
    session["user_id"] = user_id
    session["role"] = role

    user = get_current_user()
    return jsonify({
        "status": "success",
        "message": "Account created successfully. Please complete your profile onboarding.",
        "user": user
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    requested_role = str(data.get("role", "")).strip().lower()

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    user_row = query_db("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,), one=True)
    if not user_row or not user_row.get("password_hash") or not check_password_hash(user_row["password_hash"], password):
        return jsonify({"status": "error", "message": "Invalid email or password."}), 401

    if user_row.get("status") != "active":
        return jsonify({
            "status": "error",
            "message": "Your account has been suspended. Please contact platform administration."
        }), 403

    actual_role = user_row.get("role", "candidate")

    # If role was requested and user is not admin, verify role matches
    if requested_role and actual_role != "admin" and actual_role != requested_role:
        return jsonify({
            "status": "error",
            "message": f"This account is registered as a {actual_role}. Please select the {actual_role} login tab."
        }), 403

    session.clear()
    session["user_id"] = user_row["id"]
    session["role"] = actual_role

    user = get_current_user()
    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": user
    })


@auth_bp.route("/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"status": "success", "authenticated": False, "user": None})
    return jsonify({"status": "success", "authenticated": True, "user": user})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})
