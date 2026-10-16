import pandas as pd

# Load PLFS data
data_path = "data/PLFS/CSV_data_PLFS_2023_2024/perv1.csv"

df = pd.read_csv(data_path, low_memory=False)

# Principal occupation column
occupation_col = "b5pt1q6_perv1"

print("NCO OCCUPATION CODE ANALYSIS")
print("=" * 60)

# Remove missing values
occupation_codes = df[occupation_col].dropna()

print("Total non-missing occupation records:", len(occupation_codes))
print("Unique occupation codes:", occupation_codes.nunique())

print("\nTOP 50 OCCUPATION CODES")
print("=" * 60)

print(
    occupation_codes
    .value_counts()
    .head(50)
)

print("\nSAMPLE OCCUPATION CODES")
print("=" * 60)

print(
    sorted(occupation_codes.unique())[:100]
)