# Validation runbook (real data package)

**Short version:** install, copy the real files into `data/`, run
`python scripts/validate.py`, send back `validation_report.txt`. Everything
below is the same thing step by step.

Goal: run this exact code against the confidential package and bring back
numbers, without the data ever leaving the corporate environment.

## 0. Before touching the data

```bash
python --version            # 3.10+ is fine; developed on 3.13
python -m pip install -r requirements.txt -r requirements-dev.txt
python -c "import streamlit; print(streamlit.__version__)"   # must be >= 1.52
make test                   # or the four commands in CLAUDE.md; all green on the mock package
```

If Streamlit is older than 1.52 and cannot be upgraded, stop here and say so:
the UI uses horizontal containers, badges and `width=`, which older versions
do not have. The engine and the scripts still work; only the app does not.

## 1. Put the data in place

Option A (simplest): copy the real CSVs and `extracted_files/_golden_baseline.json`
over the mock ones in `data/`. The "synthetic package" warning on the Data page
disappears by itself (it is decided from the data, not from a file).

Option B (safer against accidental commits): copy the package to `data/_real/`
(gitignored) and export `COSTBOT_DATA_DIR=$PWD/data/_real`. For a Databricks
App add it to `app.yaml` under `env:`.

Never commit the real files. `git status` must not list them.

## 2. Run, in this order

```bash
python scripts/smoke_test.py                       # engine on real data; a scenario may legitimately not fire
python tests/test_golden_baseline.py               # expect the 12 documented XFAILs and zero FAIL
python scripts/evaluate_truth.py --redact --csv results.csv
python scripts/ui_test.py                          # headless UI
streamlit run app.py                               # click through DEMO_SCRIPT scenarios 1 to 4
```

`evaluate_truth.py` prints the columns it detected in `project_truth.csv`
first. If it says it cannot find the TEC or archetype column, note the
real column names; that is a two-line fix in `CANDIDATES`.

## 3. Bring back (no project names needed)

- The per-archetype table printed by `evaluate_truth.py` (with `--redact`,
  the misses list is safe too). Reference to beat: 40/52 (77%) at +/-30%.
- The summary block of `test_golden_baseline.py` (PASS / XFAIL / FAIL counts
  and the names of any FAIL).
- The last line of `smoke_test.py` and, if it failed, which scenario and why.
- Screenshots of anything that looks wrong in the app.
- The Streamlit and Python versions in use.

## 4. What to expect to differ from the mock

- Smoke scenario expectations were written on synthetic data; a "no analogue
  above threshold" on real data is information, not a bug.
- Comparable projects with 0.00 match for archetype-only inputs is a known
  engine quirk (see BACKLOG).
- Timings should stay in the tens of milliseconds per run.
