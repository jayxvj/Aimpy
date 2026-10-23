"""
EduPredict - prediction module (Member 3). The Flask backend imports this file.

    from ml.predict import predict_score, what_if, validate_input, get_model_info

predict_score({"attendance": 82, "previous_score": 70, "study_hours": 10,
               "tutoring_sessions": 2, "access_to_resources": "Medium"})
  -> {"predicted_score": 68.4, "risk": "Good", "grade": "B", "confidence": 96,
      "model_version": "LinearRegression-2026..."}
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model.pkl"
PREPROCESSING_PATH = BASE_DIR / "preprocessing.pkl"
METRICS_PATH = BASE_DIR / "metrics.json"

# Risk bands are set from THIS dataset's score range (scores run about 55-100,
# median 67), so all four bands actually occur. Change here to re-tune.
RISK_BANDS = [(72, "Excellent"), (67, "Good"), (63, "Average")]   # below 63 -> "At Risk"

_bundle = None
_prep = None


def _retrain():
    """Rebuild model.pkl from dataset.csv (takes ~20 seconds). Used when the saved model
    is missing or was built with a different scikit-learn version than this computer has."""
    import sys
    print("[EduPredict] Saved model not usable on this computer - retraining from dataset.csv ...")
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    import train
    if not (BASE_DIR / "dataset.csv").exists():
        raise FileNotFoundError("ml/dataset.csv not found - cannot train the model.")
    train.main(BASE_DIR / "dataset.csv")


def _read_saved_model():
    import sklearn
    bundle = joblib.load(MODEL_PATH)
    prep = joblib.load(PREPROCESSING_PATH)
    if bundle.get("sklearn_version") != sklearn.__version__:
        raise RuntimeError("scikit-learn version differs from the one used for training")
    # smoke test: make sure it really predicts here
    probe = pd.DataFrame([[80, 70, 10, 2, "Medium"]], columns=bundle["features"])
    bundle["model"].predict(probe)
    return bundle, prep


def _load():
    global _bundle, _prep
    if _bundle is None:
        try:
            _bundle, _prep = _read_saved_model()
        except Exception:
            _retrain()
            _bundle, _prep = _read_saved_model()
    return _bundle, _prep


def reload_model():
    """Call after retraining so a running server picks up the new model."""
    global _bundle, _prep
    _bundle = _prep = None
    return _load()


# ------------------------------------------------------------ validation
def validate_input(data):
    """Returns (clean_dict, errors_list). Use for 400 responses in the API."""
    _, prep = _load()
    clean, errors = {}, []
    for f in prep["numeric_features"]:
        if f not in data or data[f] in (None, ""):
            errors.append(f"Missing field: {f}")
            continue
        try:
            v = float(data[f])
        except (TypeError, ValueError):
            errors.append(f"{f} must be a number")
            continue
        lo, hi = prep["valid_ranges"][f]
        if not lo <= v <= hi:
            errors.append(f"{f} must be between {lo} and {hi}")
            continue
        clean[f] = v
    level = data.get("access_to_resources")
    if level in (None, ""):
        errors.append("Missing field: access_to_resources")
    else:
        level = str(level).strip().capitalize()
        if level not in prep["access_levels"]:
            errors.append("access_to_resources must be Low, Medium or High")
        else:
            clean["access_to_resources"] = level
    return clean, errors


# -------------------------------------------------------- risk / grade
def get_risk_level(score):
    for cutoff, label in RISK_BANDS:
        if score >= cutoff:
            return label
    return "At Risk"


def get_grade(score):
    for cutoff, g in [(90, "A+"), (80, "A"), (70, "B+"), (60, "B"), (50, "C"), (40, "D")]:
        if score >= cutoff:
            return g
    return "F"


def _confidence(bundle, clean):
    """Heuristic 0-100 (NOT a statistical guarantee).
    Starts from how often the model was within 3 marks on test students, and is
    lowered when the inputs are unusual compared with the training data."""
    base = 100 * bundle["within_3_marks"]
    worst_z = 0.0
    for f, st in bundle["train_stats"].items():
        if st["std"] > 0:
            worst_z = max(worst_z, abs(clean[f] - st["mean"]) / st["std"])
    penalty = min(0.30, 0.10 * max(0.0, worst_z - 2.0))
    return int(round(min(99, max(50, base * (1 - penalty)))))


# ------------------------------------------------------------ predict
def predict_score(data):
    bundle, _ = _load()
    clean, errors = validate_input(data)
    if errors:
        raise ValueError("; ".join(errors))
    x = pd.DataFrame([[clean[f] for f in bundle["features"]]], columns=bundle["features"])
    score = round(float(np.clip(bundle["model"].predict(x)[0], 0, 100)), 1)
    return {
        "predicted_score": score,
        "risk": get_risk_level(score),
        "grade": get_grade(score),
        "confidence": _confidence(bundle, clean),
        "model_version": bundle["model_version"],
    }


def what_if(current, changes):
    """Compare predictions before/after changing some inputs. All numbers come from the model."""
    before = predict_score(current)
    after = predict_score({**current, **changes})
    return {"current": before, "improved": after, "changes_applied": changes,
            "score_change": round(after["predicted_score"] - before["predicted_score"], 1)}


# ---------------------------------------------------- info for other members
FRONTEND_LABELS = {
    "attendance": "Attendance %",
    "previous_score": "Previous Exam Score",
    "study_hours": "Weekly Study Hours",
    "tutoring_sessions": "Tutoring Sessions",
    "access_to_resources": "Access to Resources",
}


def get_feature_importance():
    _load()
    return json.loads(METRICS_PATH.read_text())["feature_importance"]


def get_feature_importance_for_chart():
    imp = sorted(get_feature_importance().items(), key=lambda kv: kv[1], reverse=True)
    return {"labels": [FRONTEND_LABELS[k] for k, _ in imp],
            "values": [round(v * 100, 1) for _, v in imp]}


def get_model_info():
    """For the model-info page and the model_metrics table."""
    _load()
    r = json.loads(METRICS_PATH.read_text())
    sel = r["selected_model"]
    m = r["results"][sel]
    return {
        "model_name": sel, "model_version": r["model_version"], "trained_at": r["trained_at"],
        "training_records": r["total_records"], "train_rows": r["train_rows"], "test_rows": r["test_rows"],
        "mae": m["mae"], "rmse": m["rmse"], "r2_score": m["r2_score"],
        "within_3_marks": m["within_3_marks"],
        "cv_r2_score": m["cv_r2_score"], "cv_mae": m["cv_mae"], "cv_within_3_marks": m["cv_within_3_marks"],
        "all_models": r["results"], "data_note": r.get("data_note", ""),
        "features": [FRONTEND_LABELS[f] for f in FRONTEND_LABELS],
    }


if __name__ == "__main__":
    sample = {"attendance": 82, "previous_score": 70, "study_hours": 10,
              "tutoring_sessions": 2, "access_to_resources": "Medium"}
    print(predict_score(sample))
    print(what_if(sample, {"attendance": 95, "study_hours": 18}))
