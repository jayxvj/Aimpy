"""
EduPredict - dataset preparation
Source : Kaggle "Student Performance Factors" (lainguyn123), 6,607 rows, 20 columns.
         NOTE: this is a published SYNTHETIC dataset - say so in the report.
Output : ml/dataset.csv             project dataset used for training
         ml/dataset_full_cleaned.csv all 20 columns, cleaned (reference / analytics)
         ml/dataset_cleaning_report.txt

Usage:  python prepare_dataset.py
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
RAW = BASE / "raw" / "StudentPerformanceFactors.csv"

# project column name  <-  Kaggle column name
RENAME = {
    "Hours_Studied": "study_hours",          # hours per WEEK (matches the form, 0-80)
    "Attendance": "attendance",              # % of classes attended
    "Previous_Scores": "previous_score",     # %
    "Tutoring_Sessions": "tutoring_sessions",# per month
    "Access_to_Resources": "access_to_resources",  # Low / Medium / High
    "Exam_Score": "final_exam_score",        # target
}
# FINAL project fields (same order as the website form) + target
PROJECT_COLS = ["attendance", "previous_score", "study_hours",
                "tutoring_sessions", "access_to_resources", "final_exam_score"]
ACCESS_LEVELS = {"Low", "Medium", "High"}
RANGES = {"attendance": (0, 100), "previous_score": (0, 100),
          "study_hours": (0, 80), "tutoring_sessions": (0, 30),
          "final_exam_score": (0, 100)}


def main():
    log = []
    df = pd.read_csv(RAW)
    log.append(f"Raw rows: {len(df)}, columns: {df.shape[1]}")

    # 1. tidy text columns
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].astype("string").str.strip()

    # 2. exact duplicates
    n = df.duplicated().sum()
    df = df.drop_duplicates()
    log.append(f"Duplicate rows removed: {n}")

    # 3. missing values in the columns we train on -> drop those rows
    core_raw = list(RENAME)
    n = df[core_raw].isna().sum().sum()
    df = df.dropna(subset=core_raw)
    log.append(f"Rows dropped for missing values in training columns: {int(n)}")

    # 4. missing categorical values elsewhere -> 'Unknown' (not used by the model)
    other = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
    for c in other:
        df[c] = df[c].fillna("Unknown")
    log.append(f"Missing categorical values labelled 'Unknown' (reference file only): {other}")

    # 5. rename + range validation
    df = df.rename(columns=RENAME)
    bad = pd.Series(False, index=df.index)
    for c, (lo, hi) in RANGES.items():
        out = (df[c] < lo) | (df[c] > hi)
        if out.any():
            log.append(f"Out-of-range {c}: {int(out.sum())} row(s) removed "
                       f"(values {sorted(df.loc[out, c].unique().tolist())}, valid {lo}-{hi})")
        bad |= out
    bad_access = ~df["access_to_resources"].isin(ACCESS_LEVELS)
    if bad_access.any():
        log.append(f"Rows with invalid access_to_resources removed: {int(bad_access.sum())}")
    df = df[~(bad | bad_access)].reset_index(drop=True)

    # 6. snake_case the remaining columns for the reference file
    df.columns = [c.lower() for c in df.columns]

    full = df.copy()
    project = df[PROJECT_COLS].copy()
    project.to_csv(BASE / "dataset.csv", index=False)
    full.to_csv(BASE / "dataset_full_cleaned.csv", index=False)

    log.append(f"Final rows: {len(project)}")
    log.append("\nProject dataset (dataset.csv) summary:\n" + project.describe().round(2).to_string())
    (BASE / "dataset_cleaning_report.txt").write_text("\n".join(log))
    print("\n".join(log))


if __name__ == "__main__":
    main()
