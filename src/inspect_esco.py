import pandas as pd

# Load occupation-skill relationships
relations = pd.read_csv(
    "data/ESCO/occupationSkillRelations_en.csv"
)

# Make output easier to read
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print("FIRST 10 OCCUPATION-SKILL RELATIONSHIPS")

print(
    relations[
        [
            "occupationLabel",
            "relationType",
            "skillType",
            "skillLabel"
        ]
    ].head(10).to_string(index=False)
)