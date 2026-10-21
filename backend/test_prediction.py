import json
from pathlib import Path
import pandas as pd
import joblib

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "model" / "best_model.joblib"
FEATURE_PATH = BASE_DIR / "model" / "feature_columns.json"
DATA_PATH = BASE_DIR / "dataset" / "cleaned_student_data.csv"

# Load trained model
model = joblib.load(MODEL_PATH)

# Load feature names
with open(FEATURE_PATH, "r", encoding="utf-8") as file:
    features = json.load(file)

# Load one real student record for testing
df = pd.read_csv(DATA_PATH)
student = df[features].iloc[[0]]

# Predict score
prediction = model.predict(student)[0]

print("\n========== EDUPREDICT TEST ==========")

print("\nStudent input:")
print(student.to_string(index=False))

print("\nPredicted Exam Score:", round(float(prediction), 2))

print(
    "Actual Exam Score:",
    df["Exam_Score"].iloc[0]
)

print("\nTest completed successfully!")