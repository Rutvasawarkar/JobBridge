import pandas as pd
import os

# ============================================================
# PATHS
# ============================================================

RECOMMENDATIONS_PATH = "data/ai_explanations.csv"
LEARNING_PATHWAYS_PATH = "data/learning_pathways.csv"

# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("LOADING CAREER RECOMMENDATION SYSTEM")
print("=" * 70)

if not os.path.exists(RECOMMENDATIONS_PATH):
    raise FileNotFoundError(
        f"\nFile not found: {RECOMMENDATIONS_PATH}\n"
        "Run create_ai_explanations.py first."
    )

if not os.path.exists(LEARNING_PATHWAYS_PATH):
    raise FileNotFoundError(
        f"\nFile not found: {LEARNING_PATHWAYS_PATH}\n"
        "Run create_learning_pathways.py first."
    )

recommendations = pd.read_csv(
    RECOMMENDATIONS_PATH,
    low_memory=False
)

learning = pd.read_csv(
    LEARNING_PATHWAYS_PATH,
    low_memory=False
)

print(f"Recommendations loaded: {len(recommendations)}")
print(f"Learning pathways loaded: {len(learning)}")

# ============================================================
# CLEAN OCCUPATION CODES
# ============================================================

recommendations["current_nco_code"] = (
    recommendations["current_nco_code"]
    .astype(str)
    .str.strip()
)

learning["current_nco_code"] = (
    learning["current_nco_code"]
    .astype(str)
    .str.strip()
)

# ============================================================
# FUNCTIONS
# ============================================================

def get_recommendations(occupation, top_n=5):

    occupation = occupation.lower().strip()

    # --------------------------------------------------------
    # Exact / partial occupation search
    # --------------------------------------------------------

    mask = (
        recommendations["current_occupation"]
        .astype(str)
        .str.lower()
        .str.contains(
            occupation,
            regex=False,
            na=False
        )
    )

    result = recommendations[mask].copy()

    if result.empty:
        return result

    # --------------------------------------------------------
    # Remove duplicate target occupations
    # --------------------------------------------------------

    result = result.drop_duplicates(
        subset=["current_occupation", "target_occupation"]
    )

    # --------------------------------------------------------
    # Sort by personalized score
    # --------------------------------------------------------

    result = result.sort_values(
        by="personalized_score",
        ascending=False
    )

    return result.head(top_n)


def get_learning_path(
    current_occupation,
    target_occupation
):

    current_occupation = (
        current_occupation.lower().strip()
    )

    target_occupation = (
        target_occupation.lower().strip()
    )

    mask = (
        learning["current_occupation"]
        .astype(str)
        .str.lower()
        .eq(current_occupation)
        &
        learning["target_occupation"]
        .astype(str)
        .str.lower()
        .eq(target_occupation)
    )

    result = learning[mask].copy()

    if result.empty:
        return result

    # --------------------------------------------------------
    # Remove duplicate skills
    # --------------------------------------------------------

    result = result.drop_duplicates(
        subset=["skillLabel"]
    )

    # --------------------------------------------------------
    # Priority order
    # --------------------------------------------------------

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    difficulty_order = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }

    result["priority_order"] = (
        result["skill_priority"]
        .map(priority_order)
        .fillna(99)
    )

    result["difficulty_order"] = (
        result["learning_difficulty"]
        .map(difficulty_order)
        .fillna(99)
    )

    result = result.sort_values(
        by=[
            "priority_order",
            "difficulty_order"
        ]
    )

    return result


def print_recommendation(row, rank):

    print("\n" + "-" * 70)

    print(
        f"RECOMMENDATION #{rank}"
    )

    print("-" * 70)

    print(
        f"Current Occupation : "
        f"{row['current_occupation']}"
    )

    print(
        f"Target Occupation  : "
        f"{row['target_occupation']}"
    )

    print(
        f"Match Score        : "
        f"{row['personalized_score'] * 100:.2f}%"
    )

    print(
        f"Skill Similarity   : "
        f"{row['skill_similarity'] * 100:.2f}%"
    )

    print(
        f"Missing Skills     : "
        f"{row['missing_skill_count']}"
    )

    print(
        f"Recommendation     : "
        f"{row['personalized_level']}"
    )

    print(
        f"Reason             : "
        f"{row.get('recommendation_reason', 'N/A')}"
    )

    print("\nWHY THIS TRANSITION?")

    print(
        row.get(
            "explanation",
            "No explanation available."
        )
    )

    print("\nLEARNING PLAN")

    print(
        row.get(
            "learning_plan",
            "No learning plan available."
        )
    )


# ============================================================
# DISPLAY OCCUPATIONS
# ============================================================

def show_occupations():

    occupations = (
        recommendations[
            [
                "current_nco_code",
                "current_occupation"
            ]
        ]
        .drop_duplicates()
        .sort_values("current_occupation")
    )

    print("\n" + "=" * 70)
    print("AVAILABLE OCCUPATIONS")
    print("=" * 70)

    print(
        f"Total occupations: {len(occupations)}"
    )

    for _, row in occupations.iterrows():

        print(
            f"{str(row['current_nco_code']):<8} "
            f"{row['current_occupation']}"
        )


# ============================================================
# MAIN RECOMMENDATION FUNCTION
# ============================================================

def run_system():

    print("\n" + "=" * 70)
    print("AI SKILL TRANSITION RECOMMENDATION SYSTEM")
    print("=" * 70)

    print(
        "\nEnter your current occupation."
    )

    print(
        "Example: ICT help desk agent"
    )

    occupation = input(
        "\nCurrent occupation: "
    ).strip()

    if not occupation:

        print(
            "\nOccupation cannot be empty."
        )

        return

    # --------------------------------------------------------
    # Find recommendations
    # --------------------------------------------------------

    results = get_recommendations(
        occupation,
        top_n=5
    )

    # --------------------------------------------------------
    # No result
    # --------------------------------------------------------

    if results.empty:

        print(
            "\nNo matching occupation found."
        )

        print(
            "\nTry a broader occupation name."
        )

        return

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        f"TOP CAREER TRANSITIONS FOR: "
        f"{results.iloc[0]['current_occupation']}"
    )

    print("=" * 70)

    for rank, (_, row) in enumerate(
        results.iterrows(),
        start=1
    ):

        print_recommendation(
            row,
            rank
        )

        # ----------------------------------------------------
        # Learning skills
        # ----------------------------------------------------

        pathway = get_learning_path(
            row["current_occupation"],
            row["target_occupation"]
        )

        if not pathway.empty:

            print(
                "\nKEY SKILLS TO LEARN:"
            )

            for _, skill in pathway.head(10).iterrows():

                print(
                    f"  • {skill['skillLabel']} "
                    f"| Priority: {skill['skill_priority']} "
                    f"| Difficulty: "
                    f"{skill['learning_difficulty']}"
                )

    print("\n" + "=" * 70)
    print("END OF RECOMMENDATIONS")
    print("=" * 70)


# ============================================================
# PROGRAM MENU
# ============================================================

def main():

    while True:

        print("\n")
        print("=" * 70)
        print("SKILL TRANSITION PLATFORM")
        print("=" * 70)

        print("1. Get career recommendations")
        print("2. Show available occupations")
        print("3. Exit")

        choice = input(
            "\nChoose an option: "
        ).strip()

        if choice == "1":

            run_system()

        elif choice == "2":

            show_occupations()

        elif choice == "3":

            print(
                "\nExiting Skill Transition Platform..."
            )

            break

        else:

            print(
                "\nInvalid choice. "
                "Please enter 1, 2 or 3."
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()