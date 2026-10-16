import pandas as pd

# ============================================================
# LOAD DATA
# ============================================================

worker_file = "data/worker_skill_profiles.csv"

df = pd.read_csv(worker_file)

print("WORKER SKILL PROFILES")
print("=" * 60)
print("Rows:", len(df))
print("Columns:", len(df.columns))

# ============================================================
# CHECK COLUMNS
# ============================================================

print("\nCOLUMNS")
print("=" * 60)

print(df.columns.tolist())

# ============================================================
# REMOVE DUPLICATE SKILLS
# ============================================================

df = df.drop_duplicates(
    subset=["nco_code", "employment_type", "skillLabel"]
)

print("\nAFTER REMOVING DUPLICATE SKILLS")
print("=" * 60)
print("Rows:", len(df))

# ============================================================
# CREATE SKILL COUNT PER OCCUPATION
# ============================================================

skill_counts = (
    df.groupby(["nco_code", "employment_type"])["skillLabel"]
    .nunique()
    .reset_index(name="skill_count")
)

print("\nSKILL COUNTS")
print("=" * 60)
print(skill_counts.head(20))

# ============================================================
# SAVE
# ============================================================

skill_counts.to_csv(
    "data/occupation_skill_counts.csv",
    index=False
)

print("\nSaved successfully!")
print("File: data/occupation_skill_counts.csv")