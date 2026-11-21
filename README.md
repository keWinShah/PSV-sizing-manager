# PSV Sizing Manager (Python + FastAPI)

Gas, liquid and steam relief valve sizing to API 520 Part I (SI form), with API 526 orifice selection.
Engineering aid only: verify results against the relief study and the manufacturer's certified data.

## 1. Run it on your computer

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000

Run the checks: `pip install pytest` then `pytest`.

## 2. Upload to GitHub

1. Create an empty repository on github.com (for example `psv-sizing-manager`).
2. In this folder:
```bash
git init
git add .
git commit -m "PSV sizing manager"
git branch -M main
git remote add origin https://github.com/<your-username>/psv-sizing-manager.git
git push -u origin main
```
(No Git? On the GitHub repo page choose Add file, then Upload files, and drag in the folder contents.)

## 3. Deploy on Render

1. Sign in at render.com with your GitHub account.
2. Select New, then Web Service, then choose the repository.
3. Use these settings (they are also in `render.yaml`):
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance type: Free
   - Environment variable: `PYTHON_VERSION` = `3.11.9`
4. Select Create Web Service. After the build finishes you get `https://<name>.onrender.com`.
5. Every `git push` to `main` redeploys automatically.

Free instances sleep after about 15 minutes idle, so the first visit after a pause takes up to a minute.

## Adding more tools

Add a function in `psv_calc.py` (or a new module such as `line_sizing.py`), expose it with a route in `main.py`,
and add a page under `static/`. Add a test in `tests/` that reproduces a worked example from the standard.
