import sqlite3
from pathlib import Path

from flask import request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# SKILLBRIDGE AI - AUTHENTICATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "skillbridge.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_auth_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ============================================================
# REGISTER
# POST /api/register
# ============================================================

def register():

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data received."
            }), 400

        # ----------------------------------------------------
        # GET DATA
        # ----------------------------------------------------

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        location = str(data.get("location", "")).strip()
        education = str(data.get("education", "")).strip()

        experience = data.get("experience", 0)

        current_occupation = str(
            data.get("current_occupation", "")
        ).strip()

        career_interest = str(
            data.get("career_interest", "")
        ).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name:
            return jsonify({
                "status": "error",
                "message": "Name is required."
            }), 400

        if not email:
            return jsonify({
                "status": "error",
                "message": "Email is required."
            }), 400

        if not password:
            return jsonify({
                "status": "error",
                "message": "Password is required."
            }), 400

        if len(password) < 6:
            return jsonify({
                "status": "error",
                "message": "Password must contain at least 6 characters."
            }), 400

        # Existing database requires current_occupation.
        if not current_occupation:
            current_occupation = "Not specified"

        # ----------------------------------------------------
        # EXPERIENCE
        # ----------------------------------------------------

        try:
            experience = int(experience)

            if experience < 0:
                experience = 0

        except (ValueError, TypeError):

            experience = 0

        # ----------------------------------------------------
        # CONNECT DATABASE
        # ----------------------------------------------------

        connection = get_auth_connection()

        # ----------------------------------------------------
        # CHECK EMAIL
        # ----------------------------------------------------

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            connection.close()

            return jsonify({
                "status": "error",
                "message": "An account with this email already exists."
            }), 409

        # ----------------------------------------------------
        # HASH PASSWORD
        # ----------------------------------------------------

        password_hash = generate_password_hash(password)

        # ----------------------------------------------------
        # INSERT USER
        # ----------------------------------------------------

        cursor = connection.execute(
            """
            INSERT INTO users (
                name,
                location,
                education,
                experience,
                current_occupation,
                career_interest,
                email,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                location,
                education,
                experience,
                current_occupation,
                career_interest,
                email,
                password_hash
            )
        )

        user_id = cursor.lastrowid

        connection.commit()
        connection.close()

        # ----------------------------------------------------
        # LOGIN USER IMMEDIATELY
        # ----------------------------------------------------

        session.clear()
        session["user_id"] = user_id

        return jsonify({
            "status": "success",
            "message": "Account created successfully.",
            "user": {
                "id": user_id,
                "name": name,
                "email": email
            }
        }), 201

    except sqlite3.IntegrityError:

        return jsonify({
            "status": "error",
            "message": "Could not create account. Email may already exist."
        }), 409

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": "Registration failed.",
            "details": str(e)
        }), 500


# ============================================================
# LOGIN
# POST /api/login
# ============================================================

def login():

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON data received."
            }), 400

        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not email or not password:

            return jsonify({
                "status": "error",
                "message": "Email and password are required."
            }), 400

        # ----------------------------------------------------
        # FIND USER
        # ----------------------------------------------------

        connection = get_auth_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if not user:

            return jsonify({
                "status": "error",
                "message": "Invalid email or password."
            }), 401

        # ----------------------------------------------------
        # CHECK PASSWORD
        # ----------------------------------------------------

        if not user["password_hash"]:

            return jsonify({
                "status": "error",
                "message": "This account does not have a valid password."
            }), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return jsonify({
                "status": "error",
                "message": "Invalid email or password."
            }), 401

        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session.clear()
        session["user_id"] = user["id"]

        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": "Login failed.",
            "details": str(e)
        }), 500


# ============================================================
# CURRENT USER
# GET /api/me
# ============================================================

def current_user():

    try:

        user_id = session.get("user_id")

        if not user_id:

            return jsonify({
                "status": "success",
                "logged_in": False,
                "user": None
            }), 200

        connection = get_auth_connection()

        user = connection.execute(
            """
            SELECT
                id,
                name,
                email,
                location,
                education,
                experience,
                current_occupation,
                career_interest,
                created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        connection.close()

        if not user:

            session.clear()

            return jsonify({
                "status": "success",
                "logged_in": False,
                "user": None
            }), 200

        return jsonify({
            "status": "success",
            "logged_in": True,
            "user": dict(user)
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": "Could not retrieve user.",
            "details": str(e)
        }), 500


# ============================================================
# LOGOUT
# POST /api/logout
# ============================================================

def logout():

    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    }), 200


# ============================================================
# UPDATE PROFILE
# PUT /api/profile
# ============================================================

def update_profile():

    try:

        user_id = session.get("user_id")

        if not user_id:

            return jsonify({
                "status": "error",
                "message": "You must be logged in."
            }), 401

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "status": "error",
                "message": "No JSON data received."
            }), 400

        # ----------------------------------------------------
        # READ DATA
        # ----------------------------------------------------

        name = str(data.get("name", "")).strip()
        location = str(data.get("location", "")).strip()
        education = str(data.get("education", "")).strip()
        current_occupation = str(
            data.get("current_occupation", "")
        ).strip()

        career_interest = str(
            data.get("career_interest", "")
        ).strip()

        experience = data.get("experience", 0)

        try:
            experience = int(experience)

            if experience < 0:
                experience = 0

        except (ValueError, TypeError):

            experience = 0

        if not name:

            return jsonify({
                "status": "error",
                "message": "Name is required."
            }), 400

        if not current_occupation:

            current_occupation = "Not specified"

        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        connection = get_auth_connection()

        connection.execute(
            """
            UPDATE users
            SET
                name = ?,
                location = ?,
                education = ?,
                experience = ?,
                current_occupation = ?,
                career_interest = ?
            WHERE id = ?
            """,
            (
                name,
                location,
                education,
                experience,
                current_occupation,
                career_interest,
                user_id
            )
        )

        connection.commit()
        connection.close()

        return jsonify({
            "status": "success",
            "message": "Profile updated successfully."
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": "Profile update failed.",
            "details": str(e)
        }), 500


# ============================================================
# REGISTER ROUTES WITH EXISTING FLASK APP
# ============================================================

def register_auth_routes(app):

    app.add_url_rule(
        "/api/register",
        "register",
        register,
        methods=["POST"]
    )

    app.add_url_rule(
        "/api/login",
        "login",
        login,
        methods=["POST"]
    )

    app.add_url_rule(
        "/api/me",
        "current_user",
        current_user,
        methods=["GET"]
    )

    app.add_url_rule(
        "/api/logout",
        "logout",
        logout,
        methods=["POST"]
    )

    app.add_url_rule(
        "/api/profile",
        "update_profile",
        update_profile,
        methods=["PUT"]
    )