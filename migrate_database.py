import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "skillbridge.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE_PATH), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def get_columns(connection, table_name):
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row["name"] for row in rows}


def add_column_if_missing(connection, table_name, column_name, column_def):
    cols = get_columns(connection, table_name)
    if column_name not in cols:
        connection.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_def}')
        print(f"  + Added column {table_name}.{column_name}")
    else:
        print(f"  - Column {table_name}.{column_name} exists")


def run_migration():
    print("=" * 60)
    print("MIGRATING JOBBRIDGE DATABASE")
    print(f"Target: {DATABASE_PATH}")
    print("=" * 60)

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")

        # 1. USERS TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'candidate' CHECK (role IN ('candidate', 'recruiter', 'admin')),
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                education TEXT DEFAULT '',
                experience INTEGER DEFAULT 0,
                current_occupation TEXT DEFAULT 'Not specified',
                career_interest TEXT DEFAULT '',
                headline TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                onboarding_status TEXT NOT NULL DEFAULT 'pending' CHECK (onboarding_status IN ('pending', 'completed')),
                onboarding_step INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
                resume_filename TEXT DEFAULT '',
                resume_path TEXT DEFAULT '',
                resume_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add missing columns if users table existed previously
        add_column_if_missing(connection, "users", "phone", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "users", "headline", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "users", "bio", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "users", "onboarding_status", "TEXT NOT NULL DEFAULT 'pending'")
        add_column_if_missing(connection, "users", "onboarding_step", "INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(connection, "users", "status", "TEXT NOT NULL DEFAULT 'active'")
        add_column_if_missing(connection, "users", "resume_filename", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "users", "resume_path", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "users", "resume_updated_at", "TIMESTAMP")

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
            ON users(email COLLATE NOCASE)
            WHERE email IS NOT NULL AND TRIM(email) <> ''
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")

        # 2. COMPANIES TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                company_name TEXT NOT NULL,
                description TEXT DEFAULT '',
                website TEXT DEFAULT '',
                location TEXT DEFAULT '',
                industry TEXT DEFAULT '',
                company_size TEXT DEFAULT '1-10',
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        add_column_if_missing(connection, "companies", "industry", "TEXT DEFAULT ''")
        add_column_if_missing(connection, "companies", "company_size", "TEXT DEFAULT '1-10'")
        add_column_if_missing(connection, "companies", "verified", "INTEGER DEFAULT 0")

        # 3. JOBS TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recruiter_id INTEGER NOT NULL,
                company_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT DEFAULT '',
                employment_type TEXT DEFAULT 'Full-time',
                salary_min REAL,
                salary_max REAL,
                salary_currency TEXT DEFAULT 'INR',
                experience_years_min INTEGER DEFAULT 0,
                required_skills TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Draft', 'Open', 'Closed', 'Cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recruiter_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
            )
        """)
        add_column_if_missing(connection, "jobs", "salary_currency", "TEXT DEFAULT 'INR'")
        add_column_if_missing(connection, "jobs", "experience_years_min", "INTEGER DEFAULT 0")

        connection.execute("CREATE INDEX IF NOT EXISTS idx_jobs_recruiter ON jobs(recruiter_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")

        # 4. APPLICATIONS TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                resume_path TEXT DEFAULT '',
                cover_letter TEXT DEFAULT '',
                compatibility_score REAL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'Applied' CHECK (status IN ('Applied', 'Under Review', 'Shortlisted', 'Selected', 'Rejected', 'Withdrawn')),
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                withdrawn_at TIMESTAMP,
                UNIQUE (job_id, candidate_id),
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        add_column_if_missing(connection, "applications", "compatibility_score", "REAL DEFAULT 0.0")
        add_column_if_missing(connection, "applications", "withdrawn_at", "TIMESTAMP")

        connection.execute("CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id)")

        # 5. APPLICATION STATUS HISTORY
        connection.execute("""
            CREATE TABLE IF NOT EXISTS application_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by INTEGER,
                note TEXT DEFAULT '',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
                FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_app_history_app_id ON application_status_history(application_id)")

        # 6. SAVED JOBS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (candidate_id, job_id),
                FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)

        # 7. OCCUPATIONS TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS occupations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occupation_code TEXT UNIQUE,
                occupation_name TEXT NOT NULL,
                isco_group TEXT,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_occupations_name ON occupations(occupation_name COLLATE NOCASE)")

        # 8. SKILLS TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_uri TEXT UNIQUE,
                skill_name TEXT NOT NULL,
                skill_type TEXT DEFAULT 'skill/competence',
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(skill_name COLLATE NOCASE)")

        # 9. OCCUPATION SKILLS RELATIONSHIPS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS occupation_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occupation_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                relation_type TEXT DEFAULT 'essential',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (occupation_id) REFERENCES occupations(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
                UNIQUE (occupation_id, skill_id, relation_type)
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_occ_skills_occ ON occupation_skills(occupation_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_occ_skills_skill ON occupation_skills(skill_id)")

        # 10. USER SKILLS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                skill TEXT NOT NULL,
                proficiency TEXT DEFAULT 'Intermediate' CHECK (proficiency IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),
                years_experience REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, skill)
            )
        """)
        add_column_if_missing(connection, "user_skills", "proficiency", "TEXT DEFAULT 'Intermediate'")
        add_column_if_missing(connection, "user_skills", "years_experience", "REAL DEFAULT 1.0")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_user_skills_user ON user_skills(user_id)")

        # 11. VERIFIED COURSES TABLE
        connection.execute("""
            CREATE TABLE IF NOT EXISTS verified_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                duration_hours REAL DEFAULT 0,
                cost TEXT DEFAULT 'Free',
                prerequisites TEXT DEFAULT 'None',
                difficulty TEXT DEFAULT 'Beginner',
                is_verified INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_courses_skill ON verified_courses(skill_name COLLATE NOCASE)")

        # 12. USER LEARNING PROGRESS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                skill TEXT NOT NULL,
                course_id INTEGER,
                priority TEXT DEFAULT 'High',
                difficulty TEXT DEFAULT 'Beginner',
                status TEXT NOT NULL DEFAULT 'Not Started' CHECK (status IN ('Not Started', 'In Progress', 'Completed')),
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES verified_courses(id) ON DELETE SET NULL,
                UNIQUE (user_id, skill)
            )
        """)
        add_column_if_missing(connection, "user_learning_progress", "course_id", "INTEGER")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_learning_user ON user_learning_progress(user_id)")

        # 13. CAREER ASSESSMENTS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS career_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                responses_json TEXT NOT NULL,
                strengths_json TEXT DEFAULT '[]',
                recommended_cluster TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_assessment_user ON career_assessments(user_id)")

        # 14. IN-APP NOTIFICATIONS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)")

        # 15. AUDIT LOGS
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER,
                details TEXT DEFAULT '',
                ip_address TEXT DEFAULT '127.0.0.1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")

        # 16. RECOMMENDATIONS CACHE / HISTORY
        connection.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                current_occupation TEXT,
                target_occupation TEXT,
                current_occupation_code TEXT,
                target_occupation_code TEXT,
                match_score REAL,
                skill_similarity REAL,
                common_skill_count INTEGER,
                missing_skill_count INTEGER,
                target_skill_count INTEGER,
                skill_gap_score REAL,
                transition_score REAL,
                personalized_score REAL,
                personalized_level TEXT,
                recommendation_rank INTEGER,
                recommendation_reason TEXT,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        connection.commit()
        print("\nMigration successfully committed.")

        # Check integrity
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        print("Integrity check:", integrity)

        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            print("Foreign key warnings:", fk_errors)
        else:
            print("Foreign keys valid.")

        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        print(f"Total tables: {len(tables)}")
        for t in tables:
            print(f"  * {t['name']}")

    except Exception as e:
        connection.rollback()
        print("MIGRATION FAILED! Rolled back. Error:", e)
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    run_migration()
