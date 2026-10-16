import os
import secrets
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import get_connection, get_database_path, query_db

BASE_DIR = Path(__file__).resolve().parent.parent


def get_persistent_secret_key():
    """Retrieve secret key from env or persistent file in data/ so sessions survive server restarts."""
    env_key = os.environ.get("JOBBRIDGE_SECRET_KEY")
    if env_key:
        return env_key

    key_file = BASE_DIR / "data" / ".session_secret"
    if key_file.exists():
        try:
            return key_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Generate and persist
    new_key = secrets.token_hex(32)
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(new_key, encoding="utf-8")
    except Exception:
        pass
    return new_key


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static")
    )

    app.config["SECRET_KEY"] = get_persistent_secret_key()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("JOBBRIDGE_HTTPS", "0") == "1"
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max request payload

    CORS(app, supports_credentials=True)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.candidate_routes import candidate_bp
    from app.routes.recruiter_routes import recruiter_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.recommendation_routes import recommendation_bp
    from app.routes.notification_routes import notification_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(notification_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "success",
            "message": "JobBridge backend is healthy and running.",
            "version": "2.0.0"
        })

    @app.route("/api/database-status", methods=["GET"])
    def database_status():
        try:
            with get_connection() as conn:
                tables = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """).fetchall()
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

            counts = {}
            for t in tables:
                row = query_db(f'SELECT COUNT(*) as c FROM "{t["name"]}"', one=True)
                counts[t["name"]] = row["c"] if row else 0

            return jsonify({
                "status": "success",
                "database_path": str(get_database_path()),
                "integrity": integrity,
                "table_count": len(tables),
                "row_counts": counts
            })
        except Exception as e:
            app.logger.exception("Database status check failed")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": f"Endpoint not found: {request.path}"}), 404
        return render_template("index.html")

    @app.errorhandler(500)
    def handle_server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500

    return app
