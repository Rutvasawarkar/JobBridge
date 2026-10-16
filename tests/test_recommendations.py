from api import app
from app.services.recommendation_service import calculate_skill_overlap, calculate_job_compatibility
from app.services.readiness_service import calculate_career_readiness


def test_skill_overlap_calculation():
    cand_skills = ["Python", "SQL", "Excel", "Data Analysis"]
    target_skills = ["Python", "SQL", "Machine Learning", "Deep Learning", "Statistics"]

    overlap = calculate_skill_overlap(cand_skills, target_skills)
    assert overlap["common_count"] == 2
    assert "python" in overlap["common_skills"]
    assert "sql" in overlap["common_skills"]
    assert "machine learning" in overlap["missing_skills"]
    assert overlap["similarity_percent"] == 40.0


def test_job_compatibility():
    candidate = {
        "skills": ["Python", "SQL", "Data Analysis"],
        "experience": 2,
        "location": "Nagpur, India"
    }
    job = {
        "required_skills": "Python, SQL, Machine Learning",
        "experience_years_min": 1,
        "location": "Nagpur / Hybrid"
    }

    comp = calculate_job_compatibility(candidate, job)
    assert comp["score"] > 60.0
    assert "Python" in comp["matched_skills"] or "python" in comp["matched_skills"]
    assert len(comp["explanation"]) > 0


def test_career_readiness_scoring():
    candidate = {
        "id": 1,
        "skills": [
            {"skill": "Python", "proficiency": "Advanced"},
            {"skill": "SQL", "proficiency": "Intermediate"}
        ],
        "experience": 2
    }
    readiness = calculate_career_readiness(candidate, "Data Analyst")
    assert readiness["version"] == "1.0"
    assert 0 <= readiness["readiness_score"] <= 100
    assert readiness["readiness_band"] in ["Early Preparation", "Developing Readiness", "Role Ready", "Strong Candidate"]
    assert "essential_skill_coverage" in readiness["factors"]
    assert len(readiness["actionable_next_steps"]) > 0


def test_analyze_api(client):
    res = client.post("/api/analyze", json={"occupation": "data analyst"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["recommendations"]) > 0
    top = data["recommendations"][0]
    assert "target_occupation" in top
    assert "match_score" in top
    assert "skills" in top
