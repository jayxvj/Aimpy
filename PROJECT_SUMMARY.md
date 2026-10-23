# EduPredict – Summary of Member 2 (Database) and Member 3 (ML) work

## 1. Dataset
- Source: Kaggle "Student Performance Factors" (lainguyn123). **Synthetic data** – state this in the report.
- Cleaned to `ml/dataset.csv`: 6,606 rows, 6 columns, no missing values (1 impossible score of 101 removed).
- Inputs: attendance, previous_score, study_hours (per week), tutoring_sessions (per month), access_to_resources (Low/Medium/High).
- Target: final_exam_score.
- Why not the college files from sir: they were result sheets with only exam marks (no attendance or study hours),
  and the May 2020 sheet used a formula, not a real exam. Internal marks did not predict exam marks (R² ≈ 0).
- Reproduce: `ml/prepare_dataset.py`. Details: `ml/dataset_dictionary.md`, `ml/dataset_cleaning_report.txt`.

## 2. Machine learning (Member 3)
- Two models compared: Linear Regression and Random Forest. 80% train / 20% test, plus 5-fold cross-validation.
- Winner (lowest error): **Linear Regression**.

| Measure | Test set (20%) | 5-fold check |
|---|---|---|
| Within 3 marks of the real score | 97.7% | 97.2% |
| Average error (MAE) | 1.11 marks | 1.19 marks |
| R² (variation explained) | 0.711 | 0.629 |

- Compare with always guessing the class average: only 62% of guesses within 3 marks.
- A 97% R² is not possible: about 30% of the score is random noise in this synthetic data.
- Importance of each input (permutation importance): attendance 54.5%, weekly study hours 32.3%, previous score 4.8%,
  access to resources 4.6%, tutoring sessions 3.8%.
- `predict_score()` returns score, risk level, grade, confidence. `what_if()` compares before/after changes.
- Risk levels (tuned to this dataset's score range): At Risk < 63, Average 63–66, Good 67–71, Excellent 72+.
  (The old cutoffs below 40 would never trigger – no student scores below 55.)
- Confidence is a heuristic (not a statistical guarantee).

## 3. Database (Member 2)
- Tables: users, students, predictions, model_metrics, training_data (User → Students → Predictions).
- Validation on every student field, duplicate roll-number check, cascade delete of history.
- API: students CRUD, prediction history (list/delete/clear), save prediction from the predict page, model metrics saved at startup.
- SQLite by default; PostgreSQL via `DATABASE_URL` (see `database/README.md`, `database/schema.sql`).
- `backend/seed_db.py` adds demo students (fictional names).
- **Hand-over file `database/edupredict_full.sql`**: creates all tables and loads training_data (6,606 rows), 30 demo students,
  30 model predictions and the model metrics. Regenerate with `python database/export_sql.py`.

## 4. Website changes
- Predict form: now the 5 final fields; it calls the real model through `/api/predict`.
- Add-student form: now has all 5 fields.
- Students, history and dashboard load from the database (fallback to local demo data if the backend is off).
- Model-info page shows the real model, real metrics, real feature importance (invented numbers removed).
- Landing page numbers replaced with real ones.

## 5. Verified vs. not verified
- Verified here: dataset checks; training and predictions; page ↔ model data contract; SQL schema (SQLite copy);
  JavaScript syntax of all pages; website sync logic against a fake API (9 checks).
- **Not run here:** the Flask + database code (`tests/test_api.py`), because Flask-SQLAlchemy could not be installed
  in the build environment. Run it once on your computer and fix anything it reports.

## 5b. Making it start reliably on any computer
- `run.bat` / `run.sh` install the libraries and start everything; the backend serves the website at http://127.0.0.1:5000.
- "Failed to fetch" always means the backend is not running on that computer.
- The saved model rebuilds itself automatically if the computer has a different scikit-learn version.
- Predictions keep working even if the database library is missing (student/history then use local demo data).
- `psycopg2-binary` moved to `requirements-postgres.txt` (only for PostgreSQL), so the normal install cannot fail because of it.

## 6. Still for the other members
- Login / register (JWT) – Member 1.
- Real dashboard and analytics charts, class-wise analytics, recommendations engine – Members 4 and 5
  (dashboard/analytics charts still use demo numbers).
- What-if panel on the predict page (the API `/api/what-if` is ready).
