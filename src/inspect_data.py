from pathlib import Path

# Find our project's data folder
data_folder = Path("data")

print("Data folder exists:", data_folder.exists())
print()

print("Files currently in data folder:")

for file in data_folder.iterdir():
    print("-", file.name)