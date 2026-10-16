# JobBridge — AI-Assisted Career Transition & Recruitment Platform

JobBridge is an integrated, full-stack career development, skill-gap analysis, career-readiness, and recruitment platform.

Designed and rebuilt for local-first execution, it provides three distinct role-based portals:
1. **Candidate Portal:** Multi-step onboarding, explainable occupational career transitions, transparent Career-Readiness Score (v1.0), verified free learning courses, job search with compatibility matching, resume upload/download, and a grounded AI career assistant.
2. **Recruiter Portal:** Company onboarding, job publishing & lifecycle management (Open, Closed, Cancelled), candidate review pipeline with compatibility scores, and auditable status decisions.
3. **Platform Administrator Portal:** Dedicated `/admin` console for user moderation, job moderation, platform metrics, and security audit logs.

---

## 1. Quick Start Guide (Windows / PowerShell)

### Step 1: Open PowerShell and Navigate to the Project
```powershell
cd "C:\Users\Hp\JobBridge"
```

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell execution policies restrict script activation, you can run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

### Step 3: Run Database Migrations (Pre-configured)
The database has already been migrated and structured with Write-Ahead Logging (WAL) and foreign key constraints:
```powershell
python migrate_database.py
```

### Step 4: Seed Realistic Demonstration Data (Optional / Repeatable)
Populates 692 standardized occupations, 2,961 skills, 5,043 relationships, 17 verified free learning courses, and realistic demo accounts:
```powershell
python seed_data.py
```

### Step 5: Start the JobBridge Backend
```powershell
python api.py
```
Output:
```
============================================================
JOBBRIDGE - INTEGRATED AI CAREER & RECRUITMENT PLATFORM
============================================================
Server URL: http://127.0.0.1:5000/
Health API: http://127.0.0.1:5000/api/health
DB Status:  http://127.0.0.1:5000/api/database-status
============================================================
```

Open your browser and navigate to: **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## 2. Pre-Configured Demonstration Accounts

| Role | Email | Password | Features Accessible |
| :--- | :--- | :--- | :--- |
| **Candidate** | `user@gmail.com` | `user123` | Dashboard, Transitions, Readiness Score, Courses, Jobs, Applications, Resume, AI Assistant |
| **Recruiter** | `recruiter@gmail.com` | `recruiter123` | Company Setup, Job Management, Applicant Review, Hiring Status Decisions, Analytics |
| **Administrator** | `admin@jobbridge.local` | `admin123` | Platform Metrics, User Moderation (Suspend/Activate), Job Moderation, Audit Logs |

*New candidates and recruiters can also register directly via the portal.*

---

## 3. Automated Test Suite

JobBridge includes a complete automated test suite verifying authentication, role boundaries, recruitment workflows, recommendation algorithms, readiness scoring, and administrative audit logging.

To run the full test suite:
```powershell
python run_tests.py
```

Expected Output:
```
=================================================================
JOBBRIDGE AUTOMATED TEST SUITE (UNITTEST / BUILT-IN RUNNER)
=================================================================

--- Suite: Authentication & Roles ---
  [PASS] test_candidate_onboarding_persistence
  [PASS] test_login_and_session_restoration
  [PASS] test_registration_and_password_hashing
  [PASS] test_role_enforcement

--- Suite: Recruitment & Applications ---
  [PASS] test_job_application_and_duplicate_prevention
  [PASS] test_recruiter_job_management

--- Suite: Recommendations & Readiness ---
  [PASS] test_analyze_api
  [PASS] test_career_readiness_scoring
  [PASS] test_job_compatibility
  [PASS] test_skill_overlap_calculation

--- Suite: Administration & Security ---
  [PASS] test_admin_metrics_and_user_moderation

=================================================================
TEST RUN SUMMARY: 11 tests run
PASSED: 11 | FAILED: 0
=================================================================

ALL TESTS PASSED SUCCESSFULLY! 100% PASS RATE.
```

---

## 4. Key Architectural Features

### 4.1 Transparent Career-Readiness Score (v1.0)
Calculated deterministically without unvalidated black-box classifiers:
$$\text{Readiness} = (\text{Essential Skill Match} \times 0.50) + (\text{Proficiency Depth} \times 0.20) + (\text{Experience Match} \times 0.15) + (\text{Learning Pathway Progress} \times 0.15)$$
- Explains exactly what features contributed to the score.
- Displays actionable advice on how to raise the score (e.g. completing courses, building experience).

### 4.2 Candidate-to-Job Compatibility Score
Calculates compatibility between candidate profile and recruiter job requirements:
- **Skill Overlap (65%):** Jaccard overlap between required skills and candidate skills.
- **Experience Alignment (20%):** Candidate years vs minimum job criteria.
- **Location Compatibility (15%):** Candidate location vs role location or remote mode.

### 4.3 Verified Free Learning Pathways
Maps missing skills to authentic, free, curated courses from world-class providers:
- Harvard University (edX / YouTube - CS50)
- freeCodeCamp (Scientific Computing, Relational Databases, Web Design)
- Kaggle Learn (Python, SQL, Machine Learning, Data Visualization)
- Cisco Networking Academy (Cybersecurity)
- Open University (Project Management)

### 4.4 Security & Application Integrity
- Passwords hashed using Werkzeug (`scrypt` / `pbkdf2`).
- Cookie sessions configured with `HTTPOnly`, `SameSite=Lax`, and persistent secret key.
- Strict server-side role enforcement on every API endpoint.
- File uploads restricted to PDF, DOCX, and TXT with a 5MB size limit and sanitized filenames.
- Auditable status transitions and administrator audit logging in SQLite.

---

## 5. Project Directory Structure

```
JobBridge/
├── api.py                    # Main Flask application entry point
├── database.py               # Database connection helpers & query executors
├── migrate_database.py       # Safe schema migration script
├── seed_data.py              # Repeatable demo data seeder
├── run_tests.py              # Automated test runner
├── README.md                 # Project documentation & setup instructions
├── app/
│   ├── __init__.py           # Application factory & blueprint registration
│   ├── routes/
│   │   ├── auth_routes.py    # Login, registration, session, logout
│   │   ├── candidate_routes.py # Onboarding, jobs, applications, profile, resume
│   │   ├── recruiter_routes.py # Company setup, job CRUD, applicants, analytics
│   │   ├── admin_routes.py   # Metrics, user moderation, job moderation, logs
│   │   ├── recommendation_routes.py # Transitions, readiness, courses, assistant
│   │   └── notification_routes.py # In-app notification center
│   └── services/
│       ├── auth_service.py   # Session & role decorators
│       ├── recommendation_service.py # Skill overlap & compatibility algorithms
│       ├── readiness_service.py # Versioned Career-Readiness calculation
│       ├── notification_service.py # In-app notification dispatcher
│       ├── audit_service.py  # Security audit logging
│       └── resume_service.py # Secure resume validation and storage
├── data/
│   ├── skillbridge.db        # SQLite database (16 tables)
│   ├── ai_explanations.csv   # Standardized occupational transition data
│   ├── learning_pathways.csv # Skill pathways mapped to occupations
│   └── resumes/              # Sandboxed secure resume uploads
├── static/
│   ├── script.js             # Modern REST client (no localStorage mock)
│   └── style.css             # Branded UI styles, cards, tables, and modals
├── templates/
│   └── index.html            # Authoritative multi-portal HTML interface
└── tests/
    ├── test_auth.py
    ├── test_recruitment.py
    ├── test_recommendations.py
    └── test_admin.py
```
