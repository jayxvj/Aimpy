from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import shutil
import pandas as pd
import joblib
import json
import math
import sqlite3
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
FEATURE_PATH = MODEL_DIR / "feature_columns.json"
FRONTEND_DIR = BASE_DIR / "frontend"

# Database configuration: support writable /tmp on serverless environments like Vercel
if os.environ.get("VERCEL"):
    TMP_DIR = Path("/tmp")
    tmp_edupredict = TMP_DIR / "edupredict.db"
    tmp_auth = TMP_DIR / "auth.db"

    # Copy bundled database to /tmp if not already present
    if not tmp_edupredict.exists() and (BASE_DIR / "edupredict.db").exists():
        try:
            shutil.copy2(BASE_DIR / "edupredict.db", tmp_edupredict)
        except Exception:
            pass
    if not tmp_auth.exists() and (BASE_DIR / "auth.db").exists():
        try:
            shutil.copy2(BASE_DIR / "auth.db", tmp_auth)
        except Exception:
            pass

    DATABASE_PATH = tmp_edupredict
    AUTH_DB_PATH = tmp_auth
else:
    DATABASE_PATH = BASE_DIR / "edupredict.db"
    AUTH_DB_PATH = BASE_DIR / "auth.db"

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


# Home endpoint - serves frontend/index.html or API status
@app.route("/", methods=["GET"])
def home():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "message": "EduPredict ML API is running!",
        "model": MODEL_NAME,
        "status": "online"
    })


