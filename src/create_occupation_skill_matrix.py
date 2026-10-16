import pandas as pd

# ============================================================
# LOAD NCO → ESCO → SKILL MAPPING
# ============================================================

file = "data/nco_esco_skill_mapping.csv"

df = pd.read_csv(file)

print("NCO → ESCO → SKILL DATA")
print("=" * 60)
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nCOLUMNS")
print("=" * 60)
print(df.columns.tolist())

# ============================================================
# REMOVE DUPLICATE SKILLS
# ============================================================

df = df.drop_duplicates(
    subset=["isco3", "code", "skillUri"]
)

print("\nAFTER REMOVING DUPLICATES")
print("=" * 60)
print("Rows:", len(df))

# ============================================================
# ESSENTIAL / OPTIONAL COUNTS
# ============================================================

print("\nRELATION TYPES")
print("=" * 60)
print(df["relationType"].value_counts())

# ============================================================
# CREATE OCCUPATION SKILL MATRIX
# ============================================================

matrix = (
    df.groupby(["isco3", "code", "preferredLabel"])
      .agg(
          required_skills=("skillLabel", list),
          skill_count=("skillLabel", "nunique")
      )
      .reset_index()
)

print("\nOCCUPATION SKILL MATRIX")
print("=" * 60)
print("Rows:", len(matrix))
print("Columns:", len(matrix.columns))

print("\nSAMPLE")
print("=" * 60)

print(matrix.head(10).to_string(index=False))

# ============================================================
# SAVE
# ============================================================

output = "data/occupation_skill_matrix.csv"

matrix.to_csv(output, index=False)

print("\nSaved successfully!")
print("File:", output)