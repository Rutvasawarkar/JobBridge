from flask import Blueprint, request, jsonify, session
from database import query_db, execute_db
from app.services.auth_service import login_required

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notification_bp.route("", methods=["GET"])
@login_required()
def get_notifications():
    user_id = session["user_id"]
    notifs = query_db("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 30
    """, (user_id,))

    unread_cnt = query_db("""
        SELECT COUNT(*) as c FROM notifications
        WHERE user_id = ? AND is_read = 0
    """, (user_id,), one=True)["c"]

    return jsonify({
        "status": "success",
        "unread_count": unread_cnt,
        "notifications": [dict(n) for n in notifs]
    })


@notification_bp.route("/<int:notif_id>/read", methods=["PATCH"])
@login_required()
def mark_read(notif_id):
    user_id = session["user_id"]
    execute_db("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user_id))
    return jsonify({"status": "success", "message": "Notification marked as read."})


@notification_bp.route("/read-all", methods=["PATCH"])
@login_required()
def mark_all_read():
    user_id = session["user_id"]
    execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    return jsonify({"status": "success", "message": "All notifications marked as read."})
