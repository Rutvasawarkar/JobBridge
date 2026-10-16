from database import execute_db


def create_notification(user_id, title, message, notif_type="info"):
    """Persist an in-app notification for a user."""
    return execute_db("""
        INSERT INTO notifications (user_id, title, message, type, is_read)
        VALUES (?, ?, ?, ?, 0)
    """, (user_id, title, message, notif_type))
