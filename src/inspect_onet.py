import pandas as pd

onet_path = "data/ONET/O_NET database"

transferable_skills = pd.read_csv(
    f"{onet_path}/transferable_skills.csv"
)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)

print("FIRST 10 O*NET TRANSFERABLE SKILL RECORDS")

print(
    transferable_skills[
        [
            "O*NET-SOC Code",
            "Title",
            "Element Name",
            "Scale Name",
            "Data Value"
        ]
    ].head(10).to_string(index=False)
)