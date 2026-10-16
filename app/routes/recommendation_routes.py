from flask import Blueprint, request, jsonify, session
from database import query_db
from app.services.auth_service import get_current_user
from app.services.recommendation_service import (
    get_career_transitions,
    get_verified_courses_for_skills,
    calculate_skill_overlap,
    parse_skills_list
)
from app.services.readiness_service import calculate_career_readiness

recommendation_bp = Blueprint("recommendations", __name__, url_prefix="/api")


@recommendation_bp.route("/occupations", methods=["GET"])
def list_occupations():
    """Return available occupations for dropdown and autocomplete."""
    rows = query_db("""
        SELECT DISTINCT occupation_name
        FROM occupations
        ORDER BY occupation_name ASC
        LIMIT 300
    """)
    names = [r["occupation_name"] for r in rows if r["occupation_name"]]
    return jsonify({
        "status": "success",
        "count": len(names),
        "occupations": names
    })


@recommendation_bp.route("/analyze", methods=["POST"])
def analyze_career():
    """Analyze career transition opportunities from current occupation."""
    data = request.get_json(silent=True) or {}
    user = get_current_user()

    occupation = str(data.get("occupation", "")).strip()
    if not occupation and user:
        occupation = user.get("current_occupation", "")

    if not occupation or occupation == "Not specified":
        return jsonify({
            "status": "error",
            "message": "Current occupation is required for transition analysis."
        }), 400

    skills = data.get("skills")
    if not skills and user:
        skills = user.get("skills", [])

    transitions = get_career_transitions(occupation, candidate_skills=skills, top_n=5)

    if not transitions:
        return jsonify({
            "status": "error",
            "message": f"No career transition models matched for '{occupation}'. Try selecting a standardized occupation from /api/occupations."
        }), 404

    # Calculate readiness preview for top target
    top_target = transitions[0]["target_occupation"]
    readiness = None
    if user:
        readiness = calculate_career_readiness(user, top_target)

    return jsonify({
        "status": "success",
        "current_occupation": occupation,
        "recommendations": transitions,
        "career_readiness": readiness,
        "career_readiness_note": "Match scores evaluate occupational skill proximity. Career-readiness evaluates verified candidate profile coverage."
    })


@recommendation_bp.route("/career-readiness", methods=["GET"])
def get_career_readiness():
    """Explainable career-readiness score calculation for target role."""
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Please log in to calculate personal career readiness."}), 401

    target_role = request.args.get("target_role") or user.get("career_interest") or "Data Analyst"
    readiness = calculate_career_readiness(user, target_role)
    return jsonify({"status": "success", "readiness": readiness})


@recommendation_bp.route("/courses", methods=["GET"])
def get_courses():
    """List verified authentic free courses."""
    skill_filter = request.args.get("skill")
    skills = [skill_filter] if skill_filter else None
    courses = get_verified_courses_for_skills(skills)
    return jsonify({
        "status": "success",
        "count": len(courses),
        "courses": [dict(c) for c in courses]
    })


@recommendation_bp.route("/assistant/chat", methods=["POST"])
def assistant_chat():
    """
    Deterministic grounded career assistant.
    Grounded strictly in the user's profile, target role, missing skills, and verified courses.
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip().lower()

    if not message:
        return jsonify({"status": "error", "message": "Message content cannot be empty."}), 400

    user_name = user.get("name", "there") if user else "there"
    curr_occ = user.get("current_occupation", "your current role") if user else "your current role"
    target_role = user.get("career_interest", "your target career") if user else "your target career"
    user_skills = [s.get("skill") if isinstance(s, dict) else str(s) for s in user.get("skills", [])] if user else []

    # Contextual deterministic response generator
    if any(k in message for k in ["readiness", "score", "improve"]):
        readiness = calculate_career_readiness(user, target_role) if user else None
        score_txt = f"{readiness['readiness_score']}% ({readiness['readiness_band']})" if readiness else "not yet calculated"
        reply = (
            f"Hello {user_name}! Your current Career-Readiness Score for **{target_role}** is **{score_txt}**.\n\n"
            f"Here are 3 verified steps to raise your score:\n"
            f"1. **Essential Skills:** Complete courses for target skills you have not yet added to your profile.\n"
            f"2. **Learning Progress:** Mark verified courses as 'Completed' in your learning pathways (+15% max factor).\n"
            f"3. **Hands-on Experience:** Document practical projects and internships on your resume and profile."
        )

    elif any(k in message for k in ["skill", "gap", "missing", "learn"]):
        transitions = get_career_transitions(curr_occ, candidate_skills=user_skills, top_n=1) if user else []
        if transitions:
            missing = transitions[0].get("missing_skills", [])[:4]
            reply = (
                f"Analyzing your transition from **{curr_occ}** to **{transitions[0]['target_occupation']}**:\n\n"
                f"Key missing skills to focus on:\n" +
                "\n".join([f"- **{s}**" for s in missing]) +
                f"\n\nYou can access free verified certifications for these in the **Learning Pathways** section."
            )
        else:
            reply = (
                f"Based on industry benchmarks for **{target_role}**, the top essential competencies are: "
                f"**Python**, **SQL**, **Data Analysis**, and **System Design**. Check the Courses tab to access free verified resources."
            )

    elif any(k in message for k in ["job", "apply", "opportunity", "opening"]):
        open_jobs = query_db("SELECT title, location, employment_type FROM jobs WHERE status = 'Open' LIMIT 3")
        jobs_list = "\n".join([f"- **{j['title']}** ({j['location']} - {j['employment_type']})" for j in open_jobs])
        reply = (
            f"Here are top active opportunities currently open on JobBridge:\n\n"
            f"{jobs_list}\n\n"
            f"Head over to the **Jobs** tab to view your personalized compatibility scores and apply directly!"
        )

    else:
        reply = (
            f"Hello {user_name}! I am your JobBridge Career Assistant. "
            f"I can help you analyze realistic career transitions from **{curr_occ}**, "
            f"calculate your explainable **Readiness Score** for **{target_role}**, "
            f"recommend verified free learning courses, and explore matched jobs.\n\n"
            f"Try asking: *'How can I improve my readiness score?'* or *'What skills am I missing for {target_role}?'*"
        )

    return jsonify({
        "status": "success",
        "reply": reply,
        "grounding": {
            "current_occupation": curr_occ,
            "target_role": target_role,
            "skills_count": len(user_skills)
        }
    })
