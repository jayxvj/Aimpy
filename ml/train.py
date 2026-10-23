"""
EduPredict - ML training pipeline (Member 3)

Dataset (ml/dataset.csv) -> clean -> split 80/20 -> Linear Regression + Random Forest
-> evaluate (MAE, RMSE, R2, % within 3 marks, 5-fold cross-validation)
-> pick best by RMSE -> save model.pkl, preprocessing.pkl, metrics.json

Final input fields (same as the website form):
  attendance, previous_score, study_hours, tutoring_sessions, access_to_resources
Target: final_exam_score

Usage:  python train.py [path_to_dataset.csv]
"""
import sys
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset.csv"
MODEL_PATH = BASE_DIR / "model.pkl"
PREPROCESSING_PATH = BASE_DIR / "preprocessing.pkl"
METRICS_PATH = BASE_DIR / "metrics.json"

NUMERIC_FEATURES = ["attendance", "previous_score", "study_hours", "tutoring_sessions"]
CATEGORICAL_FEATURES = ["access_to_resources"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "final_exam_score"
ACCESS_LEVELS = ["Low", "Medium", "High"]

VALID_RANGES = {
    "attendance": (0, 100),
    "previous_score": (0, 100),
    "study_hours": (0, 80),          # hours per week
    "tutoring_sessions": (0, 30),    # sessions per month
    "final_exam_score": (0, 100),
}
RANDOM_STATE = 42
TOLERANCE = 3                        # "accurate" = within 3 marks of the real score


# ---------------------------------------------------------------- data
def load_dataset(path=DATASET_PATH):
    df = pd.read_csv(path)
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}. Expected: {FEATURES + [TARGET]}")
    return df[FEATURES + [TARGET]]


def clean_data(df):
    """Coerce types, drop rows with missing / out-of-range / invalid values.
    (Duplicate rows are kept: two different students can have identical values.)"""
    df = df.copy()
    for col in NUMERIC_FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["access_to_resources"] = df["access_to_resources"].astype(str).str.strip().str.capitalize()
    df = df.dropna(subset=FEATURES + [TARGET])
    for col, (lo, hi) in VALID_RANGES.items():
        df = df[(df[col] >= lo) & (df[col] <= hi)]
    df = df[df["access_to_resources"].isin(ACCESS_LEVELS)]
    return df.reset_index(drop=True)


def prepare_features(df):
    return df[FEATURES], df[TARGET]


def split_data(X, y, test_size=0.2):
    return train_test_split(X, y, test_size=test_size, random_state=RANDOM_STATE)


# -------------------------------------------------------------- models
def _preprocessor():
    return ColumnTransformer(
        [("access", OneHotEncoder(categories=[ACCESS_LEVELS]), CATEGORICAL_FEATURES)],
        remainder="passthrough",
    )


def build_linear_regression():
    return Pipeline([("prep", _preprocessor()), ("model", LinearRegression())])


def build_random_forest():
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                               random_state=RANDOM_STATE, n_jobs=-1)
    return Pipeline([("prep", _preprocessor()), ("model", rf)])


def train_linear_regression(X_train, y_train):
    return build_linear_regression().fit(X_train, y_train)


def train_random_forest(X_train, y_train):
    return build_random_forest().fit(X_train, y_train)


def _metrics(y_true, pred):
    err = np.abs(np.asarray(y_true) - np.asarray(pred))
    return {
        "mae": float(mean_absolute_error(y_true, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, pred))),
        "r2_score": float(r2_score(y_true, pred)),
        "within_3_marks": float((err <= TOLERANCE).mean()),
        "within_5_marks": float((err <= 5).mean()),
    }


def evaluate_model(model, X_test, y_test):
    return _metrics(y_test, np.clip(model.predict(X_test), 0, 100))


def cross_validate_model(builder, X, y, folds=5):
    """5-fold cross-validation: every student is predicted by a model that never saw them."""
    pred = cross_val_predict(builder(), X, y, cv=KFold(folds, shuffle=True, random_state=RANDOM_STATE))
    return _metrics(y, np.clip(pred, 0, 100))


def select_best_model(results):
    """Lowest RMSE on the test set wins."""
    return min(results, key=lambda n: results[n]["metrics"]["rmse"])


def get_feature_importance(model, X_test, y_test):
    """Permutation importance: how much the error grows when one input is shuffled.
    Works for any model and keeps 'access_to_resources' as one feature."""
    r = permutation_importance(model, X_test, y_test, n_repeats=10,
                               random_state=RANDOM_STATE, scoring="neg_mean_squared_error")
    imp = np.clip(r.importances_mean, 0, None)
    imp = imp / imp.sum() if imp.sum() > 0 else imp
    return {f: float(v) for f, v in zip(FEATURES, imp)}


def save_model(name, model, metrics, X_train):
    version = f"{name}-{datetime.now().strftime('%Y%m%d%H%M')}"
    stats = {c: {"mean": float(X_train[c].mean()), "std": float(X_train[c].std())}
             for c in NUMERIC_FEATURES}
    joblib.dump({
        "model": model, "model_name": name, "model_version": version,
        "features": FEATURES, "rmse": metrics["rmse"], "r2_score": metrics["r2_score"],
        "within_3_marks": metrics["within_3_marks"], "train_stats": stats,
        "sklearn_version": sklearn.__version__,
    }, MODEL_PATH)
    joblib.dump({
        "features": FEATURES, "numeric_features": NUMERIC_FEATURES,
        "valid_ranges": {k: VALID_RANGES[k] for k in NUMERIC_FEATURES},
        "access_levels": ACCESS_LEVELS,
    }, PREPROCESSING_PATH)
    return version


# ---------------------------------------------------------------- main
def main(dataset_path=DATASET_PATH):
    raw = load_dataset(dataset_path)
    df = clean_data(raw)
    print(f"Loaded {len(raw)} rows, {len(df)} after cleaning")

    X, y = prepare_features(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    builders = {"LinearRegression": build_linear_regression, "RandomForest": build_random_forest}
    results = {}
    for name, builder in builders.items():
        model = builder().fit(X_train, y_train)
        m = evaluate_model(model, X_test, y_test)
        cv = cross_validate_model(builder, X, y)
        results[name] = {"model": model, "metrics": m, "cv": cv}
        print(f"{name:17s} TEST  MAE={m['mae']:.2f} RMSE={m['rmse']:.2f} R2={m['r2_score']:.3f} "
              f"within3={100*m['within_3_marks']:.1f}%")
        print(f"{'':17s} 5-FOLD MAE={cv['mae']:.2f} RMSE={cv['rmse']:.2f} R2={cv['r2_score']:.3f} "
              f"within3={100*cv['within_3_marks']:.1f}%")

    best = select_best_model(results)
    best_model = results[best]["model"]
    print(f"\nSelected model: {best}")
    version = save_model(best, best_model, results[best]["metrics"], X_train)

    report = {
        "selected_model": best, "model_version": version,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(dataset_path), "total_records": int(len(df)),
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "tolerance_marks": TOLERANCE,
        "results": {n: {**r["metrics"], **{"cv_" + k: v for k, v in r["cv"].items()}}
                    for n, r in results.items()},
        "feature_importance": get_feature_importance(best_model, X_test, y_test),
        "data_note": "Synthetic dataset (Kaggle 'Student Performance Factors'). "
                     "Scores describe this dataset, not real students.",
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2))
    print(f"Saved: {MODEL_PATH.name}, {PREPROCESSING_PATH.name}, {METRICS_PATH.name}")
    return report


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DATASET_PATH)
