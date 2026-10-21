import pandas as pd
import json
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer

from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor

from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error, r2_score

import joblib


# =====================================
# 1. SET PATHS
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "dataset" / "cleaned_student_data.csv"
MODEL_DIR = BASE_DIR / "model"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# =====================================
# 2. LOAD DATASET
# =====================================

df = pd.read_csv(DATA_PATH)

print("Dataset loaded successfully!")
print("Dataset shape:", df.shape)


# =====================================
# 3. DEFINE FEATURES AND TARGET
# =====================================

TARGET = "Exam_Score"

X = df.drop(columns=[TARGET])
y = df[TARGET]

print("\nNumber of features:", X.shape[1])
print("Target variable:", TARGET)


# =====================================
# 4. IDENTIFY COLUMN TYPES
# =====================================

numeric_features = X.select_dtypes(
    include=["number"]
).columns.tolist()

categorical_features = X.select_dtypes(
    exclude=["number"]
).columns.tolist()

print("\nNumeric features:", numeric_features)
print("\nCategorical features:", categorical_features)


# =====================================
# 5. PREPROCESSING
# =====================================

numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median"))
])

categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer(transformers=[
    ("numeric", numeric_transformer, numeric_features),
    ("categorical", categorical_transformer, categorical_features)
])


# =====================================
# 6. SPLIT DATA
# =====================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# =====================================
# 7. DEFINE MODELS
# =====================================

models = {
    "Linear Regression": LinearRegression(),

    "Decision Tree": DecisionTreeRegressor(
        max_depth=10,
        random_state=42
    ),

    "Random Forest": RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    )
}


# =====================================
# 8. TRAIN AND EVALUATE
# =====================================

results = []
trained_models = {}

for name, algorithm in models.items():

    print(f"\nTraining {name}...")

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", algorithm)
    ])

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)

    rmse = mean_squared_error(
        y_test,
        predictions
    ) ** 0.5

    r2 = r2_score(y_test, predictions)

    results.append({
        "Model": name,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    })

    trained_models[name] = pipeline

    print("MAE:", round(mae, 3))
    print("RMSE:", round(rmse, 3))
    print("R2:", round(r2, 3))


# =====================================
# 9. COMPARE RESULTS
# =====================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="MAE",
    ascending=True
)

print("\n=================================")
print("MODEL COMPARISON")
print("=================================")

print(results_df.to_string(index=False))


# =====================================
# 10. SAVE RESULTS
# =====================================

results_df.to_csv(
    MODEL_DIR / "model_comparison.csv",
    index=False
)

# Select the model with the lowest MAE
best_model_name = results_df.iloc[0]["Model"]

best_model = trained_models[best_model_name]

joblib.dump(
    best_model,
    MODEL_DIR / "best_model.joblib"
)

# Save the exact input column order
with open(
    MODEL_DIR / "feature_columns.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(X.columns.tolist(), file, indent=4)

print("\n=================================")
print("BEST MODEL:", best_model_name)
print("=================================")

print("\nSaved files:")
print("1. model/best_model.joblib")
print("2. model/model_comparison.csv")
print("3. model/feature_columns.json")

print("\nModel training completed successfully!")