import pandas as pd
import os

# ============================================================
# FILE PATHS
# ============================================================

PLFS_PATH = "data/plfs_labeled.csv"
TRANSITION_PATH = "data/transition_candidates.csv"
OUTPUT_PATH = "data/personalized_recommendations.csv"


# ============================================================
# LOAD DATA
# ============================================================

print("LOADING DATA")
print("=" * 60)

plfs = pd.read_csv(PLFS_PATH)
transitions = pd.read_csv(TRANSITION_PATH)

print(f"PLFS rows: {len(plfs)}")
print(f"Transition rows: {len(transitions)}")


# ============================================================
# SHOW COLUMNS
# ============================================================

print("\nPLFS COLUMNS")
print("=" * 60)
print(list(plfs.columns))

print("\nTRANSITION COLUMNS")
print("=" * 60)
print(list(transitions.columns))


# ============================================================
# FIND PLFS OCCUPATION COLUMN
# ============================================================

possible_occupation_columns = [
    "ocu_pas",
    "nco_code",
    "occupation_code",
    "occupation",
    "nco"
]

occupation_col = None

for col in possible_occupation_columns:
    if col in plfs.columns:
        occupation_col = col
        break

if occupation_col is None:
    raise ValueError(
        "Could not find occupation column in PLFS data."
    )

print(
    f"\nUsing PLFS occupation column: {occupation_col}"
)


# ============================================================
# FIND TRANSITION OCCUPATION COLUMN
# ============================================================

possible_transition_columns = [
    "current_nco_code",
    "current_occupation_code",
    "current_isco3"
]

transition_occupation_col = None

for col in possible_transition_columns:
    if col in transitions.columns:
        transition_occupation_col = col
        break

if transition_occupation_col is None:
    raise ValueError(
        "Could not find current occupation column "
        "in transition data."
    )

print(
    "Using transition occupation column: "
    f"{transition_occupation_col}"
)


# ============================================================
# PREPARE WORKER DATA
# ============================================================

# Convert occupation to numeric
plfs[occupation_col] = pd.to_numeric(
    plfs[occupation_col],
    errors="coerce"
)

# Remove workers without occupation
worker_data = plfs.dropna(
    subset=[occupation_col]
).copy()

print(
    f"\nWorkers with occupation: {len(worker_data)}"
)


# ============================================================
# STANDARDIZE OCCUPATION CODE
# ============================================================

worker_data["current_nco_code"] = (
    worker_data[occupation_col]
    .astype(int)
    .astype(str)
)


# ============================================================
# SELECT WORKER FEATURES
# ============================================================

worker_features = [
    "age",
    "sex",
    "gedu_lvl",
    "tedu_lvl",
    "form_edu",
    "voc",
    "employment_type"
]

# Keep only columns that actually exist
worker_features = [
    col for col in worker_features
    if col in worker_data.columns
]

worker_profiles = worker_data[
    ["current_nco_code"] + worker_features
].copy()


# ============================================================
# REMOVE DUPLICATE WORKER PROFILES
# ============================================================

worker_profiles = worker_profiles.drop_duplicates()

print(
    f"Unique worker profiles: {len(worker_profiles)}"
)


# ============================================================
# PREPARE TRANSITION DATA
# ============================================================

transitions = transitions.copy()

# Standardize transition occupation code
transitions[
    transition_occupation_col
] = pd.to_numeric(
    transitions[transition_occupation_col],
    errors="coerce"
)

# Remove invalid occupation codes
transitions = transitions.dropna(
    subset=[transition_occupation_col]
).copy()

# Convert to same format as worker data
transitions["current_nco_code"] = (
    transitions[transition_occupation_col]
    .astype(int)
    .astype(str)
)

print(
    f"\nValid transition rows: {len(transitions)}"
)


# ============================================================
# MERGE WORKERS WITH TRANSITIONS
# ============================================================

print("\nMERGING WORKERS WITH TRANSITIONS")
print("=" * 60)

personalized = worker_profiles.merge(
    transitions,
    on="current_nco_code",
    how="inner"
)

print(
    f"Personalized rows: {len(personalized)}"
)


# ============================================================
# CHECK RESULT
# ============================================================

if len(personalized) == 0:
    raise ValueError(
        "No personalized recommendations were created. "
        "Check occupation code formats."
    )


# ============================================================
# CREATE PERSONALIZED SCORE
# ============================================================

# Base transition score
personalized["personalized_score"] = (
    personalized["transition_score"]
)


# ============================================================
# EDUCATION ADJUSTMENT
# ============================================================

# The adjustment is intentionally simple at this stage.
# It provides personalization based on available PLFS data.

if "tedu_lvl" in personalized.columns:

    personalized["education_factor"] = (
        pd.to_numeric(
            personalized["tedu_lvl"],
            errors="coerce"
        )
        .fillna(0)
    )

    # Normalize education factor
    max_education = (
        personalized["education_factor"].max()
    )

    if max_education > 0:

        personalized["education_factor"] = (
            personalized["education_factor"]
            / max_education
        )

        personalized["personalized_score"] = (
            personalized["transition_score"] * 0.8
            +
            personalized["education_factor"] * 0.2
        )


# ============================================================
# RANK RECOMMENDATIONS FOR EACH WORKER PROFILE
# ============================================================

personalized = personalized.sort_values(
    [
        "current_nco_code",
        "personalized_score"
    ],
    ascending=[True, False]
)

personalized[
    "personalized_rank"
] = personalized.groupby(
    "current_nco_code"
)["personalized_score"].rank(
    method="first",
    ascending=False
)


# ============================================================
# RECOMMENDATION LEVEL
# ============================================================

def recommendation_level(score):

    if score >= 0.70:
        return "Excellent"

    elif score >= 0.50:
        return "Good"

    elif score >= 0.30:
        return "Moderate"

    else:
        return "Low"


personalized["personalized_level"] = (
    personalized["personalized_score"]
    .apply(recommendation_level)
)


# ============================================================
# DISPLAY SAMPLE
# ============================================================

print("\nPERSONALIZED RECOMMENDATIONS")
print("=" * 60)

display_columns = [
    "current_nco_code",
    "current_occupation",
    "target_occupation",
    "skill_similarity",
    "missing_skill_count",
    "transition_score",
    "personalized_score",
    "personalized_rank",
    "personalized_level"
]

display_columns = [
    col
    for col in display_columns
    if col in personalized.columns
]

print(
    personalized[display_columns]
    .head(30)
    .to_string(index=False)
)


# ============================================================
# SUMMARY
# ============================================================

print("\nRECOMMENDATION LEVEL COUNTS")
print("=" * 60)

print(
    personalized[
        "personalized_level"
    ].value_counts()
)


# ============================================================
# SAVE DATASET
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

personalized.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved successfully!")
print(f"File: {OUTPUT_PATH}")