import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------
# LOAD PLFS
# -----------------------------
plfs_path = BASE_DIR / "data" / "plfs_labeled.csv"
df = pd.read_csv(plfs_path)

# -----------------------------
# LOAD ESCO
# -----------------------------
esco_path = BASE_DIR / "data" / "ESCO" / "occupations_en.csv"
esco = pd.read_csv(esco_path)

# -----------------------------
# GET UNIQUE PLFS NCO CODES
# -----------------------------
nco_codes = (
    df["ocu_pas"]
    .dropna()
    .astype(float)
    .astype(int)
    .astype(str)
    .unique()
)

# -----------------------------
# CREATE 3-DIGIT ISCO GROUP
# FROM ESCO ISCO GROUP
# -----------------------------
esco["isco3"] = (
    pd.to_numeric(esco["iscoGroup"], errors="coerce")
    .astype("Int64")
    .astype(str)
    .str[:3]
)

# -----------------------------
# CHECK POSSIBLE MATCHES
# -----------------------------
matched = esco[esco["isco3"].isin(nco_codes)]

print("NCO → ESCO POSSIBLE MATCHING")
print("=" * 60)

print("PLFS unique NCO codes:", len(nco_codes))
print("ESCO occupations:", len(esco))
print("ESCO occupations with matching 3-digit prefix:",
      len(matched))

print("\nMATCHING 3-DIGIT GROUPS")
print("=" * 60)

groups = (
    matched[["isco3", "iscoGroup", "preferredLabel", "code"]]
    .drop_duplicates()
    .sort_values(["isco3", "iscoGroup"])
)

print(groups.head(100).to_string(index=False))