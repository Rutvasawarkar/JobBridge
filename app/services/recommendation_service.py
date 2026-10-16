import re
import pandas as pd
from pathlib import Path
from database import query_db

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
AI_EXPLANATIONS_PATH = DATA_DIR / "ai_explanations.csv"
LEARNING_PATHWAYS_PATH = DATA_DIR / "learning_pathways.csv"

_recommendations_cache = None
_learning_cache = None


def get_cached_datasets():
    global _recommendations_cache, _learning_cache
    if _recommendations_cache is None and AI_EXPLANATIONS_PATH.exists():
        _recommendations_cache = pd.read_csv(AI_EXPLANATIONS_PATH, low_memory=False)
    if _learning_cache is None and LEARNING_PATHWAYS_PATH.exists():
        _learning_cache = pd.read_csv(LEARNING_PATHWAYS_PATH, low_memory=False)
    return _recommendations_cache, _learning_cache


def normalize_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def parse_skills_list(skills_input):
    """Normalize input into a clean set of lowercase skill strings."""
    if not skills_input:
        return set()
    if isinstance(skills_input, str):
        parts = [s.strip() for s in skills_input.replace(";", ",").replace("|", ",").split(",")]
        return {p.lower() for p in parts if p}
    if isinstance(skills_input, (list, tuple, set)):
        result = set()
        for item in skills_input:
            if isinstance(item, dict):
                s = item.get("skill", "")
            else:
                s = str(item)
            s = s.strip().lower()
            if s:
                result.add(s)
        return result
    return set()


def calculate_skill_overlap(candidate_skills, target_skills):
    """Calculate Jaccard-like overlap, common skills, and missing skills."""
    c_set = parse_skills_list(candidate_skills)
    t_set = parse_skills_list(target_skills)

    if not t_set:
        return {
            "similarity": 1.0 if c_set else 0.5,
            "similarity_percent": 100.0 if c_set else 50.0,
            "common_skills": list(c_set),
            "missing_skills": [],
            "extra_skills": list(c_set)
        }

    common = c_set.intersection(t_set)
    missing = t_set - c_set
    extra = c_set - t_set
    similarity = len(common) / len(t_set)

    return {
        "similarity": round(similarity, 4),
        "similarity_percent": round(similarity * 100, 1),
        "common_skills": sorted(list(common)),
        "missing_skills": sorted(list(missing)),
        "extra_skills": sorted(list(extra)),
        "common_count": len(common),
        "missing_count": len(missing),
        "target_count": len(t_set)
    }


def calculate_job_compatibility(candidate, job):
    """
    Calculate explainable candidate-job compatibility score:
    - Skill Match (65% weight)
    - Experience Alignment (20% weight)
    - Location Alignment (15% weight)
    """
    job_skills = parse_skills_list(job.get("required_skills", ""))
    candidate_skills = parse_skills_list(candidate.get("skills", []))
    
    # 1. Skill Score
    if job_skills:
        overlap = calculate_skill_overlap(candidate_skills, job_skills)
        skill_score = overlap["similarity"]
        common = overlap["common_skills"]
        missing = overlap["missing_skills"]
    else:
        skill_score = 0.8
        common = list(candidate_skills)
        missing = []

    # 2. Experience Score
    cand_exp = candidate.get("experience", 0) or 0
    req_exp = job.get("experience_years_min", 0) or 0
    if req_exp == 0 or cand_exp >= req_exp:
        exp_score = 1.0
    else:
        exp_score = max(0.2, cand_exp / req_exp)

    # 3. Location Score
    job_loc = normalize_text(job.get("location", ""))
    cand_loc = normalize_text(candidate.get("location", ""))
    if "remote" in job_loc or not cand_loc or not job_loc:
        loc_score = 1.0
    elif cand_loc in job_loc or job_loc in cand_loc:
        loc_score = 1.0
    else:
        loc_score = 0.6

    total_score = (skill_score * 0.65) + (exp_score * 0.20) + (loc_score * 0.15)
    percentage = round(total_score * 100, 1)

    # Explanation
    reasons = []
    if skill_score >= 0.7:
        reasons.append(f"Strong skill alignment ({len(common)} required skill{'s' if len(common)!=1 else ''} matched)")
    elif skill_score >= 0.4:
        reasons.append(f"Partial skill match ({len(common)} matched, {len(missing)} to develop)")
    else:
        reasons.append(f"Developing skill profile ({len(missing)} skills required)")

    if cand_exp >= req_exp:
        reasons.append(f"Meets experience criteria ({cand_exp} yrs)")
    else:
        reasons.append(f"Entry-level fit (needs {req_exp} yrs, has {cand_exp} yrs)")

    if loc_score == 1.0:
        reasons.append("Location or remote mode compatible")

    return {
        "score": percentage,
        "skill_score_percent": round(skill_score * 100, 1),
        "experience_score_percent": round(exp_score * 100, 1),
        "location_score_percent": round(loc_score * 100, 1),
        "matched_skills": common,
        "missing_skills": missing,
        "explanation": "; ".join(reasons)
    }


