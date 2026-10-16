import pandas as pd

# ============================================================
# 1. LOAD SKILL GAP DATASET
# ============================================================

input_file = "data/skill_gap_dataset.csv"

df = pd.read_csv(input_file)

print("SKILL GAP DATASET")
print("=" * 60)
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print()


# ============================================================
# 2. FILTER BY SKILL SIMILARITY
# ============================================================

# Keep transitions where at least 30% of target skills
# are already covered by the current occupation.

df = df[
    df["skill_similarity"] >= 0.30
].copy()

print("AFTER SKILL SIMILARITY FILTER")
print("=" * 60)
print(f"Rows: {len(df)}")
print()


# ============================================================
# 3. CALCULATE ISCO GROUP DISTANCE
# ============================================================

df["same_isco_group"] = (
    df["current_isco3"] == df["target_isco3"]
)


# ============================================================
# 4. CREATE TRANSITION SCORE
# ============================================================

# Skill similarity is the main factor.
#
# Same occupation group gets an additional bonus.

df["transition_score"] = (
    df["skill_similarity"] * 0.80
    + df["same_isco_group"].astype(int) * 0.20
)


# ============================================================
# 5. REMOVE VERY LARGE SKILL GAPS
# ============================================================

df = df[
    df["missing_skill_count"] <=
    df["target_skill_count"] * 0.70
].copy()


# ============================================================
# 6. SORT BEST TRANSITIONS FIRST
# ============================================================

df = df.sort_values(
    by=[
        "current_occupation",
        "transition_score"
    ],
    ascending=[
        True,
        False
    ]
).reset_index(drop=True)


# ============================================================
# 7. KEEP TOP 10 TARGETS PER CURRENT OCCUPATION
# ============================================================

df = (
    df.groupby(
        "current_occupation",
        group_keys=False
    )
    .head(10)
    .reset_index(drop=True)
)


# ============================================================
# 8. SAVE
# ============================================================

output_file = "data/transition_candidates.csv"

df.to_csv(
    output_file,
    index=False
)


# ============================================================
# 9. DISPLAY RESULTS
# ============================================================

print("TRANSITION CANDIDATES")
print("=" * 60)
print(f"Rows: {len(df)}")
print()

columns = [
    "current_occupation",
    "target_occupation",
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "same_isco_group",
    "transition_score"
]

print(
    df[columns]
    .head(30)
    .to_string(index=False)
)

print()
print("Saved successfully!")
print(f"File: {output_file}")