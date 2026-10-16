import sqlite3
from pathlib import Path


# ============================================================
# SKILLBRIDGE AI
# USER DATABASE MIGRATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "skillbridge.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def get_columns(connection, table_name):
    """Return existing column names for a table."""

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {row["name"] for row in rows}


def add_column_if_missing(connection, table_name, column_name, column_definition):
    """Add a column only if it doesn't already exist."""

    columns = get_columns(connection, table_name)

    if column_name not in columns:

        connection.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {column_definition}"
        )

        print(f"✓ Added column: {table_name}.{column_name}")

    else:

        print(f"✓ Already exists: {table_name}.{column_name}")


def create_user_tables():

    connection = get_connection()

    try:

        # ====================================================
        # USERS TABLE
        # ====================================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)

        # Add required user columns to the existing table
        add_column_if_missing(
            connection,
            "users",
            "full_name",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "email",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "password_hash",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "location",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "education",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "experience",
            "INTEGER DEFAULT 0"
        )

        add_column_if_missing(
            connection,
            "users",
            "current_occupation",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "career_interest",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "users",
            "created_at",
            "TIMESTAMP"
        )

        # ====================================================
        # UNIQUE EMAIL INDEX
        # ====================================================

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_users_email
            ON users(email)
            WHERE email IS NOT NULL
        """)

        print("✓ Email index ready")

        # ====================================================
        # USER SKILLS TABLE
        # ====================================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                skill TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        print("✓ user_skills table ready")

        # ====================================================
        # USER SKILLS INDEX
        # ====================================================

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_user_skills_user_id
            ON user_skills(user_id)
        """)

        # ====================================================
        # SAVE
        # ====================================================

        connection.commit()

        print()
        print("=" * 70)
        print("USER DATABASE MIGRATION COMPLETED")
        print("=" * 70)
        print()
        print("Database:")
        print(DATABASE_PATH)
        print()

    except Exception as e:

        connection.rollback()

        print()
        print("=" * 70)
        print("DATABASE MIGRATION FAILED")
        print("=" * 70)
        print()
        print(str(e))
        print()

    finally:

        connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SKILLBRIDGE AI - USER DATABASE SETUP")
    print("=" * 70)
    print()

    create_user_tables()