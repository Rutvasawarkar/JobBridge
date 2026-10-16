import pandas as pd
import os

# ============================================================
# PATHS
# ============================================================

TOP_RECOMMENDATIONS_PATH = "data/top_worker_recommendations.csv"
LEARNING_PATHWAYS_PATH = "data/learning_pathways.csv"

OUTPUT_PATH = "data/ai_explanations.csv"

# ============================================================
# LOAD DATA
# ============================================================

print("=" * 60)
print("LOADING RECOMMENDATION DATA")
print("=" * 60)

if not os.path.exists(TOP_RECOMMENDATIONS_PATH):
    raise FileNotFoundError(
        f"File not found: {TOP_RECOMMENDATIONS_PATH}\n"
        "Run create_top_worker_recommendations.py first."
    )

if not os.path.exists(LEARNING_PATHWAYS_PATH):
    raise FileNotFoundError(
        f"File not found: {LEARNING_PATHWAYS_PATH}\n"
        "Run create_learning_pathways.py first."
    )

recommendations = pd.read_csv(
    TOP_RECOMMENDATIONS_PATH,
    low_memory=False
)

learning = pd.read_csv(
    LEARNING_PATHWAYS_PATH,
    low_memory=False
)

print(f"Top recommendation rows: {len(recommendations)}")
print(f"Learning pathway rows: {len(learning)}")

# ============================================================
# CHECK COLUMNS
# ============================================================

print("\n" + "=" * 60)
print("RECOMMENDATION COLUMNS")
print("=" * 60)

print(list(recommendations.columns))

print("\n" + "=" * 60)
print("LEARNING PATHWAY COLUMNS")
print("=" * 60)

print(list(learning.columns))

# ============================================================
# CLEAN COLUMN TYPES
# ============================================================

if "current_nco_code" in recommendations.columns:
    recommendations["current_nco_code"] = (
        recommendations["current_nco_code"]
        .astype(str)
        .str.strip()
    )

if "current_nco_code" in learning.columns:
    learning["current_nco_code"] = (
        learning["current_nco_code"]
        .astype(str)
        .str.strip()
    )

# ============================================================
# REMOVE DUPLICATES
# ============================================================

recommendations = recommendations.drop_duplicates(
    subset=[
        "current_nco_code",
        "current_occupation",
        "target_occupation"
    ]
).copy()

print("\n" + "=" * 60)
print("AFTER DUPLICATE REMOVAL")
print("=" * 60)

print(f"Recommendation rows: {len(recommendations)}")

# ============================================================
# BUILD SKILL GAP LOOKUP
# ============================================================

print("\n" + "=" * 60)
print("BUILDING SKILL GAP LOOKUP")
print("=" * 60)

# Learning pathways contain one row per missing skill.
# We group them so that each occupation transition gets
# its list of required learning skills.

required_columns = [
    "current_nco_code",
    "current_occupation",
    "target_occupation",
    "skillLabel",
    "skillType",
    "skill_priority",
    "learning_difficulty"
]

missing_columns = [
    col for col in required_columns
    if col not in learning.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns in learning_pathways.csv: {missing_columns}"
    )

# Remove empty skill names
learning = learning[
    learning["skillLabel"].notna()
].copy()

learning["skillLabel"] = (
    learning["skillLabel"]
    .astype(str)
    .str.strip()
)

learning = learning[
    learning["skillLabel"] != ""
]

# ============================================================
# AGGREGATE MISSING SKILLS
# ============================================================

def unique_list(series):
    values = []

    for value in series:
        if pd.isna(value):
            continue

        value = str(value).strip()

        if value and value not in values:
            values.append(value)

    return values


skill_lookup = (
    learning
    .groupby(
        [
            "current_nco_code",
            "current_occupation",
            "target_occupation"
        ],
        dropna=False
    )
    .agg(
        missing_skills=("skillLabel", unique_list),
        skill_types=("skillType", unique_list),
        skill_priorities=("skill_priority", unique_list),
        learning_difficulties=("learning_difficulty", unique_list)
    )
    .reset_index()
)

print(f"Transition skill profiles: {len(skill_lookup)}")

# ============================================================
# MERGE RECOMMENDATIONS WITH SKILLS
# ============================================================

print("\n" + "=" * 60)
print("MERGING RECOMMENDATIONS WITH SKILL GAPS")
print("=" * 60)

df = recommendations.merge(
    skill_lookup,
    on=[
        "current_nco_code",
        "current_occupation",
        "target_occupation"
    ],
    how="left"
)

print(f"Merged rows: {len(df)}")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default

        return int(float(value))

    except (ValueError, TypeError):
        return default


def clean_list(value):
    if isinstance(value, list):
        return value

    if pd.isna(value):
        return []

    return [str(value)]


