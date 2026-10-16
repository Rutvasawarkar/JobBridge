from flask import request
from database import execute_db


def log_audit(actor_id, action, target_type, target_id=None, details=""):
    """Record an auditable action performed by an actor (e.g. admin or recruiter)."""
    ip_addr = request.remote_addr if request else "127.0.0.1"
    return execute_db("""
        INSERT INTO audit_logs (actor_id, action, target_type, target_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (actor_id, action, target_type, target_id, details, ip_addr))
