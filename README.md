# EduPredict – Predictive Analytics in Education

Predicts a student's final exam score from 5 factors, flags academic risk, and stores students and
prediction history in a database.

## Folder guide
| Folder | What is inside |
|---|---|
| `frontend/` | the website pages (HTML/CSS/JS) – already connected to the backend |
| `backend/` | Flask API (`app.py`), database tables (`models.py`), database functions (`services/db_service.py`), demo data (`seed_db.py`) |
| `ml/` | dataset, training (`train.py`), prediction (`predict.py`), saved model (`model.pkl`) and results (`metrics.json`) |
| `database/` | PostgreSQL schema + database guide |
| `tests/` | `test_api.py` (backend + database) and `test_frontend_sync.js` (website sync) |

## Run it
**Easiest (Windows):** double-click **`run.bat`**. It installs the libraries (first time, needs internet), starts the
backend and opens the website at **http://127.0.0.1:5000**. (Mac/Linux: `bash run.sh`.)

**Manual:**
1. `pip install -r requirements.txt`
2. `cd backend` then `python app.py`   (keep this window open)
3. Open **http://127.0.0.1:5000** in the browser. Always open the site from this address, not by double-clicking the HTML files.

The backend serves the website too, so there is nothing else to start.

**Seeing "Failed to fetch" or "Cannot reach the backend"?** The backend is not running on that computer.
Start it with `run.bat` and open http://127.0.0.1:5000. See "If something goes wrong" below.

## Retrain the model
`cd ml` then `python train.py` – reads `dataset.csv`, trains two models, saves the best one.
To rebuild the dataset from the raw Kaggle file: `python prepare_dataset.py`.

## Tests
- `python tests/test_api.py`  (needs the pip packages installed)
- `node tests/test_frontend_sync.js`

## The 5 input fields
attendance %, previous exam score %, weekly study hours, tutoring sessions per month, access to resources (Low/Medium/High).

## If something goes wrong
| Problem | Fix |
|---|---|
| "Failed to fetch" / "Cannot reach the backend" | Backend not running. Double-click `run.bat`, wait for "EduPredict is running", then open http://127.0.0.1:5000 |
| `python` is not recognized | Install Python from python.org and tick "Add Python to PATH" (or the script tries `py`) |
| First start takes ~20 seconds | Normal: if the saved model was built with another scikit-learn version, it is rebuilt automatically from `ml/dataset.csv` |
| Window says "database not available" | Predictions still work. Run `pip install -r requirements.txt` again, then restart |
| Port 5000 busy | Close the other program using it (or other copies of the backend) and start again |
