from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import joblib
import json
import math

app = Flask(__name__)
CORS(app)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
FEATURE_PATH = MODEL_DIR / "feature_columns.json"

# Database configuration
DATABASE_PATH = BASE_DIR / "edupredict.db"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH.as_posix()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Prediction history database table
class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"

    id = db.Column(db.Integer, primary_key=True)

    student_data = db.Column(db.Text, nullable=False)

    predicted_score = db.Column(db.Float, nullable=False)
    performance_category = db.Column(
        db.String(50), nullable=False
    )
    model_used = db.Column(db.String(100), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_data": json.loads(self.student_data),
            "predicted_score": self.predicted_score,
            "performance_category": self.performance_category,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat()
        }


# Check required model files
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

# Load exact training feature order
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


# Return model features
@app.route("/features", methods=["GET"])
def get_features():
    return jsonify({
        "features": feature_columns,
        "total_features": len(feature_columns)
    })


# Predict student exam performance and save it
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Please send student details as a JSON object."
            }), 400

        # Check required features
        missing_features = [
            column for column in feature_columns
            if column not in data
        ]

        if missing_features:
            return jsonify({
                "error": "Some required student features are missing.",
                "missing_features": missing_features
            }), 400

        # Prepare input in training column order
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

        # Generate prediction
        prediction = float(model.predict(input_df)[0])

        if not math.isfinite(prediction):
            return jsonify({
                "error": "The model returned an invalid prediction."
            }), 500

        # Keep score within 0–100
        prediction = max(0.0, min(100.0, prediction))
        prediction = round(prediction, 2)

        # Determine performance category
        if prediction >= 80:
            category = "Excellent"
        elif prediction >= 70:
            category = "Good"
        elif prediction >= 60:
            category = "Average"
        else:
            category = "Needs Improvement"

        # Save prediction to database
        record = PredictionHistory(
            student_data=json.dumps(input_data),
            predicted_score=prediction,
            performance_category=category,
            model_used=MODEL_NAME
        )

        db.session.add(record)
        db.session.commit()

        return jsonify({
            "id": record.id,
            "predicted_score": prediction,
            "performance_category": category,
            "model_used": MODEL_NAME,
            "created_at": record.created_at.isoformat()
        }), 200

    except (TypeError, ValueError) as error:
        db.session.rollback()
        return jsonify({
            "error": f"Invalid input: {error}"
        }), 400

    except Exception:
        db.session.rollback()
        app.logger.exception("Prediction failed")

        return jsonify({
            "error": "Prediction failed. Please check the server logs."
        }), 500


# Retrieve saved prediction history
@app.route("/history", methods=["GET"])
def get_history():
    try:
        records = (
            PredictionHistory.query
            .order_by(PredictionHistory.created_at.desc())
            .all()
        )

        return jsonify({
            "total": len(records),
            "history": [record.to_dict() for record in records]
        }), 200

    except Exception:
        app.logger.exception("Could not retrieve prediction history")

        return jsonify({
            "error": "Could not retrieve prediction history."
        }), 500


# Initialize database tables
with app.app_context():
    db.create_all()


# Start Flask server
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )