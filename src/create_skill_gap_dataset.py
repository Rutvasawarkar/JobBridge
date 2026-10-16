import pandas as pd
import ast
import os

# ============================================================
# 1. LOAD OCCUPATION-SKILL MATRIX
# ============================================================

input_file = "data/occupation_skill_matrix.csv"

df = pd.read_csv(input_file)

print("OCCUPATION SKILL MATRIX")
print("=" * 60)
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print()

print("COLUMNS")
print("=" * 60)
print(df.columns.tolist())
print()


# ============================================================
# 2. CONVERT REQUIRED SKILLS FROM STRING TO LIST
# ============================================================

def convert_to_list(value):
    """
    Convert the required_skills column from
    CSV string representation into a Python list.
    """

    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []


df["required_skills"] = df["required_skills"].apply(convert_to_list)


# ============================================================
# 3. NORMALIZE SKILL NAMES
# ============================================================

def normalize_skills(skills):
    """
    Normalize skill names so comparisons are consistent.
    """

    return {
        str(skill).strip().lower()
        for skill in skills
        if str(skill).strip()
    }


df["skill_set"] = df["required_skills"].apply(normalize_skills)


# ============================================================
# 4. PREPARE OCCUPATION INFORMATION
# ============================================================

occupations = df[
    [
        "isco3",
        "code",
        "preferredLabel",
        "skill_set"
    ]
].copy()

occupations = occupations.drop_duplicates(
    subset=["code"]
).reset_index(drop=True)

print("UNIQUE OCCUPATIONS")
print("=" * 60)
print(f"Occupations: {len(occupations)}")
print()


# ============================================================
# 5. CREATE CURRENT → TARGET OCCUPATION PAIRS
# ============================================================

gap_records = []

for i, current in occupations.iterrows():

    current_skills = current["skill_set"]

    for j, target in occupations.iterrows():

        # Do not recommend the same occupation
        if current["code"] == target["code"]:
            continue

        target_skills = target["skill_set"]

        # ----------------------------------------------------
        # Common skills
        # ----------------------------------------------------

        common_skills = current_skills.intersection(
            target_skills
        )

        # ----------------------------------------------------
        # Missing skills
        # ----------------------------------------------------

        missing_skills = target_skills.difference(
            current_skills
        )

        # ----------------------------------------------------
        # Extra skills
        # ----------------------------------------------------

        extra_skills = current_skills.difference(
            target_skills
        )

        target_skill_count = len(target_skills)
        common_skill_count = len(common_skills)
        missing_skill_count = len(missing_skills)

        # ----------------------------------------------------
        # Skill gap score
        #
        # 0 = no gap
        # 1 = completely different
        # ----------------------------------------------------

        if target_skill_count > 0:
            skill_gap_score = (
                missing_skill_count /
                target_skill_count
            )
        else:
            skill_gap_score = 1.0

        # ----------------------------------------------------
        # Skill similarity score
        #
        # Higher is better
        # ----------------------------------------------------

        skill_similarity = 1 - skill_gap_score

        gap_records.append(
            {
                "current_isco3": current["isco3"],
                "current_nco_code": current["isco3"],
                "current_occupation": current["preferredLabel"],
                "current_occupation_code": current["code"],

                "target_occupation": target["preferredLabel"],
                "target_occupation_code": target["code"],
                "target_isco3": target["isco3"],

                "common_skills": sorted(common_skills),
                "missing_skills": sorted(missing_skills),
                "extra_skills": sorted(extra_skills),

                "common_skill_count": common_skill_count,
                "missing_skill_count": missing_skill_count,
                "extra_skill_count": len(extra_skills),

                "current_skill_count": len(current_skills),
                "target_skill_count": target_skill_count,

                "skill_gap_score": round(
                    skill_gap_score, 4
                ),

                "skill_similarity": round(
                    skill_similarity, 4
                )
            }
        )


# ============================================================
# 6. CREATE DATAFRAME
# ============================================================

gap_df = pd.DataFrame(gap_records)


print("SKILL GAP DATASET")
print("=" * 60)
print(f"Rows: {len(gap_df)}")
print(f"Columns: {len(gap_df.columns)}")
print()


# ============================================================
# 7. REMOVE VERY LARGE / UNUSABLE TRANSITIONS
# ============================================================

# Keep transitions where at least one skill is shared.
gap_df = gap_df[
    gap_df["common_skill_count"] > 0
].copy()


# ============================================================
# 8. SORT BY BEST TRANSITIONS
# ============================================================

gap_df = gap_df.sort_values(
    by=[
        "current_occupation",
        "skill_similarity"
    ],
    ascending=[
        True,
        False
    ]
).reset_index(drop=True)


# ============================================================
# 9. SAVE DATASET
# ============================================================

output_file = "data/skill_gap_dataset.csv"

gap_df.to_csv(
    output_file,
    index=False
)


# ============================================================
# 10. DISPLAY SAMPLE
# ============================================================

print("TOP SKILL TRANSITIONS")
print("=" * 60)

sample_columns = [
    "current_occupation",
    "target_occupation",
    "common_skill_count",
    "missing_skill_count",
    "target_skill_count",
    "skill_gap_score",
    "skill_similarity"
]

print(
    gap_df[sample_columns].head(20).to_string(
        index=False
    )
)

print()
print("Saved successfully!")
print(f"File: {output_file}")