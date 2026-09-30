# Deploying as a Databricks App (what worked on 2026-09-30)

The repo already carries `app.yaml` (Streamlit on port 8000, CORS and XSRF
off). Nothing in the code changes for Databricks; the data package sits in
`data/` inside the uploaded folder, so no `COSTBOT_DATA_DIR` is needed.

1. On the corporate laptop, copy the working folder (zip of `main` + the real
   package in `data/`) to a folder named `costbot`. Delete `.venv`,
   `__pycache__` and `validation_report.txt` from the copy.
2. Databricks Apps refuse any file above 10 MB. Delete large files the app
   does not read, e.g. `data/extracted_rates/path_b_v2_qac_embeddings.json`.
   The app reads only the CSVs listed in `costbot/data.py` and
   `_golden_baseline.json` (tests only).
3. Workspace > Users > <your e-mail>: drag the `costbot` folder in.
4. Compute > Apps > Create app > Custom, name `costbot`. Wait for it to exist.
5. Deploy, source code path `Workspace/Users/<your e-mail>/costbot`.
6. Open the app link. The header must not say "mock data".

Redeploy after a code change: download the new `main` zip, replace the code
files in the workspace folder (keep `data/`), Deploy again.
