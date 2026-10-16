import pandas as pd

# ============================================================
# FILE PATHS
# ============================================================

plfs_path = "data/plfs_labeled.csv"
esco_occ_path = "data/ESCO/occupations_en.csv"
esco_rel_path = "data/ESCO/occupationSkillRelations_en.csv"

# ============================================================
# LOAD DATA
# ============================================================

plfs = pd.read_csv(plfs_path)
esco_occ = pd.read_csv(esco_occ_path)
esco_rel = pd.read_csv(esco_rel_path)

print("DATA LOADED")
print("=" * 60)
print("PLFS rows:", len(plfs))
print("ESCO occupations:", len(esco_occ))
print("ESCO relations:", len(esco_rel))

# ============================================================
# PREPARE PLFS NCO CODES
# ============================================================

plfs["nco_code"] = (
    pd.to_numeric(plfs["ocu_pas"], errors="coerce")
    .dropna()
    .astype(int)
    .astype(str)
)

# Keep only records having occupation codes
plfs_occ = plfs[plfs["nco_code"].notna()].copy()

# 3-digit NCO/ISCO group
plfs_occ["isco3"] = plfs_occ["nco_code"].str[:3]

print("\nPLFS OCCUPATION RECORDS:", len(plfs_occ))
print("PLFS UNIQUE NCO CODES:", plfs_occ["nco_code"].nunique())

# ============================================================
# PREPARE ESCO OCCUPATION CODES
# ============================================================

esco_occ["iscoGroup"] = (
    esco_occ["iscoGroup"]
    .astype(str)
    .str.strip()
)

esco_occ["isco3"] = esco_occ["iscoGroup"].str[:3]

# Only ESCO occupations whose 3-digit group occurs in PLFS
plfs_isco3 = set(plfs_occ["isco3"].unique())

esco_matched = esco_occ[
    esco_occ["isco3"].isin(plfs_isco3)
].copy()

print("\nESCO OCCUPATIONS WITH MATCHING 3-DIGIT GROUP:",
      len(esco_matched))

# ============================================================
# JOIN ESCO OCCUPATIONS WITH THEIR SKILLS
# ============================================================

mapping = esco_matched[
    [
        "conceptUri",
        "preferredLabel",
        "iscoGroup",
        "code",
        "isco3"
    ]
].merge(
    esco_rel[
        [
            "occupationUri",
            "occupationLabel",
            "relationType",
            "skillType",
            "skillUri",
            "skillLabel"
        ]
    ],
    left_on="conceptUri",
    right_on="occupationUri",
    how="inner"
)

print("\nNCO/ISCO → ESCO → SKILL MAPPING")
print("=" * 60)

print("Mapping rows:", len(mapping))
print("Unique ESCO occupations:", mapping["conceptUri"].nunique())
print("Unique skills:", mapping["skillUri"].nunique())

# ============================================================
# SAVE
# ============================================================

output_path = "data/nco_esco_skill_mapping.csv"

mapping.to_csv(
    output_path,
    index=False
)

print("\nSaved successfully!")
print("File:", output_path)

# ============================================================
# SAMPLE
# ============================================================

print("\nSAMPLE MAPPING")
print("=" * 60)

print(
    mapping[
        [
            "isco3",
            "preferredLabel",
            "code",
            "relationType",
            "skillType",
            "skillLabel"
        ]
    ].head(20).to_string(index=False)
)