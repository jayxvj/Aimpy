import sqlite3
import random
import string
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "auth.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
    """)
    conn.commit()
    conn.close()

def generate_unique_id():
    # Format: EDU-YEAR-RANDOM5 e.g. EDU-2026-84920
    digits = ''.join(random.choices(string.digits, k=5))
    return f"EDU-2026-{digits}"

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "service": "EduPredict Auth Service",
        "version": "1.0.0"
    })

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
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

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "error": "Admin ID / Username already registered. Please login."}), 409

    # Generate unique ID and ensure uniqueness
    unique_id = generate_unique_id()
    while True:
        cursor.execute("SELECT id FROM users WHERE unique_id = ?", (unique_id,))
        if not cursor.fetchone():
            break
        unique_id = generate_unique_id()

    # Hash the password - never store plain text!
    password_hash = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT INTO users (unique_id, username, password_hash, name, college_name, branch, year, location, profile_pic, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (unique_id, username, password_hash, name, college_name, branch, year, location, profile_pic, created_at))
    conn.commit()
    conn.close()

    # Note: As requested, after register user must login.
    return jsonify({
        "success": True,
        "message": "Account registered successfully! Please log in with your credentials.",
        "unique_id": unique_id
    }), 201

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "Admin ID and password are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "Invalid Admin ID or password"}), 401

    if not check_password_hash(row["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid Admin ID or password"}), 401

    # Return sanitized profile without password
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

@app.route("/auth/profile/<unique_id>", methods=["GET"])
def get_profile(unique_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE unique_id = ?", (unique_id,))
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
def update_profile():
    data = request.get_json() or {}
    unique_id = data.get("unique_id")
    if not unique_id:
        return jsonify({"success": False, "error": "User Unique ID is required"}), 400

    name = (data.get("name") or "").strip()
    college_name = (data.get("college_name") or "").strip()
    branch = (data.get("branch") or "").strip()
    year = (data.get("year") or "").strip()
    location = (data.get("location") or "").strip()
    profile_pic = data.get("profile_pic")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE unique_id = ?", (unique_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "error": "User not found"}), 404

    # Keep existing profile pic if not provided in payload
    final_pic = profile_pic if profile_pic is not None else row["profile_pic"]

    cursor.execute("""
    UPDATE users
    SET name = ?, college_name = ?, branch = ?, year = ?, location = ?, profile_pic = ?
    WHERE unique_id = ?
    """, (name or row["name"], college_name, branch, year, location, final_pic, unique_id))
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE unique_id = ?", (unique_id,))
    updated_row = cursor.fetchone()
    conn.close()

    updated_user = {
        "unique_id": updated_row["unique_id"],
        "username": updated_row["username"],
        "name": updated_row["name"],
        "college_name": updated_row["college_name"] or "",
        "branch": updated_row["branch"] or "",
        "year": updated_row["year"] or "",
        "location": updated_row["location"] or "",
        "profile_pic": updated_row["profile_pic"] or "",
        "created_at": updated_row["created_at"]
    }

    return jsonify({
        "success": True,
        "message": "Profile updated successfully",
        "user": updated_user
    })

if __name__ == "__main__":
    init_db()
    print("Starting EduPredict Auth Service on port 5001...")
    app.run(host="127.0.0.1", port=5001, debug=False)
