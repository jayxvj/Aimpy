from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import pandas as pd
import joblib
import json
import math

app = Flask(__name__)

# Allow frontend requests during local development
CORS(app)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_DIR = BASE_DIR / "model"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
FEATURE_PATH = MODEL_DIR / "feature_columns.json"

# Check that required model files exist
if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_PATH}"
    )

if not FEATURE_PATH.exists():
    raise FileNotFoundError(
        f"Feature columns file not found: {FEATURE_PATH}"
    )

# Load trained model
model = joblib.load(MODEL_PATH)
MODEL_NAME = "Linear Regression"

# Load the exact training feature order
with open(FEATURE_PATH, "r", encoding="utf-8") as file:
    feature_columns = json.load(file)

if not isinstance(feature_columns, list) or not feature_columns:
    raise ValueError(
        "feature_columns.json must contain a non-empty list."
    )


# Home endpoint
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "EduPredict ML API is running!",
        "model": MODEL_NAME,
        "status": "online"
    })


# Return the features required by the model
@app.route("/features", methods=["GET"])
def get_features():
    return jsonify({
        "features": feature_columns,
        "total_features": len(feature_columns)
    })


# Predict student exam performance
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)

        # Validate JSON body
        if not isinstance(data, dict):
            return jsonify({
                "error": "Please send student details as a JSON object."
            }), 400

        # Check for missing model inputs
        missing_features = [
            column
            for column in feature_columns
            if column not in data
        ]

        if missing_features:
            return jsonify({
                "error": "Some required student features are missing.",
                "missing_features": missing_features
            }), 400

        # Prepare input using the exact training column order
        input_data = {
            column: data[column]
            for column in feature_columns
        }

        input_df = pd.DataFrame([input_data])

        # Check missing values
        if input_df.isnull().any().any():
            return jsonify({
                "error": "Input contains missing values. Please complete all required fields."
            }), 400

        # Predict exam score
        prediction = float(model.predict(input_df)[0])

        if not math.isfinite(prediction):
            return jsonify({
                "error": "The model returned an invalid prediction."
            }), 500

        # Keep score within the configured 0–100 range
        prediction = max(0.0, min(100.0, prediction))

        # Performance categories for demonstration
        if prediction >= 80:
            category = "Excellent"
        elif prediction >= 70:
            category = "Good"
        elif prediction >= 60:
            category = "Average"
        else:
            category = "Needs Improvement"

        return jsonify({
            "predicted_score": round(prediction, 2),
            "performance_category": category,
            "model_used": "Linear Regression"
        }), 200

    except (TypeError, ValueError) as error:
        return jsonify({
            "error": f"Invalid input: {error}"
        }), 400

    except Exception:
        app.logger.exception("Prediction failed")

        return jsonify({
            "error": "Prediction failed. Please check the server logs."
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )