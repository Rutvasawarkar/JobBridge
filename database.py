import sqlite3
from pathlib import Path

# ============================================================
# JOBBRIDGE - DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "skillbridge.db"


def get_connection():
    """Create a thread-safe connection with foreign keys and WAL mode."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=15
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def get_database_path():
    """Return the absolute path of the database file."""
    return DATABASE_PATH


def query_db(query, args=(), one=False):
    """Execute a read query and return dict or list of dicts."""
    with get_connection() as conn:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        if rv:
            return (dict(rv[0])) if one else [dict(r) for r in rv]
        return None if one else []


def execute_db(query, args=(), commit=True):
    """Execute an insert/update/delete query and return lastrowid / rowcount."""
    with get_connection() as conn:
        cur = conn.execute(query, args)
        if commit:
            conn.commit()
        last_id = cur.lastrowid
        row_count = cur.rowcount
        cur.close()
        return {"lastrowid": last_id, "rowcount": row_count}


if __name__ == "__main__":
    print("JobBridge database configuration")
    print("-" * 40)
    print("Project root:", BASE_DIR)
    print("Data directory:", DATA_DIR)
    print("Database path:", DATABASE_PATH)
    print("Database exists:", DATABASE_PATH.exists())

    with get_connection() as connection:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

    print("\nExisting database tables:")
    for table in tables:
        cnt = query_db(f'SELECT COUNT(*) as c FROM "{table["name"]}"', one=True)["c"]
        print(f"- {table['name']}: {cnt} rows")
