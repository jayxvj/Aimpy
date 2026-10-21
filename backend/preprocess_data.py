import pandas as pd
from pathlib import Path

# Set file paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "Student Performance Factors.csv"
OUTPUT_PATH = BASE_DIR / "dataset" / "cleaned_student_data.csv"

# Load dataset
df = pd.read_csv(DATASET_PATH)

print("Original dataset shape:", df.shape)

# Remove duplicate records
df = df.drop_duplicates()

# Handle missing values
for column in df.columns:
    if df[column].isnull().any():

        # Numerical columns: fill with median
        if pd.api.types.is_numeric_dtype(df[column]):
            df[column] = df[column].fillna(df[column].median())

        # Categorical columns: fill with most frequent value
        else:
            df[column] = df[column].fillna(
                df[column].mode()[0]
            )

# Check target variable
if "Exam_Score" not in df.columns:
    raise ValueError("Exam_Score target column not found!")

# Remove rows with missing target values, if any
df = df.dropna(subset=["Exam_Score"])

# Save cleaned dataset
df.to_csv(OUTPUT_PATH, index=False)

print("\nData cleaning completed!")
print("Cleaned dataset shape:", df.shape)
print("\nRemaining missing values:")
print(df.isnull().sum())

print("\nTarget variable summary:")
print(df["Exam_Score"].describe())

print("\nCleaned dataset saved at:")
print(OUTPUT_PATH)