import pandas as pd

INPUT_FILE = "data/worker_skill_profiles.csv"
OUTPUT_FILE = "data/occupation_skill_profiles.csv"

print("LOADING WORKER-SKILL DATA")
print("=" * 60)

df = pd.read_csv(INPUT_FILE)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

# ---------------------------------------------------------
# Keep only the columns needed for occupation-skill analysis
# ---------------------------------------------------------

skills = df[
    [
        "nco_code",
        "skillLabel",
        "skillType",
        "relationType"
    ]
].drop_duplicates()

# Remove missing values
skills = skills.dropna(subset=["nco_code", "skillLabel"])

# ---------------------------------------------------------
# Create occupation-level skill profile
# ---------------------------------------------------------

occupation_profiles = (
    skills
    .groupby("nco_code")
    .agg(
        skill_count=("skillLabel", "nunique"),
        skills=("skillLabel", lambda x: " | ".join(sorted(set(x))))
    )
    .reset_index()
)

# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

occupation_profiles.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("OCCUPATION SKILL PROFILES")
print("=" * 60)

print(f"Occupation groups: {len(occupation_profiles)}")
print(
    f"Total unique skills: "
    f"{skills['skillLabel'].nunique()}"
)

print()
print("SAMPLE")
print("=" * 60)

print(
    occupation_profiles.head(10).to_string(index=False)
)

print()
print("Saved successfully!")
print(f"File: {OUTPUT_FILE}")