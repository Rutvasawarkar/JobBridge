import os
import json
import sqlite3
import pandas as pd
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "skillbridge.db"


def get_connection():
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def seed_occupations_and_skills(conn):
    print("Loading occupations and skills from datasets...")
    
    ai_exp_path = DATA_DIR / "ai_explanations.csv"
    learn_path = DATA_DIR / "learning_pathways.csv"
    
    occupations_set = set()
    skills_set = set()
    occ_skills_list = []
    
    if ai_exp_path.exists():
        df_exp = pd.read_csv(ai_exp_path, low_memory=False)
        for _, r in df_exp.iterrows():
            curr = str(r.get("current_occupation", "")).strip()
            curr_code = str(r.get("current_occupation_code", "")).strip()
            target = str(r.get("target_occupation", "")).strip()
            target_code = str(r.get("target_occupation_code", "")).strip()
            target_isco = str(r.get("target_isco3", "")).strip()
            expl = str(r.get("explanation", "")).strip()
            
            if curr:
                occupations_set.add((curr_code or None, curr, None, f"Standard occupation profile for {curr}."))
            if target:
                occupations_set.add((target_code or None, target, target_isco or None, expl or f"Standard occupation profile for {target}."))

    if learn_path.exists():
        df_learn = pd.read_csv(learn_path, low_memory=False)
        for _, r in df_learn.iterrows():
            target = str(r.get("target_occupation", "")).strip()
            skill = str(r.get("skillLabel", "")).strip()
            s_type = str(r.get("skillType", "knowledge")).strip()
            rel = str(r.get("relationType", "essential")).strip()
            if skill:
                skills_set.add((skill, s_type, f"{skill.capitalize()} relevant for career pathways."))
            if target and skill:
                occ_skills_list.append((target, skill, rel))

    print(f"  Found {len(occupations_set)} unique occupations and {len(skills_set)} unique skills.")

    occ_id_map = {}
    for code, name, isco, desc in occupations_set:
        try:
            existing = conn.execute("SELECT id FROM occupations WHERE occupation_name = ?", (name,)).fetchone()
            if existing:
                occ_id_map[name.lower()] = existing["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO occupations (occupation_code, occupation_name, isco_group, description)
                    VALUES (?, ?, ?, ?)
                """, (code, name, isco, desc))
                occ_id_map[name.lower()] = cur.lastrowid
        except Exception:
            pass

    skill_id_map = {}
    for name, s_type, desc in skills_set:
        try:
            existing = conn.execute("SELECT id FROM skills WHERE skill_name = ?", (name,)).fetchone()
            if existing:
                skill_id_map[name.lower()] = existing["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO skills (skill_uri, skill_name, skill_type, description)
                    VALUES (?, ?, ?, ?)
                """, (f"urn:skill:{name.lower().replace(' ', '_')}", name, s_type, desc))
                skill_id_map[name.lower()] = cur.lastrowid
        except Exception:
            pass

    inserted_rel = 0
    for occ_name, skill_name, rel in occ_skills_list:
        occ_id = occ_id_map.get(occ_name.lower())
        s_id = skill_id_map.get(skill_name.lower())
        if occ_id and s_id:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO occupation_skills (occupation_id, skill_id, relation_type)
                    VALUES (?, ?, ?)
                """, (occ_id, s_id, rel))
                inserted_rel += 1
            except Exception:
                pass

    print(f"  Inserted {len(occ_id_map)} occupations, {len(skill_id_map)} skills, and {inserted_rel} relationships.")


def seed_verified_courses(conn):
    print("Seeding verified, authentic free courses...")
    courses = [
        ("Python", "Harvard University (edX)", "CS50's Introduction to Programming with Python", 
         "https://cs50.harvard.edu/python/", 40.0, "Free", "None", "Beginner"),
        ("Python", "freeCodeCamp", "Scientific Computing with Python Certification", 
         "https://www.freecodecamp.org/learn/scientific-computing-with-python/", 50.0, "Free", "None", "Beginner"),
        ("Python", "Kaggle Learn", "Python for Data Analysis", 
         "https://www.kaggle.com/learn/python", 5.0, "Free", "None", "Beginner"),
        ("SQL", "Kaggle Learn", "Intro to SQL", 
         "https://www.kaggle.com/learn/intro-to-sql", 6.0, "Free", "None", "Beginner"),
        ("SQL", "Kaggle Learn", "Advanced SQL", 
         "https://www.kaggle.com/learn/advanced-sql", 8.0, "Free", "Intro to SQL", "Intermediate"),
        ("SQL", "freeCodeCamp", "Relational Database Certification", 
         "https://www.freecodecamp.org/learn/relational-database/", 80.0, "Free", "Basic CLI", "Intermediate"),
        ("Machine Learning", "Kaggle Learn", "Intro to Machine Learning", 
         "https://www.kaggle.com/learn/intro-to-machine-learning", 8.0, "Free", "Basic Python", "Beginner"),
        ("Machine Learning", "Kaggle Learn", "Intermediate Machine Learning", 
         "https://www.kaggle.com/learn/intermediate-machine-learning", 10.0, "Free", "Intro to ML", "Intermediate"),
        ("Machine Learning", "freeCodeCamp", "Machine Learning with Python Certification", 
         "https://www.freecodecamp.org/learn/machine-learning-with-python/", 60.0, "Free", "Python, Calculus", "Advanced"),
        ("Excel", "freeCodeCamp", "Microsoft Excel Tutorial for Beginners - Full Course", 
         "https://www.youtube.com/watch?v=Vl0H-qTclOg", 4.0, "Free", "None", "Beginner"),
        ("Data Analysis", "Kaggle Learn", "Pandas for Data Manipulation", 
         "https://www.kaggle.com/learn/pandas", 6.0, "Free", "Basic Python", "Beginner"),
        ("Data Analysis", "Kaggle Learn", "Data Visualization with Seaborn", 
         "https://www.kaggle.com/learn/data-visualization", 6.0, "Free", "Python", "Beginner"),
        ("HTML", "freeCodeCamp", "Responsive Web Design Certification", 
         "https://www.freecodecamp.org/learn/2022/responsive-web-design/", 60.0, "Free", "None", "Beginner"),
        ("CSS", "freeCodeCamp", "Responsive Web Design Certification", 
         "https://www.freecodecamp.org/learn/2022/responsive-web-design/", 60.0, "Free", "None", "Beginner"),
        ("JavaScript", "freeCodeCamp", "JavaScript Algorithms and Data Structures", 
         "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/", 80.0, "Free", "None", "Intermediate"),
        ("Communication", "Khan Academy", "Interpersonal Communication & Active Listening", 
         "https://www.khanacademy.org/college-careers-more/career-readiness", 8.0, "Free", "None", "Beginner"),
        ("Project Management", "OpenLearn (Open University)", "Project Management Principles", 
         "https://www.open.edu/openlearn/money-business/leadership-management/project-management/content-section-0", 12.0, "Free", "None", "Beginner"),
        ("Cybersecurity", "Cisco Networking Academy", "Introduction to Cybersecurity", 
         "https://www.netacad.com/courses/cybersecurity/introduction-cybersecurity", 15.0, "Free", "None", "Beginner")
    ]

    inserted = 0
    for skill, prov, title, url, hours, cost, prereq, diff in courses:
        existing = conn.execute("SELECT id FROM verified_courses WHERE title = ?", (title,)).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO verified_courses (
                    skill_name, provider, title, url, duration_hours, cost, prerequisites, difficulty, is_verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (skill, prov, title, url, hours, cost, prereq, diff))
            inserted += 1
    print(f"  Inserted {inserted} verified courses.")


def upsert_user(conn, email, data):
    row = conn.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
    if row:
        user_id = row["id"]
        set_clauses = ", ".join(f'"{k}" = ?' for k in data.keys())
        conn.execute(f'UPDATE users SET {set_clauses} WHERE id = ?', list(data.values()) + [user_id])
        return user_id
    else:
        cols = ", ".join(f'"{k}"' for k in data.keys())
        placeholders = ", ".join("?" for _ in data)
        cur = conn.execute(f'INSERT INTO users (email, {cols}) VALUES (?, {placeholders})', [email] + list(data.values()))
        return cur.lastrowid


def seed_demo_accounts_and_jobs(conn):
    print("Seeding demonstration accounts, jobs and applications...")
    
    # 1. Admin Account
    admin_id = upsert_user(conn, "admin@jobbridge.local", {
        "name": "Platform Admin",
        "full_name": "System Administrator",
        "password_hash": generate_password_hash("admin123"),
        "role": "admin",
        "current_occupation": "Platform Administrator",
        "headline": "Lead Platform Administrator",
        "bio": "Overseeing system operations and safety.",
        "onboarding_status": "completed",
        "onboarding_step": 6,
        "status": "active"
    })

    # 2. Recruiter Account & Company
    recruiter_id = upsert_user(conn, "recruiter@gmail.com", {
        "name": "Sarah Jenkins",
        "full_name": "Sarah Jenkins",
        "password_hash": generate_password_hash("recruiter123"),
        "role": "recruiter",
        "current_occupation": "Technical Recruiter",
        "headline": "Senior Technical Recruiter at DataNova",
        "bio": "Hiring top data & engineering talent.",
        "location": "Nagpur, India",
        "onboarding_status": "completed",
        "onboarding_step": 6,
        "status": "active"
    })

    company_row = conn.execute("SELECT id FROM companies WHERE user_id = ?", (recruiter_id,)).fetchone()
    if company_row:
        company_id = company_row["id"]
        conn.execute("""
            UPDATE companies
            SET company_name = ?, description = ?, website = ?, location = ?, industry = ?, company_size = ?, verified = 1
            WHERE id = ?
        """, (
            "DataNova Technologies",
            "Next-generation AI & data intelligence solutions delivering scalable data pipelines and analytics.",
            "https://datanova.example.com", "Nagpur, India", "Information Technology & AI", "50-200", company_id
        ))
    else:
        cur = conn.execute("""
            INSERT INTO companies (user_id, company_name, description, website, location, industry, company_size, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            recruiter_id, "DataNova Technologies",
            "Next-generation AI & data intelligence solutions delivering scalable data pipelines and analytics.",
            "https://datanova.example.com", "Nagpur, India", "Information Technology & AI", "50-200"
        ))
        company_id = cur.lastrowid

    # 3. Candidate Account
    candidate_id = upsert_user(conn, "user@gmail.com", {
        "name": "Alex Rivera",
        "full_name": "Alex Rivera",
        "password_hash": generate_password_hash("user123"),
        "role": "candidate",
        "phone": "+91 98765 43210",
        "location": "Nagpur, India",
        "education": "B.Tech in Computer Science, RCOEM",
        "experience": 2,
        "current_occupation": "Junior Data Analyst",
        "career_interest": "Data Scientist",
        "headline": "Aspiring Data Scientist | Python, SQL, Machine Learning",
        "bio": "Passionate data professional with 2 years of experience in data wrangling, analytics, and predictive modeling.",
        "onboarding_status": "completed",
        "onboarding_step": 6,
        "status": "active"
    })

    # Candidate skills
    candidate_skills = [
        ("Python", "Advanced", 2.5),
        ("SQL", "Advanced", 2.0),
        ("Excel", "Intermediate", 3.0),
        ("Data Analysis", "Advanced", 2.0),
        ("Machine Learning", "Beginner", 1.0)
    ]
    for skill, prof, yrs in candidate_skills:
        conn.execute("""
            INSERT OR IGNORE INTO user_skills (user_id, skill, proficiency, years_experience)
            VALUES (?, ?, ?, ?)
        """, (candidate_id, skill, prof, yrs))

    # Candidate learning progress
    conn.execute("""
        INSERT OR IGNORE INTO user_learning_progress (user_id, skill, priority, difficulty, status)
        VALUES (?, 'Machine Learning', 'High', 'Beginner', 'In Progress'),
               (?, 'Data Analysis', 'Medium', 'Beginner', 'Completed')
    """, (candidate_id, candidate_id))

    # 4. Jobs posted by DataNova
    conn.execute("DELETE FROM jobs WHERE recruiter_id = ?", (recruiter_id,))

    jobs_data = [
        ("Junior Data Scientist",
         "We are looking for a motivated Junior Data Scientist to analyze complex datasets, build predictive models, and partner with cross-functional product teams.",
         "Nagpur / Hybrid", "Full-time", 600000, 950000, "INR", 1, "Python, SQL, Machine Learning, Data Analysis", "Open"),
        ("Data Analyst",
         "Join our core analytics team to build production dashboards, automate reporting pipelines, and communicate actionable insights to stakeholders.",
         "Nagpur, India", "Full-time", 450000, 750000, "INR", 1, "SQL, Python, Excel, Data Analysis", "Open"),
        ("Frontend Developer",
         "Seeking a skilled frontend developer proficient in modern JavaScript, HTML5, and responsive styling to design accessible user interfaces.",
         "Remote", "Full-time", 500000, 800000, "INR", 2, "JavaScript, HTML, CSS", "Open"),
        ("ML Engineer Intern",
         "Summer internship for passionate students or freshers keen to learn production ML deployments and feature engineering.",
         "Pune / Remote", "Internship", 240000, 360000, "INR", 0, "Python, Machine Learning", "Open"),
        ("Lead Database Architect",
         "Lead database design, query optimization, and schema migrations across our cloud-native infrastructure.",
         "Nagpur, India", "Full-time", 1200000, 1800000, "INR", 5, "SQL, Database Management, Python", "Closed")
    ]

    job_ids = []
    for title, desc, loc, emp_type, s_min, s_max, curr, exp, skills, status in jobs_data:
        cur = conn.execute("""
            INSERT INTO jobs (
                recruiter_id, company_id, title, description, location, employment_type,
                salary_min, salary_max, salary_currency, experience_years_min, required_skills, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (recruiter_id, company_id, title, desc, loc, emp_type, s_min, s_max, curr, exp, skills, status))
        job_ids.append(cur.lastrowid)

    # 5. Candidate Application
    conn.execute("DELETE FROM applications WHERE candidate_id = ?", (candidate_id,))
    if job_ids:
        applied_job_id = job_ids[0]
        cur = conn.execute("""
            INSERT INTO applications (
                job_id, candidate_id, cover_letter, compatibility_score, status
            )
            VALUES (?, ?, ?, ?, 'Under Review')
        """, (applied_job_id, candidate_id, 
              "I am very excited to apply for the Junior Data Scientist position. My background in Python, SQL, and exploratory data analysis aligns well with your mission.",
              88.5))
        
        app_id = cur.lastrowid
        conn.execute("DELETE FROM application_status_history WHERE application_id = ?", (app_id,))
        conn.execute("""
            INSERT INTO application_status_history (application_id, old_status, new_status, changed_by, note)
            VALUES (?, 'Applied', 'Under Review', ?, 'Candidate profile reviewed and passed initial screening.')
        """, (app_id, recruiter_id))

        # Saved job
        conn.execute("DELETE FROM saved_jobs WHERE candidate_id = ?", (candidate_id,))
        if len(job_ids) > 1:
            conn.execute("""
                INSERT INTO saved_jobs (candidate_id, job_id)
                VALUES (?, ?)
            """, (candidate_id, job_ids[1]))

    # 6. Notifications
    conn.execute("DELETE FROM notifications WHERE user_id = ?", (candidate_id,))
    conn.execute("""
        INSERT INTO notifications (user_id, title, message, type, is_read)
        VALUES (?, 'Welcome to JobBridge!', 'Your profile has been created. Start exploring career transitions and verified learning courses.', 'system', 1),
               (?, 'Application Update', 'Your application for Junior Data Scientist at DataNova Technologies is now Under Review.', 'application', 0)
    """, (candidate_id, candidate_id))

    print("  Seed accounts, company, jobs, application, and notifications created successfully.")


def run_seeder():
    print("=" * 60)
    print("JOBBRIDGE DATABASE SEEDING")
    print("=" * 60)
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        seed_occupations_and_skills(conn)
        seed_verified_courses(conn)
        seed_demo_accounts_and_jobs(conn)
        conn.commit()
        print("\nAll seed operations committed successfully.")

        tables = ["users", "companies", "jobs", "applications", "occupations", "skills", "verified_courses", "notifications"]
        print("\nTable Row Counts:")
        for t in tables:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  - {t}: {cnt} rows")

    except Exception as e:
        conn.rollback()
        print("SEEDING FAILED! Rolled back. Error:", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_seeder()
