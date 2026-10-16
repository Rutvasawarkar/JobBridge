import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# PATHS
# ============================================================

INPUT_PATH = "data/transition_candidates.csv"
MODEL_PATH = "data/transition_model.pkl"


# ============================================================
# LOAD DATA
# ============================================================

print("LOADING DATA")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH,
    low_memory=False
)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# SELECT FEATURES
# ============================================================

print("\nSELECTING FEATURES")
print("=" * 60)

features = [
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "common_skill_count",
    "skill_gap_score",
    "same_isco_group"
]

target = "transition_score"


# Check required columns
required_columns = features + [target]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}"
    )


# ============================================================
# PREPARE FEATURES
# ============================================================

X = df[features].copy()
y = df[target].copy()


# Convert boolean to integer
X["same_isco_group"] = X["same_isco_group"].astype(int)


# Convert numeric columns
numeric_columns = [
    "skill_similarity",
    "missing_skill_count",
    "target_skill_count",
    "common_skill_count",
    "skill_gap_score"
]

for col in numeric_columns:
    X[col] = pd.to_numeric(
        X[col],
        errors="coerce"
    )


# Remove invalid rows
valid = X.notna().all(axis=1) & y.notna()

X = X[valid]
y = y[valid]


print(f"Valid training rows: {len(X)}")


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

print("\nTRAIN / TEST SPLIT")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print(f"Training rows: {len(X_train)}")
print(f"Testing rows:  {len(X_test)}")


# ============================================================
# TRAIN RANDOM FOREST
# ============================================================

print("\nTRAINING TRANSITION MODEL")
print("=" * 60)

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=12,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)


# ============================================================
# PREDICTIONS
# ============================================================

print("\nEVALUATING MODEL")
print("=" * 60)

y_pred = model.predict(X_test)


# ============================================================
# METRICS
# ============================================================

mae = mean_absolute_error(
    y_test,
    y_pred
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        y_pred
    )
)

r2 = r2_score(
    y_test,
    y_pred
)

print(f"MAE : {mae:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"R²  : {r2:.4f}")


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\nFEATURE IMPORTANCE")
print("=" * 60)

importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print(importance.to_string(index=False))


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)

print("\nMODEL SAVED")
print("=" * 60)

print(f"File: {MODEL_PATH}")