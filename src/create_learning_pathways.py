import pandas as pd
import os

# ============================================================
# PATHS
# ============================================================

TRANSITION_PATH = "data/top_worker_recommendations.csv"
ESCO_RELATIONS_PATH = "data/ESCO/occupationSkillRelations_en.csv"
OUTPUT_PATH = "data/learning_pathways.csv"


# ============================================================
# LOAD DATA
# ============================================================

print("LOADING DATA")
print("=" * 60)

transitions = pd.read_csv(
    TRANSITION_PATH,
    low_memory=False
)

esco = pd.read_csv(
    ESCO_RELATIONS_PATH,
    low_memory=False
)

print(f"Transition rows: {len(transitions)}")
print(f"ESCO relation rows: {len(esco)}")


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

transitions.columns = transitions.columns.str.strip()
esco.columns = esco.columns.str.strip()


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_transition = [
    "current_occupation",
    "target_occupation",
    "target_occupation_code",
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "skill_gap_score",
    "transition_score"
]

required_esco = [
    "occupationLabel",
    "skillLabel",
    "skillType",
    "relationType"
]

for col in required_transition:
    if col not in transitions.columns:
        raise ValueError(
            f"Missing transition column: {col}"
        )

for col in required_esco:
    if col not in esco.columns:
        raise ValueError(
            f"Missing ESCO column: {col}"
        )


# ============================================================
# NORMALIZE OCCUPATION NAMES
# ============================================================

transitions["current_occupation_clean"] = (
    transitions["current_occupation"]
    .astype(str)
    .str.strip()
    .str.lower()
)

transitions["target_occupation_clean"] = (
    transitions["target_occupation"]
    .astype(str)
    .str.strip()
    .str.lower()
)

esco["occupation_clean"] = (
    esco["occupationLabel"]
    .astype(str)
    .str.strip()
    .str.lower()
)

esco["skill_clean"] = (
    esco["skillLabel"]
    .astype(str)
    .str.strip()
    .str.lower()
)


# ============================================================
# CREATE OCCUPATION → SKILL DICTIONARY
# ============================================================

print("\nBUILDING OCCUPATION SKILL PROFILES")
print("=" * 60)

# Remove duplicate occupation-skill relationships

esco_unique = esco.drop_duplicates(
    subset=[
        "occupation_clean",
        "skill_clean"
    ]
).copy()


occupation_skills = (
    esco_unique
    .groupby("occupation_clean")
    .agg({
        "skill_clean": set
    })
    .to_dict()["skill_clean"]
)


print(
    f"Occupations with ESCO skills: "
    f"{len(occupation_skills)}"
)


# ============================================================
# FUNCTION TO GET MISSING SKILLS
# ============================================================

def get_missing_skills(current_occupation, target_occupation):

    current_skills = occupation_skills.get(
        current_occupation,
        set()
    )

    target_skills = occupation_skills.get(
        target_occupation,
        set()
    )

    missing = target_skills - current_skills

    return missing


# ============================================================
# CALCULATE MISSING SKILLS
# ============================================================

print("\nCALCULATING SKILL GAPS")
print("=" * 60)

transitions["missing_skill_set"] = transitions.apply(
    lambda row: get_missing_skills(
        row["current_occupation_clean"],
        row["target_occupation_clean"]
    ),
    axis=1
)


# ============================================================
# EXPLODE MISSING SKILLS
# ============================================================

learning = transitions.explode(
    "missing_skill_set"
).copy()


learning = learning[
    learning["missing_skill_set"].notna()
].copy()


learning["skill_clean"] = (
    learning["missing_skill_set"]
    .astype(str)
    .str.strip()
    .str.lower()
)


# ============================================================
# ADD SKILL INFORMATION
# ============================================================

skill_information = esco_unique[
    [
        "skill_clean",
        "skillLabel",
        "skillType",
        "relationType"
    ]
].drop_duplicates(
    subset=["skill_clean"]
)


learning = learning.merge(
    skill_information,
    on="skill_clean",
    how="left"
)


# ============================================================
# ASSIGN PRIORITY
# ============================================================

def assign_priority(row):

    relation = str(
        row["relationType"]
    ).lower()

    if relation == "essential":
        return "High"

    return "Medium"


learning["skill_priority"] = learning.apply(
    assign_priority,
    axis=1
)


# ============================================================
# ASSIGN LEARNING DIFFICULTY
# ============================================================

def assign_difficulty(score):

    if score >= 0.75:
        return "Low"

    elif score >= 0.50:
        return "Medium"

    else:
        return "High"


learning["learning_difficulty"] = (
    learning["transition_score"]
    .apply(assign_difficulty)
)


# ============================================================
# PRIORITY ORDER
# ============================================================

priority_order = {
    "High": 1,
    "Medium": 2,
    "Low": 3
}

learning["priority_order"] = (
    learning["skill_priority"]
    .map(priority_order)
)


# ============================================================
# FINAL COLUMNS
# ============================================================

final_columns = [
    "current_nco_code",
    "current_occupation",
    "current_occupation_code",

    "target_occupation",
    "target_occupation_code",
    "target_isco3",

    "skill_similarity",
    "common_skill_count",
    "missing_skill_count",
    "target_skill_count",
    "skill_gap_score",
    "transition_score",

    "personalized_score",
    "personalized_level",
    "recommendation_rank",

    "skillLabel",
    "skillType",
    "relationType",

    "skill_priority",
    "learning_difficulty"
]


final_columns = [
    col for col in final_columns
    if col in learning.columns
]


learning = learning[
    final_columns
]


# ============================================================
# REMOVE DUPLICATES
# ============================================================

learning = learning.drop_duplicates(
    subset=[
        "current_occupation",
        "target_occupation",
        "skillLabel"
    ]
)


# ============================================================
# SORT
# ============================================================

learning = learning.sort_values(
    by=[
        "current_occupation",
        "recommendation_rank",
        "skill_priority",
        "skillLabel"
    ],
    na_position="last"
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

learning.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# RESULTS
# ============================================================

print("\nLEARNING PATHWAY DATASET")
print("=" * 60)

print(f"Rows: {len(learning)}")
print(f"Columns: {len(learning.columns)}")


# ============================================================
# SAMPLE
# ============================================================

print("\nSAMPLE LEARNING PATHWAYS")
print("=" * 60)

print(
    learning.head(30).to_string(
        index=False
    )
)


# ============================================================
# PRIORITY COUNTS
# ============================================================

print("\nSKILL PRIORITY COUNTS")
print("=" * 60)

print(
    learning[
        "skill_priority"
    ].value_counts()
)


# ============================================================
# DIFFICULTY COUNTS
# ============================================================

print("\nLEARNING DIFFICULTY COUNTS")
print("=" * 60)

print(
    learning[
        "learning_difficulty"
    ].value_counts()
)


print("\nSaved successfully!")
print(f"File: {OUTPUT_PATH}")