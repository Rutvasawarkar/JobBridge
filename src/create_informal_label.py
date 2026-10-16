import pandas as pd

# Load our cleaned PLFS dataset
df = pd.read_csv("data/plfs_clean.csv")

print("PLFS CLEAN DATA")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ==========================================
# CREATE INFORMAL EMPLOYMENT LABEL
# ==========================================

def classify_employment(row):

    pas = row["pas"]

    # Self-employed
    if pas in [11, 12]:
        return "Informal"

    # Unpaid family worker
    elif pas == 21:
        return "Informal"

    # Regular salaried/wage employee
    elif pas == 31:

        # No paid leave + no social security
        if row["leave_pas"] == 2 and row["ssec_pas"] == 2:
            return "Informal"

        else:
            return "Formal"

    # Casual labour
    elif pas in [41, 51]:
        return "Informal"

    # Other cases
    else:
        return "Other"


df["employment_type"] = df.apply(classify_employment, axis=1)


# ==========================================
# CHECK RESULTS
# ==========================================

print("\nEMPLOYMENT TYPE COUNTS")

print(
    df["employment_type"]
    .value_counts(dropna=False)
)


# ==========================================
# SAVE
# ==========================================

df.to_csv(
    "data/plfs_labeled.csv",
    index=False
)

print("\nSaved successfully!")
print("File: data/plfs_labeled.csv")