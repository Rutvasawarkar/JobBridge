import pandas as pd
import os

# ============================================================
# FILE PATHS
# ============================================================

INPUT_PATH = "data/personalized_recommendations.csv"
OUTPUT_PATH = "data/top_worker_recommendations.csv"

TOP_N = 5


# ============================================================
# LOAD DATA
# ============================================================

print("LOADING PERSONALIZED RECOMMENDATIONS")
print("=" * 60)

df = pd.read_csv(INPUT_PATH)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "current_nco_code",
    "current_occupation",
    "target_occupation",
    "target_occupation_code",
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "transition_score",
    "personalized_score",
    "personalized_level"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# ============================================================
# REMOVE DUPLICATE RECOMMENDATIONS
# ============================================================

print("\nREMOVING DUPLICATE RECOMMENDATIONS")
print("=" * 60)

before = len(df)

df = df.drop_duplicates(
    subset=[
        "current_nco_code",
        "current_occupation",
        "target_occupation",
        "target_occupation_code"
    ]
).copy()

after = len(df)

print(f"Rows before: {before}")
print(f"Rows after:  {after}")
print(f"Duplicates removed: {before - after}")


# ============================================================
# PREPARE NUMERIC SCORES
# ============================================================

numeric_columns = [
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "transition_score",
    "personalized_score"
]

for col in numeric_columns:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(
    subset=["personalized_score"]
).copy()


# ============================================================
# SORT RECOMMENDATIONS
# ============================================================

print("\nRANKING RECOMMENDATIONS")
print("=" * 60)

df = df.sort_values(
    [
        "current_nco_code",
        "personalized_score",
        "skill_similarity"
    ],
    ascending=[
        True,
        False,
        False
    ]
)


# ============================================================
# TOP N RECOMMENDATIONS
# ============================================================

top_recommendations = (
    df
    .groupby("current_nco_code", group_keys=False)
    .head(TOP_N)
    .copy()
)


# ============================================================
# CREATE RANK
# ============================================================

top_recommendations["recommendation_rank"] = (
    top_recommendations
    .groupby("current_nco_code")
    .cumcount()
    + 1
)


# ============================================================
# SELECT IMPORTANT COLUMNS
# ============================================================

output_columns = [
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
    "recommendation_rank"
]

# Keep only columns that exist
output_columns = [
    col
    for col in output_columns
    if col in top_recommendations.columns
]

top_recommendations = top_recommendations[
    output_columns
].copy()


# ============================================================
# SUMMARY
# ============================================================

print("\nTOP WORKER RECOMMENDATIONS")
print("=" * 60)

print(
    f"Rows: {len(top_recommendations)}"
)

print(
    f"Unique current occupations: "
    f"{top_recommendations['current_nco_code'].nunique()}"
)

print(
    f"Top {TOP_N} recommendations per occupation"
)


# ============================================================
# SAMPLE
# ============================================================

print("\nSAMPLE RECOMMENDATIONS")
print("=" * 60)

print(
    top_recommendations
    .head(30)
    .to_string(index=False)
)


# ============================================================
# RECOMMENDATION LEVEL COUNTS
# ============================================================

print("\nRECOMMENDATION LEVEL COUNTS")
print("=" * 60)

print(
    top_recommendations[
        "personalized_level"
    ].value_counts()
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

top_recommendations.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved successfully!")
print(f"File: {OUTPUT_PATH}")