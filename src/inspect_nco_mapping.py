import pandas as pd
from pathlib import Path

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

plfs_path = BASE_DIR / "data" / "plfs_labeled.csv"

# Your ESCO occupation file
esco_path = BASE_DIR / "data" / "ESCO" / "occupations_en.csv"

# -----------------------------
# LOAD PLFS
# -----------------------------
df = pd.read_csv(plfs_path)

print("PLFS LABELED DATA")
print("=" * 60)
print("Rows:", len(df))
print("Columns:", len(df.columns))

# -----------------------------
# LOAD ESCO
# -----------------------------
esco = pd.read_csv(esco_path)

print("\nESCO OCCUPATION DATA")
print("=" * 60)
print("Rows:", len(esco))
print("Columns:", len(esco.columns))
print("\nColumns:")
print(esco.columns.tolist())

# -----------------------------
# PLFS NCO CODES
# -----------------------------
plfs_codes = (
    df["ocu_pas"]
    .dropna()
    .astype(float)
    .astype(int)
    .astype(str)
    .unique()
)

print("\nPLFS UNIQUE NCO CODES:", len(plfs_codes))
print(sorted(plfs_codes)[:50])

# -----------------------------
# SHOW ESCO SAMPLE
# -----------------------------
print("\nESCO SAMPLE")
print("=" * 60)
print(esco.head(10).to_string(index=False))