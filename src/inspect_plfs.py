import pandas as pd

# File paths
plfs_path = "data/PLFS/CSV_data_PLFS_2023_2024/perv1.csv"
layout_path = "data/ONET/Data_LayoutPLFS_2023-24.xlsx"

# --------------------------------------------------
# 1. Read PLFS person-level CSV
# --------------------------------------------------

df = pd.read_csv(plfs_path)

print("PLFS RECORDS:", len(df))
print("PLFS COLUMNS:", len(df.columns))


# --------------------------------------------------
# 2. Read PLFS layout
# --------------------------------------------------

layout = pd.read_excel(
    layout_path,
    sheet_name="perv1"
)


# --------------------------------------------------
# 3. Create CSV → PLFS field mapping
# --------------------------------------------------

mapping = dict(zip(layout["Field_Name"], df.columns))


# --------------------------------------------------
# 4. Rename columns using PLFS Field_Name
# --------------------------------------------------

df = df.rename(columns={
    csv_col: field_name
    for field_name, csv_col in mapping.items()
})


# --------------------------------------------------
# 5. Create employment-status categories
# --------------------------------------------------

employment_codes = {
    11: "Self-employed - Own account worker",
    12: "Self-employed - Employer",
    21: "Unpaid family worker",
    31: "Regular salaried/wage employee",
    41: "Casual wage labour - Public works",
    51: "Other type of work",
    81: "Unemployed",
    91: "Not in labour force",
    92: "Not in labour force",
    93: "Not in labour force",
    94: "Not in labour force",
    95: "Not in labour force",
    97: "Not in labour force",
    99: "Other/unknown"
}

df["employment_status"] = df["pas"].map(employment_codes)


# --------------------------------------------------
# 6. Display results
# --------------------------------------------------

print("\nPAS CODE COUNTS")
print(df["pas"].value_counts().sort_index())

print("\nEMPLOYMENT STATUS")
print(df["employment_status"].value_counts(dropna=False))

# ==========================================
# CREATE CLEAN PLFS DATASET
# ==========================================

important_columns = [
    "age",
    "sex",
    "gedu_lvl",
    "tedu_lvl",
    "form_edu",
    "voc",
    "pas",
    "ind_pas",
    "ocu_pas",
    "etyp_pas",
    "wrkr_pas",
    "job_pas",
    "leave_pas",
    "ssec_pas",
    "dur_pas",
    "ern_reg",
    "ern_self",
    "acws"
]

clean_df = df[important_columns].copy()

print("\nCLEAN DATASET")
print("Rows:", len(clean_df))
print("Columns:", len(clean_df.columns))

print("\nCOLUMNS")
print(clean_df.columns.tolist())

print("\nFIRST 10 ROWS")
print(clean_df.head(10))

clean_df.to_csv("data/plfs_clean.csv", index=False)

print("\nSaved successfully!")
print("File: data/plfs_clean.csv")