# ============================================================
# EXPLANATION GENERATOR
# ============================================================

def generate_explanation(row):

    current = str(
        row.get("current_occupation", "current occupation")
    )

    target = str(
        row.get("target_occupation", "target occupation")
    )

    similarity = safe_float(
        row.get("skill_similarity", 0)
    )

    missing_count = safe_int(
        row.get("missing_skill_count", 0)
    )

    target_count = safe_int(
        row.get("target_skill_count", 0)
    )

    transition_score = safe_float(
        row.get("transition_score", 0)
    )

    personalized_score = safe_float(
        row.get("personalized_score", transition_score)
    )

    level = str(
        row.get("personalized_level", "Moderate")
    )

    # --------------------------------------------------------
    # Similarity explanation
    # --------------------------------------------------------

    similarity_percent = round(similarity * 100, 1)

    if similarity >= 0.80:
        similarity_text = (
            f"Your current occupation shares a very high "
            f"level of skills with {target} "
            f"({similarity_percent}% skill similarity)."
        )

    elif similarity >= 0.60:
        similarity_text = (
            f"Your current occupation has a strong skill "
            f"overlap with {target} "
            f"({similarity_percent}% skill similarity)."
        )

    elif similarity >= 0.40:
        similarity_text = (
            f"Your current occupation has a moderate skill "
            f"overlap with {target} "
            f"({similarity_percent}% skill similarity)."
        )

    else:
        similarity_text = (
            f"The transition to {target} requires a significant "
            f"skill expansion because the current skill overlap "
            f"is {similarity_percent}%."
        )

    # --------------------------------------------------------
    # Skill gap explanation
    # --------------------------------------------------------

    if missing_count == 0:
        gap_text = (
            "No additional target skills were identified in "
            "the current skill-gap analysis."
        )

    elif missing_count <= 5:
        gap_text = (
            f"The estimated skill gap is small, with "
            f"{missing_count} additional skill(s) to develop."
        )

    elif missing_count <= 15:
        gap_text = (
            f"The estimated skill gap is moderate, with "
            f"{missing_count} additional skill(s) to develop."
        )

    else:
        gap_text = (
            f"The transition requires substantial upskilling, "
            f"with approximately {missing_count} additional "
            f"skill(s) identified."
        )

    # --------------------------------------------------------
    # Recommendation explanation
    # --------------------------------------------------------

    if level == "Excellent":

        recommendation_text = (
            f"{target} is an excellent transition option from "
            f"{current} based on the calculated skill similarity, "
            f"skill gap and transition score."
        )

    elif level == "Good":

        recommendation_text = (
            f"{target} is a good transition option from "
            f"{current}. The worker already possesses several "
            f"relevant skills, although some upskilling is required."
        )

    elif level == "Moderate":

        recommendation_text = (
            f"{target} is a moderate transition option. "
            f"The career path is possible, but additional "
            f"skill development would be required."
        )

    else:

        recommendation_text = (
            f"{target} is a lower-priority transition option "
            f"because the skill gap is relatively large."
        )

    # --------------------------------------------------------
    # Final explanation
    # --------------------------------------------------------

    explanation = (
        f"{recommendation_text} "
        f"{similarity_text} "
        f"{gap_text}"
    )

    return explanation


# ============================================================
# LEARNING PLAN GENERATOR
# ============================================================

def generate_learning_plan(row):

    skills = clean_list(
        row.get("missing_skills", [])
    )

    priorities = clean_list(
        row.get("skill_priorities", [])
    )

    difficulties = clean_list(
        row.get("learning_difficulties", [])
    )

    # Remove duplicate skills
    unique_skills = []

    for skill in skills:

        skill = str(skill).strip()

        if skill and skill not in unique_skills:
            unique_skills.append(skill)

    # --------------------------------------------------------
    # If no missing skills
    # --------------------------------------------------------

    if not unique_skills:

        return (
            "No major missing skills were identified. "
            "Focus on strengthening existing skills and "
            "gaining practical experience in the target occupation."
        )

    # --------------------------------------------------------
    # Limit displayed skills
    # --------------------------------------------------------

    top_skills = unique_skills[:10]

    skill_text = "; ".join(top_skills)

    if len(unique_skills) > 10:

        skill_text += (
            f"; and {len(unique_skills) - 10} additional skill(s)"
        )

    # --------------------------------------------------------
    # Difficulty
    # --------------------------------------------------------

    if "High" in difficulties:

        difficulty_text = (
            "The pathway contains high-difficulty learning "
            "requirements, so these should be developed gradually."
        )

    elif "Medium" in difficulties:

        difficulty_text = (
            "The pathway contains several medium-difficulty "
            "skills that should be developed through structured practice."
        )

    else:

        difficulty_text = (
            "The identified skills are generally suitable for "
            "progressive self-learning and practical practice."
        )

    return (
        f"Priority learning skills: {skill_text}. "
        f"{difficulty_text}"
    )


