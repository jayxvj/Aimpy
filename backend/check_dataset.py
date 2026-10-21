import pandas as pd
from pathlib import Path

# Locate the dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "Student Performance Factors.csv"

# Check if the dataset exists
if not DATASET_PATH.exists():
    print("ERROR: Dataset file not found!")
    print("Expected location:", DATASET_PATH)
else:
    # Load the dataset
    df = pd.read_csv(DATASET_PATH)

    print("\n========== DATASET LOADED SUCCESSFULLY ==========")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nDataset shape (rows, columns):")
    print(df.shape)

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nMissing values in each column:")
    print(df.isnull().sum())

    print("\nDataset information:")
    df.info()

    print("\nTarget variable check:")
    if "Exam_Score" in df.columns:
        print("Exam_Score is available!")
        print(df["Exam_Score"].describe())
    else:
        print("Exam_Score column was not found.")
        print("Please check the column names above.")
