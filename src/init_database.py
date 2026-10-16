from database import get_connection, get_database_path


# ============================================================
# SKILLBRIDGE AI
# DATABASE INITIALIZATION
# ============================================================

def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    print("=" * 70)
    print("SKILLBRIDGE AI DATABASE INITIALIZATION")
    print("=" * 70)

    # ========================================================
    # 1. USERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            location TEXT,

            education TEXT,

            experience INTEGER,

            current_occupation TEXT NOT NULL,

            career_interest TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    print("✓ users table ready")


    # ========================================================
    # 2. USER SKILLS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            skill TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)

    print("✓ user_skills table ready")


    # ========================================================
    # 3. OCCUPATIONS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS occupations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            occupation_code TEXT UNIQUE,

            occupation_name TEXT NOT NULL,

            isco_group TEXT,

            description TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    print("✓ occupations table ready")


    # ========================================================
    # 4. SKILLS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            skill_uri TEXT UNIQUE,

            skill_name TEXT NOT NULL,

            skill_type TEXT,

            description TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    print("✓ skills table ready")


    # ========================================================
    # 5. OCCUPATION-SKILL RELATIONSHIPS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS occupation_skills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            occupation_id INTEGER NOT NULL,

            skill_id INTEGER NOT NULL,

            relation_type TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (occupation_id)
                REFERENCES occupations(id)
                ON DELETE CASCADE,

            FOREIGN KEY (skill_id)
                REFERENCES skills(id)
                ON DELETE CASCADE,

            UNIQUE (
                occupation_id,
                skill_id,
                relation_type
            )

        )
    """)

    print("✓ occupation_skills table ready")


    # ========================================================
    # 6. RECOMMENDATIONS
    # ========================================================

    cursor.execute("""
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

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)

    print("✓ recommendations table ready")


    # ========================================================
    # 7. USER LEARNING PROGRESS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_learning_progress (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            skill TEXT NOT NULL,

            priority TEXT,

            difficulty TEXT,

            status TEXT DEFAULT 'Not Started',

            completed_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)

    print("✓ user_learning_progress table ready")


    # ========================================================
    # INDEXES
    # ========================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_skills_user_id
        ON user_skills(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_recommendations_user_id
        ON recommendations(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_progress_user_id
        ON user_learning_progress(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_occupation_skills_occupation
        ON occupation_skills(occupation_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_occupation_skills_skill
        ON occupation_skills(skill_id)
    """)

    print("✓ indexes created")


    # ========================================================
    # SAVE DATABASE
    # ========================================================

    connection.commit()

    connection.close()

    print()
    print("=" * 70)
    print("DATABASE CREATED SUCCESSFULLY")
    print("=" * 70)

    print(f"Database:")
    print(get_database_path())

    print()
    print("Tables created:")
    print("  1. users")
    print("  2. user_skills")
    print("  3. occupations")
    print("  4. skills")
    print("  5. occupation_skills")
    print("  6. recommendations")
    print("  7. user_learning_progress")

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    create_tables()