import pandas as pd

# ---------------------------------------
# LOAD PLFS PERSON DATA
# ---------------------------------------

data_path = "data/PLFS/CSV_data_PLFS_2023_2024/perv1.csv"

df = pd.read_csv(data_path, low_memory=False)

print("PLFS OCCUPATION CODE ANALYSIS")
print("=" * 50)

print("Rows:", len(df))
print("Columns:", len(df.columns))


# ---------------------------------------
# PRINCIPAL ACTIVITY OCCUPATION
# ---------------------------------------

ocu_pas = "b5pt1q6_perv1"

print("\nPRINCIPAL ACTIVITY OCCUPATION CODES")
print("=" * 50)

print(
    df[ocu_pas]
    .value_counts()
    .head(30)
)


# ---------------------------------------
# FIND CWS OCCUPATION COLUMN
# ---------------------------------------

print("\nPOSSIBLE CWS/OCCUPATION COLUMNS")
print("=" * 50)

for col in df.columns:
    if "b6q7" in col.lower() or "ocu" in col.lower():
        print(col)


# ---------------------------------------
# SHOW ALL BLOCK 6 COLUMNS
# ---------------------------------------

print("\nBLOCK 6 COLUMNS")
print("=" * 50)

for col in df.columns:
    if col.startswith("b6"):
        print(col)