import pandas as pd

relations_path = "data/ESCO/occupationSkillRelations_en.csv"

df = pd.read_csv(relations_path)

print("ESCO OCCUPATION-SKILL RELATIONS")
print("=" * 60)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nCOLUMNS")
print("=" * 60)
print(df.columns.tolist())

print("\nFIRST 10 ROWS")
print("=" * 60)
print(df.head(10).to_string(index=False))