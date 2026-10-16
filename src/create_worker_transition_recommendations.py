import pandas as pd
import os

# ============================================================
# FILE PATHS
# ============================================================

INPUT_FILE = "data/transition_candidates.csv"
OUTPUT_FILE = "data/worker_transition_recommendations.csv"

# ============================================================
# LOAD DATA
# ============================================================

print("LOADING TRANSITION CANDIDATES")
print("=" * 60)

df = pd.read_csv(INPUT_FILE)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\nCOLUMNS")
print("=" * 60)
print(df.columns.tolist())

# ============================================================
# CLEAN DATA
# ============================================================

df = df.dropna(
    subset=[
        "current_occupation",
        "target_occupation",
        "skill_similarity",
        "transition_score"
    ]
)

# Remove same occupation transitions
df = df[
    df["current_occupation"] != df["target_occupation"]
].copy()

# ============================================================
# RANK TRANSITIONS
# ============================================================

print("\nRANKING TRANSITION OPTIONS")
print("=" * 60)

# Higher transition score = better transition
df = df.sort_values(
    by=[
        "current_occupation",
        "transition_score",
        "skill_similarity"
    ],
    ascending=[True, False, False]
)

# Rank each target occupation for every current occupation
df["recommendation_rank"] = (
    df.groupby("current_occupation")
      .cumcount() + 1
)

# ============================================================
# KEEP TOP RECOMMENDATIONS
# ============================================================

TOP_N = 10

recommendations = df[
    df["recommendation_rank"] <= TOP_N
].copy()

# ============================================================
# ADD RECOMMENDATION LEVEL
# ============================================================

def recommendation_level(score):
    if score >= 0.70:
        return "Excellent"
    elif score >= 0.55:
        return "Good"
    elif score >= 0.40:
        return "Moderate"
    else:
        return "Low"


recommendations["recommendation_level"] = (
    recommendations["transition_score"]
    .apply(recommendation_level)
)

# ============================================================
# SELECT IMPORTANT COLUMNS
# ============================================================

output_columns = [
    "current_occupation",
    "target_occupation",
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "same_isco_group",
    "transition_score",
    "recommendation_rank",
    "recommendation_level"
]

recommendations = recommendations[output_columns]

# ============================================================
# SAVE
# ============================================================

os.makedirs("data", exist_ok=True)

recommendations.to_csv(
    OUTPUT_FILE,
    index=False
)

# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\nWORKER TRANSITION RECOMMENDATIONS")
print("=" * 60)

print(f"Rows: {len(recommendations)}")
print(
    f"Unique current occupations: "
    f"{recommendations['current_occupation'].nunique()}"
)

print(
    f"Unique target occupations: "
    f"{recommendations['target_occupation'].nunique()}"
)

print("\nSAMPLE RECOMMENDATIONS")
print("=" * 60)

print(
    recommendations.head(30).to_string(index=False)
)

print("\nRECOMMENDATION LEVEL COUNTS")
print("=" * 60)

print(
    recommendations["recommendation_level"]
    .value_counts()
)

print("\nSaved successfully!")
print(f"File: {OUTPUT_FILE}")