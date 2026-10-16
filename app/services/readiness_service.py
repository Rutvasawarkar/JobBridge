from database import query_db
from app.services.recommendation_service import parse_skills_list


def calculate_career_readiness(candidate, target_role_name, target_skills_list=None):
    """
    Calculate an explainable, transparent Career-Readiness Score (v1.0):
    1. Essential Skill Coverage (50%)
    2. Skill Proficiency Depth (20%)
    3. Experience Alignment (15%)
    4. Verified Learning Pathway Progress (15%)
    """
    candidate_id = candidate.get("id")
    candidate_skills = candidate.get("skills", [])
    
    # 1. Target Skills Lookup
    if not target_skills_list:
        # Check occupation in database
        occ_rows = query_db("""
            SELECT s.skill_name
            FROM occupations o
            JOIN occupation_skills os ON o.id = os.occupation_id
            JOIN skills s ON os.skill_id = s.id
            WHERE o.occupation_name LIKE ?
            LIMIT 15
        """, (f"%{target_role_name}%",))
        if occ_rows:
            target_skills_list = [r["skill_name"] for r in occ_rows]
        else:
            target_skills_list = ["Python", "SQL", "Data Analysis", "Communication"]

    c_skills_set = parse_skills_list(candidate_skills)
    t_skills_set = parse_skills_list(target_skills_list)

    # 1. Essential Skill Match (50%)
    matched = c_skills_set.intersection(t_skills_set)
    missing = t_skills_set - c_skills_set
    skill_coverage = len(matched) / max(1, len(t_skills_set))
    essential_score = round(skill_coverage * 50, 1)

    # 2. Proficiency Depth (20%)
    prof_weights = {"Beginner": 0.5, "Intermediate": 0.8, "Advanced": 1.0, "Expert": 1.0}
    prof_sum = 0.0
    matched_count = 0
    for cs in candidate_skills:
        s_name = cs.get("skill", "").lower()
        if s_name in [m.lower() for m in matched]:
            prof = cs.get("proficiency", "Intermediate")
            prof_sum += prof_weights.get(prof, 0.7)
            matched_count += 1
    
    avg_prof = (prof_sum / max(1, matched_count)) if matched_count > 0 else 0.4
    proficiency_score = round(avg_prof * 20, 1)

    # 3. Experience Alignment (15%)
    cand_exp = candidate.get("experience", 0) or 0
    exp_ratio = min(1.0, cand_exp / 3.0)  # Benchmark 3 years for mid-level readiness
    experience_score = round(exp_ratio * 15, 1)

    # 4. Learning Pathway Progress (15%)
    completed_learning = 0
    if candidate_id:
        completed_rows = query_db("""
            SELECT COUNT(*) as c FROM user_learning_progress
            WHERE user_id = ? AND status = 'Completed'
        """, (candidate_id,), one=True)
        completed_learning = completed_rows["c"] if completed_rows else 0

    learning_ratio = min(1.0, completed_learning / 2.0)  # 2 completed courses yields max learning factor
    learning_score = round(learning_ratio * 15, 1)

    # Total score out of 100
    total = round(essential_score + proficiency_score + experience_score + learning_score, 1)

    # Readiness Band
    if total >= 80:
        band = "Strong Candidate"
        band_class = "band-high"
    elif total >= 60:
        band = "Role Ready"
        band_class = "band-mid"
    elif total >= 40:
        band = "Developing Readiness"
        band_class = "band-low"
    else:
        band = "Early Preparation"
        band_class = "band-early"

    # Actionable Steps
    next_steps = []
    if missing:
        sample_missing = list(missing)[:3]
        next_steps.append(f"Develop missing essential skill{'s' if len(sample_missing)!=1 else ''}: {', '.join(sample_missing)}.")
    if completed_learning == 0:
        next_steps.append("Complete verified free courses in your learning pathway to earn up to +15 points.")
    if cand_exp < 2:
        next_steps.append("Build project portfolio and document hands-on experience to strengthen domain readiness.")

    return {
        "version": "1.0",
        "target_role": target_role_name,
        "readiness_score": total,
        "readiness_band": band,
        "band_class": band_class,
        "factors": {
            "essential_skill_coverage": {
                "score": essential_score,
                "max": 50,
                "matched_count": len(matched),
                "total_target_skills": len(t_skills_set),
                "matched_skills": sorted(list(matched)),
                "missing_skills": sorted(list(missing))
            },
            "proficiency_depth": {
                "score": proficiency_score,
                "max": 20,
                "average_rating": round(avg_prof * 100, 1)
            },
            "experience_alignment": {
                "score": experience_score,
                "max": 15,
                "candidate_experience_years": cand_exp
            },
            "learning_progress": {
                "score": learning_score,
                "max": 15,
                "completed_courses_count": completed_learning
            }
        },
        "actionable_next_steps": next_steps,
        "disclaimer": "This score evaluates profile and skill alignment against standardized role requirements. It is an explainable measure of readiness, not a predictive guarantee of employment."
    }