def get_career_transitions(current_occupation, candidate_skills=None, top_n=5):
    """
    Return realistic career transitions with skill gap analysis and learning pathways.
    Queries cached AI explanations & learning pathways or database.
    """
    rec_df, learn_df = get_cached_datasets()
    if rec_df is None or rec_df.empty:
        return []

    norm_curr = normalize_text(current_occupation)
    if not norm_curr:
        return []

    # Search for occupation
    exact = rec_df[rec_df["current_occupation"].apply(normalize_text) == norm_curr]
    if exact.empty:
        exact = rec_df[rec_df["current_occupation"].apply(lambda v: norm_curr in normalize_text(v))]
    if exact.empty:
        exact = rec_df[rec_df["current_occupation"].apply(lambda v: normalize_text(v) in norm_curr)]
    if exact.empty:
        # Fallback to top overall transitions
        exact = rec_df.head(10)

    transitions = []
    matches = exact.drop_duplicates(subset=["current_occupation", "target_occupation"])
    matches = matches.sort_values(by=["personalized_score", "transition_score"], ascending=False).head(top_n)

    cand_skills_set = parse_skills_list(candidate_skills) if candidate_skills else None

    for _, row in matches.iterrows():
        target = str(row.get("target_occupation", "")).strip()
        
        # Pathways / Missing Skills
        pathway_items = []
        if learn_df is not None and not learn_df.empty:
            p_mask = (learn_df["current_occupation"].apply(normalize_text) == normalize_text(row.get("current_occupation", ""))) & \
                     (learn_df["target_occupation"].apply(normalize_text) == normalize_text(target))
            p_rows = learn_df[p_mask].drop_duplicates(subset=["skillLabel"]).head(10)
            for _, sr in p_rows.iterrows():
                s_name = str(sr.get("skillLabel", "")).strip()
                pathway_items.append({
                    "skill": s_name,
                    "priority": str(sr.get("skill_priority", "High")),
                    "difficulty": str(sr.get("learning_difficulty", "Beginner")),
                    "type": str(sr.get("skillType", "knowledge"))
                })

        # Calculate candidate-specific overlap if candidate skills provided
        if cand_skills_set and pathway_items:
            target_skills_all = [p["skill"] for p in pathway_items]
            overlap = calculate_skill_overlap(cand_skills_set, target_skills_all)
            cand_similarity = overlap["similarity_percent"]
            cand_missing = overlap["missing_skills"]
            cand_common = overlap["common_skills"]
        else:
            cand_similarity = round(float(row.get("skill_similarity", 0.5)) * 100, 1)
            cand_missing = [p["skill"] for p in pathway_items]
            cand_common = []

        transitions.append({
            "current_occupation": str(row.get("current_occupation", "")),
            "target_occupation": target,
            "target_occupation_code": str(row.get("target_occupation_code", "")),
            "match_score": round(float(row.get("personalized_score", 0.8)) * 100, 1),
            "skill_similarity": cand_similarity,
            "missing_skill_count": len(cand_missing) if cand_skills_set else int(row.get("missing_skill_count", len(pathway_items))),
            "target_skill_count": int(row.get("target_skill_count", len(pathway_items))),
            "reason": str(row.get("recommendation_reason", "High skill overlap and progressive transition")),
            "explanation": str(row.get("explanation", f"Realistic transition into {target} based on transferable skills.")),
            "learning_plan": str(row.get("learning_plan", "Focus on core essential skills.")),
            "skills": pathway_items,
            "missing_skills": cand_missing,
            "common_skills": cand_common
        })

    return transitions


def get_verified_courses_for_skills(skill_names):
    """Fetch verified authentic free courses corresponding to missing skills."""
    if not skill_names:
        return query_db("SELECT * FROM verified_courses ORDER BY id LIMIT 6")

    like_clauses = " OR ".join(["skill_name LIKE ?" for _ in skill_names])
    args = [f"%{s}%" for s in skill_names]
    
    courses = query_db(f"""
        SELECT * FROM verified_courses
        WHERE {like_clauses}
        ORDER BY id
        LIMIT 10
    """, args)

    if not courses:
        courses = query_db("SELECT * FROM verified_courses ORDER BY id LIMIT 6")
        
    return courses
