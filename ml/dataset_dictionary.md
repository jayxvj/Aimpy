# EduPredict dataset – data dictionary

**File:** `ml/dataset.csv` (6,606 rows, no missing values)
**Source:** Kaggle "Student Performance Factors" (lainguyn123). The data is **synthetic** – state this in the report.
**Cleaning:** see `dataset_cleaning_report.txt` and `prepare_dataset.py`.

| Column | Meaning | Type | Valid range |
|---|---|---|---|
| attendance | % of classes attended | number | 0–100 |
| previous_score | previous exam score, % | number | 0–100 |
| study_hours | study hours per week | number | 0–80 |
| tutoring_sessions | tutoring sessions per month | number | 0–30 |
| access_to_resources | availability of study materials / resources | text | Low, Medium, High |
| final_exam_score | **target**: final exam score, % | number | 0–100 |

`dataset_full_cleaned.csv` keeps all 20 original columns (lower-case names) for analytics and charts.
