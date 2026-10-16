import pandas as pd

# ============================================================
# FILE PATH
# ============================================================

mapping_path = "data/nco_esco_skill_mapping.csv"

# ============================================================
# LOAD MAPPING
# ============================================================

df = pd.read_csv(mapping_path)

print("ESCO MAPPING DATA")
print("=" * 60)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nCOLUMNS")
print("=" * 60)
print(df.columns.tolist())

# ============================================================
# PREPARE NCO CODE
# ============================================================

df["nco_code"] = df["isco3"].astype(str).str.strip()

# ============================================================
# REMOVE MISSING SKILLS
# ============================================================

df = df[df["skillLabel"].notna()].copy()

# ============================================================
# REMOVE DUPLICATE SKILL MAPPINGS
# ============================================================

df = df.drop_duplicates(
    subset=[
        "nco_code",
        "skillUri",
        "relationType",
        "skillType"
    ]
)

# ============================================================
# CREATE NCO-LEVEL SKILL PROFILE
# ============================================================

skill_profiles = (
    df[
        [
            "nco_code",
            "skillUri",
            "skillLabel",
            "skillType",
            "relationType"
        ]
    ]
    .sort_values(
        [
            "nco_code",
            "relationType",
            "skillLabel"
        ]
    )
)

# ============================================================
# INFORMATION
# ============================================================

print("\nNCO SKILL PROFILE")
print("=" * 60)

print("Rows:", len(skill_profiles))

print(
    "Unique NCO groups:",
    skill_profiles["nco_code"].nunique()
)

print(
    "Unique skills:",
    skill_profiles["skillUri"].nunique()
)

# ============================================================
# SKILLS PER NCO GROUP
# ============================================================

skill_count = (
    skill_profiles
    .groupby("nco_code")["skillUri"]
    .nunique()
    .sort_values(ascending=False)
)

print("\nTOP NCO GROUPS BY NUMBER OF SKILLS")
print("=" * 60)

print(skill_count.head(20))

# ============================================================
# RELATION TYPE COUNTS
# ============================================================

print("\nRELATION TYPE COUNTS")
print("=" * 60)

print(
    skill_profiles["relationType"]
    .value_counts()
)

# ============================================================
# SAVE
# ============================================================

output_path = "data/nco_skill_profiles.csv"

skill_profiles.to_csv(
    output_path,
    index=False
)

print("\nSaved successfully!")
print("File:", output_path)

# ============================================================
# SAMPLE
# ============================================================

print("\nSAMPLE SKILL PROFILES")
print("=" * 60)

print(
    skill_profiles.head(30).to_string(index=False)
)