# ============================================================
# AI-STYLE EXPLANATIONS
# ============================================================

print("\n" + "=" * 60)
print("GENERATING EXPLANATIONS")
print("=" * 60)

df["explanation"] = df.apply(
    generate_explanation,
    axis=1
)

df["learning_plan"] = df.apply(
    generate_learning_plan,
    axis=1
)

# ============================================================
# ADD EXPLANATION COMPONENTS
# ============================================================

df["skill_similarity_percent"] = (
    pd.to_numeric(
        df["skill_similarity"],
        errors="coerce"
    )
    .fillna(0)
    * 100
).round(2)

df["skill_gap_percent"] = (
    pd.to_numeric(
        df["skill_gap_score"],
        errors="coerce"
    )
    .fillna(0)
    * 100
).round(2)

df["transition_score_percent"] = (
    pd.to_numeric(
        df["transition_score"],
        errors="coerce"
    )
    .fillna(0)
    * 100
).round(2)

df["personalized_score_percent"] = (
    pd.to_numeric(
        df["personalized_score"],
        errors="coerce"
    )
    .fillna(0)
    * 100
).round(2)

# ============================================================
# REASON / FACTOR COLUMNS
# ============================================================

def generate_reason(row):

    reasons = []

    similarity = safe_float(
        row.get("skill_similarity", 0)
    )

    missing = safe_int(
        row.get("missing_skill_count", 0)
    )

    same_group = row.get(
        "same_isco_group",
        False
    )

    if similarity >= 0.80:
        reasons.append("high skill similarity")

    elif similarity >= 0.60:
        reasons.append("strong skill similarity")

    elif similarity >= 0.40:
        reasons.append("moderate skill similarity")

    else:
        reasons.append("large skill difference")

    if missing <= 5:
        reasons.append("small skill gap")

    elif missing <= 15:
        reasons.append("moderate skill gap")

    else:
        reasons.append("large skill gap")

    if str(same_group).lower() == "true":
        reasons.append("same ISCO occupational group")

    return ", ".join(reasons)


df["recommendation_reason"] = df.apply(
    generate_reason,
    axis=1
)

# ============================================================
# SELECT FINAL COLUMNS
# ============================================================

preferred_columns = [
    "current_nco_code",
    "current_occupation",
    "current_occupation_code",

    "target_occupation",
    "target_occupation_code",
    "target_isco3",

    "skill_similarity",
    "skill_similarity_percent",

    "common_skill_count",
    "missing_skill_count",
    "target_skill_count",

    "skill_gap_score",
    "skill_gap_percent",

    "transition_score",
    "transition_score_percent",

    "personalized_score",
    "personalized_score_percent",

    "personalized_level",
    "recommendation_rank",

    "recommendation_reason",

    "missing_skills",

    "explanation",
    "learning_plan"
]

final_columns = [
    col for col in preferred_columns
    if col in df.columns
]

df = df[final_columns].copy()

# ============================================================
# CLEAN LIST COLUMNS FOR CSV
# ============================================================

for column in [
    "missing_skills"
]:

    if column in df.columns:

        df[column] = df[column].apply(
            lambda x: "; ".join(
                map(str, x)
            )
            if isinstance(x, list)
            else (
                "" if pd.isna(x)
                else str(x)
            )
        )

# ============================================================
# REMOVE FINAL DUPLICATES
# ============================================================

df = df.drop_duplicates(
    subset=[
        "current_nco_code",
        "current_occupation",
        "target_occupation"
    ]
)

# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_PATH,
    index=False
)

# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 60)
print("AI EXPLANATION DATASET")
print("=" * 60)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\n" + "=" * 60)
print("SAMPLE AI EXPLANATIONS")
print("=" * 60)

display_columns = [
    "current_occupation",
    "target_occupation",
    "personalized_score_percent",
    "personalized_level",
    "missing_skill_count",
    "recommendation_reason",
    "explanation",
    "learning_plan"
]

display_columns = [
    col for col in display_columns
    if col in df.columns
]

print(
    df[display_columns]
    .head(10)
    .to_string(index=False)
)

print("\n" + "=" * 60)
print("RECOMMENDATION LEVEL COUNTS")
print("=" * 60)

if "personalized_level" in df.columns:
    print(
        df["personalized_level"]
        .value_counts()
    )

print("\n" + "=" * 60)
print("SAVED SUCCESSFULLY")
print("=" * 60)

print(f"File: {OUTPUT_PATH}")