@app.route("/api", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def api_health():
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


# Model comparison endpoint for benchmark pop-up
@app.route("/api/model-comparison", methods=["GET"])
def model_comparison():
    comparison_csv = BASE_DIR / "model" / "model_comparison.csv"
    models_data = []

    if comparison_csv.exists():
        try:
            df = pd.read_csv(comparison_csv)
            for row in df.to_dict(orient="records"):
                is_win = (row.get("Model") == "Linear Regression")
                models_data.append({
                    "Model": row.get("Model"),
                    "MAE": round(float(row.get("MAE", 0)), 4),
                    "RMSE": round(float(row.get("RMSE", 0)), 4),
                    "R2": round(float(row.get("R2", 0)), 4),
                    "AccuracyPct": round(float(row.get("R2", 0)) * 100, 2),
                    "IsWinner": is_win
                })
        except Exception as e:
            print(f"Error reading model_comparison.csv: {e}")

    if not models_data:
        models_data = [
            {"Model": "Linear Regression", "MAE": 0.4524, "RMSE": 1.8044, "R2": 0.7696, "AccuracyPct": 76.96, "IsWinner": True},
            {"Model": "Gradient Boosting", "MAE": 0.7918, "RMSE": 1.9416, "R2": 0.7333, "AccuracyPct": 73.33, "IsWinner": False},
            {"Model": "Random Forest", "MAE": 1.0900, "RMSE": 2.1599, "R2": 0.6699, "AccuracyPct": 66.99, "IsWinner": False},
            {"Model": "Decision Tree", "MAE": 1.6553, "RMSE": 3.2952, "R2": 0.2318, "AccuracyPct": 23.18, "IsWinner": False}
        ]

    return jsonify({
        "status": "success",
        "selected_model": "Linear Regression",
        "models": models_data,
        "key_reasons": [
            {
                "title": "Superior Variance Explained (Highest R² = 76.96%)",
                "description": "Linear Regression captures ~77% of all variance in student performance, outperforming Gradient Boosting (73.33%) and Random Forest (66.99%)."
            },
            {
                "title": "Lowest Prediction Error (MAE = 0.45 Marks)",
                "description": "Average prediction error is just 0.45 marks—more than 2.4x more accurate than Random Forest (1.09 marks) and 3.6x more accurate than Decision Tree (1.66 marks)."
            },
            {
                "title": "Continuous Scaling vs. Step-Function Artifacts",
                "description": "Study hours and attendance improve student outcomes linearly. Tree models create discontinuous threshold cutoffs causing unfair score cliffs."
            },
            {
                "title": "Complete Explainability & Zero Overfitting Risk",
                "description": "Direct coefficient interpretability allows counselors to explain exact causes, while tree ensembles overfit easily on small institution samples."
            }
        ]
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


# -------------------- AUTHENTICATION ROUTES (auth.db) --------------------
def get_auth_db_connection():
    conn = sqlite3.connect(AUTH_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def init_auth_db():
    create_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        college_name TEXT,
        branch TEXT,
        year TEXT,
        location TEXT,
        profile_pic TEXT,
        created_at TEXT NOT NULL
    );
    """
    for db_path in [AUTH_DB_PATH, DATABASE_PATH]:
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(create_sql)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"init_auth_db error on {db_path}: {e}")

    # Synchronize users from auth.db into edupredict.db so both databases match exactly
    try:
        auth_conn = get_auth_db_connection()
        auth_users = auth_conn.execute("SELECT * FROM users").fetchall()
        auth_conn.close()

        edu_conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        edu_conn.row_factory = sqlite3.Row
        for u in auth_users:
            edu_conn.execute("""
            INSERT OR REPLACE INTO users (id, unique_id, username, password_hash, name, college_name, branch, year, location, profile_pic, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (u["id"], u["unique_id"], u["username"], u["password_hash"], u["name"], u["college_name"], u["branch"], u["year"], u["location"], u["profile_pic"], u["created_at"]))
        edu_conn.commit()
        edu_conn.close()
    except Exception as e:
        print(f"User sync error: {e}")

def generate_unique_id():
    digits = ''.join(random.choices(string.digits, k=5))
    return f"EDU-2026-{digits}"

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/auth/<path:subpath>", methods=["OPTIONS"])
def auth_options(subpath):
    return "", 200

@app.route("/auth/health", methods=["GET"])
def auth_health():
    return jsonify({
        "status": "online",
        "service": "EduPredict Auth Service (Port 5000)",
        "version": "1.0.0"
    })

@app.route("/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    college_name = (data.get("college_name") or "").strip()
    branch = (data.get("branch") or "").strip()
    year = (data.get("year") or "").strip()
    location = (data.get("location") or "").strip()
    profile_pic = data.get("profile_pic") or ""

    if not username:
        return jsonify({"success": False, "error": "Admin ID / Username is required"}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required"}), 400
    if len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
    if not name:
        return jsonify({"success": False, "error": "Full Name is required"}), 400

    conn = get_auth_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Admin ID / Username already registered. Please login."}), 409

    unique_id = generate_unique_id()
    while True:
        cursor.execute("SELECT id FROM users WHERE unique_id = ?", (unique_id,))
        if not cursor.fetchone():
            break
        unique_id = generate_unique_id()

    password_hash = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat()

    # Save to both auth.db and edupredict.db to ensure single-source data consistency
    for db_path in [AUTH_DB_PATH, DATABASE_PATH]:
        try:
            d_conn = sqlite3.connect(db_path, timeout=30.0)
            d_conn.execute("""
            INSERT OR REPLACE INTO users (unique_id, username, password_hash, name, college_name, branch, year, location, profile_pic, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (unique_id, username, password_hash, name, college_name, branch, year, location, profile_pic, created_at))
            d_conn.commit()
            d_conn.close()
        except Exception as e:
            print(f"Error saving user to {db_path}: {e}")

    return jsonify({
        "success": True,
        "message": "Account registered successfully! Please log in with your credentials.",
        "unique_id": unique_id
    }), 201

@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "Admin ID and password are required"}), 400

    conn = get_auth_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "Invalid Admin ID or password"}), 401

    if not check_password_hash(row["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid Admin ID or password"}), 401

    user_data = {
        "unique_id": row["unique_id"],
        "username": row["username"],
        "name": row["name"],
        "college_name": row["college_name"] or "",
        "branch": row["branch"] or "",
        "year": row["year"] or "",
        "location": row["location"] or "",
        "profile_pic": row["profile_pic"] or "",
        "created_at": row["created_at"]
    }

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": user_data
    })

@app.route("/auth/profile/<identifier>", methods=["GET"])
def auth_get_profile(identifier):
    conn = get_auth_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE unique_id = ? OR LOWER(username) = LOWER(?)", (identifier, identifier))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "User not found"}), 404

    user_data = {
        "unique_id": row["unique_id"],
        "username": row["username"],
        "name": row["name"],
        "college_name": row["college_name"] or "",
        "branch": row["branch"] or "",
        "year": row["year"] or "",
        "location": row["location"] or "",
        "profile_pic": row["profile_pic"] or "",
        "created_at": row["created_at"]
    }
    return jsonify({"success": True, "user": user_data})

@app.route("/auth/profile", methods=["PUT"])
def auth_update_profile():
    try:
        data = request.get_json(silent=True) or {}
        unique_id = (data.get("unique_id") or "").strip()
        username = (data.get("username") or "").strip()

        if not unique_id and not username:
            return jsonify({"success": False, "error": "User identifier is required"}), 400

        name = (data.get("name") or "").strip()
        college_name = (data.get("college_name") or "").strip()
        branch = (data.get("branch") or "").strip()
        year = (data.get("year") or "").strip()
        location = (data.get("location") or "").strip()
        profile_pic = data.get("profile_pic")

        conn = get_auth_db_connection()
        cursor = conn.cursor()
        if unique_id:
            cursor.execute("SELECT * FROM users WHERE unique_id = ?", (unique_id,))
        else:
            cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({"success": False, "error": "User not found"}), 404

        current_data = dict(row)
        target_uid = current_data["unique_id"]
        final_name = name or current_data["name"]
        final_pic = profile_pic if profile_pic is not None else current_data.get("profile_pic", "")

        cursor.execute("""
        UPDATE users
        SET name = ?, college_name = ?, branch = ?, year = ?, location = ?, profile_pic = ?
        WHERE unique_id = ?
        """, (final_name, college_name, branch, year, location, final_pic, target_uid))
        conn.commit()

        cursor.execute("SELECT * FROM users WHERE unique_id = ?", (target_uid,))
        updated_row = cursor.fetchone()
        updated_dict = dict(updated_row) if updated_row else current_data
        conn.close()

        # Also update edupredict.db so both databases remain identical
        try:
            edu_conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
            edu_conn.execute("""
            UPDATE users
            SET name = ?, college_name = ?, branch = ?, year = ?, location = ?, profile_pic = ?
            WHERE unique_id = ?
            """, (final_name, college_name, branch, year, location, final_pic, target_uid))
            edu_conn.commit()
            edu_conn.close()
        except Exception as sync_err:
            print(f"Sync error to edupredict.db: {sync_err}")

        updated_user = {
            "unique_id": updated_dict["unique_id"],
            "username": updated_dict["username"],
            "name": updated_dict["name"],
            "college_name": updated_dict.get("college_name") or "",
            "branch": updated_dict.get("branch") or "",
            "year": updated_dict.get("year") or "",
            "location": updated_dict.get("location") or "",
            "profile_pic": updated_dict.get("profile_pic") or "",
            "created_at": updated_dict["created_at"]
        }

        return jsonify({
            "success": True,
            "message": "Profile updated successfully in database",
            "user": updated_user
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to update profile: {str(e)}"}), 500


# Serve static frontend files (predict.html, analytics.html, css, js, assets, etc.)
@app.route("/<path:filename>", methods=["GET"])
def serve_frontend_file(filename):
    file_path = FRONTEND_DIR / filename
    if file_path.is_file():
        return send_from_directory(FRONTEND_DIR, filename)
    html_file = FRONTEND_DIR / f"{filename}.html"
    if html_file.is_file():
        return send_from_directory(FRONTEND_DIR, f"{filename}.html")
    return jsonify({"error": "Resource not found"}), 404


# Initialize database tables
with app.app_context():
    db.create_all()
    init_auth_db()


# Start Flask server
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )