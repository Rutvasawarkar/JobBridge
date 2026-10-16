import pandas as pd

# ============================================================
# FILE PATHS
# ============================================================

plfs_path = "data/plfs_labeled.csv"
skills_path = "data/nco_skill_profiles.csv"

# ============================================================
# LOAD DATA
# ============================================================

plfs = pd.read_csv(plfs_path)
skills = pd.read_csv(skills_path)

print("DATA LOADED")
print("=" * 60)

print("PLFS rows:", len(plfs))
print("Skill profile rows:", len(skills))

# ============================================================
# PREPARE PLFS NCO CODE
# ============================================================

plfs["nco_code"] = (
    pd.to_numeric(plfs["ocu_pas"], errors="coerce")
    .astype("Int64")
    .astype(str)
)

# Remove missing/invalid occupation codes

plfs = plfs[
    plfs["nco_code"].notna() &
    (plfs["nco_code"] != "<NA>")
].copy()

# Convert NCO to 3-digit group

plfs["nco_code"] = plfs["nco_code"].str[:3]

# ============================================================
# SELECT WORKER INFORMATION
# ============================================================

worker_columns = [
    "age",
    "sex",
    "gedu_lvl",
    "tedu_lvl",
    "form_edu",
    "voc",
    "employment_type",
    "nco_code"
]

worker_data = plfs[worker_columns].copy()

# ============================================================
# JOIN WORKERS WITH SKILLS
# ============================================================
worker_data["nco_code"] = worker_data["nco_code"].astype(str)
skills["nco_code"] = skills["nco_code"].astype(str)
worker_skills = worker_data.merge(
    skills,
    on="nco_code",
    how="inner"
)

# ============================================================
# REMOVE DUPLICATES
# ============================================================

worker_skills = worker_skills.drop_duplicates()

# ============================================================
# RESULTS
# ============================================================

print("\nWORKER SKILL DATASET")
print("=" * 60)

print("Rows:", len(worker_skills))

print(
    "Unique workers/records:",
    len(worker_data)
)

print(
    "Unique NCO groups:",
    worker_skills["nco_code"].nunique()
)

print(
    "Unique skills:",
    worker_skills["skillUri"].nunique()
)

# ============================================================
# EMPLOYMENT TYPE DISTRIBUTION
# ============================================================

print("\nEMPLOYMENT TYPE")
print("=" * 60)

print(
    worker_skills["employment_type"]
    .value_counts()
)

# ============================================================
# SAMPLE
# ============================================================

print("\nSAMPLE WORKER-SKILL RECORDS")
print("=" * 60)

print(
    worker_skills[
        [
            "age",
            "sex",
            "employment_type",
            "nco_code",
            "skillLabel",
            "skillType",
            "relationType"
        ]
    ].head(30).to_string(index=False)
)

# ============================================================
# SAVE
# ============================================================

output_path = "data/worker_skill_profiles.csv"

worker_skills.to_csv(
    output_path,
    index=False
)

print("\nSaved successfully!")
print("File:", output_path)