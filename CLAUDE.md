# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo.

## What this is

GP Screening Cost Estimator: a Streamlit POC that produces Class 5 screening
cost estimates for capital projects from scope parameters. Up to 10
deterministic models fire progressively as the user adds inputs; an ensemble
combines them into P50, a P20 to P80 range and a confidence tier.
No LLM, no database, no Spark. Everything runs from flat files in `data/`.

The spec is the manager's brief in `README.md` (Sep 15, 2026) plus the
update email in `LATEST_REQUIREMENT_UPDATE_EMAIL.md` (Sep 16). `wireframe.md`
is an OLDER UX state and is superseded where they conflict. The reference
implementation (`cost_bot_api.py` and 15 other modules) is NOT in this repo;
it lives in a confidential zip we do not have. Treat README/email as the
source of truth for behaviour and flag deviations instead of silently
changing them.

## Layout

| Path | Role |
|---|---|
| `app.py` | Streamlit UI, 5 tabs. Builds a `scope` dict and calls `screen_project`. |
| `engine.py` | All models, ensemble, CP30 escalation, bid validation, HTML report. Single module by design. |
| `test_golden_baseline.py` | Runs the 4 calculators against `data/extracted_files/_golden_baseline.json`. |
| `scripts/generate_mock_data.py` | Writes the synthetic `data/` package (seed 42). |
| `scripts/smoke_test.py` | Runs the DEMO_SCRIPT scenarios through the engine, no UI. |
| `scripts/ui_test.py` | Headless Streamlit `AppTest`: fills scenario 1, exercises the list cards, clicks Run. |
| `scripts/evaluate_truth.py` | LOOCV hit rate at +/-30% per archetype from `project_truth.csv`. Meaningless on mock data. |
| `tests/` | pytest unit tests for ensemble rules, CP30, bid validation, equipment vector. |
| `docs/` | Review of spec vs implementation and the backlog. |
| `data/` | Mock data package (tracked). Real data goes in `data/_real/` (gitignored). |
| `APP_DOCUMENTATION.md`, `DEMO_SCRIPT.md` | AI-written docs from the first build; accuracy numbers in them are unverified. |

## Run and test

```bash
/opt/anaconda3/bin/python3.13 -m venv .venv      # once (system 3.14 has no packages)
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/generate_mock_data.py   # only if data/ is missing or schema changed
.venv/bin/python scripts/smoke_test.py           # engine end-to-end, must print SMOKE OK
.venv/bin/python test_golden_baseline.py         # calculators vs snapshot, exit 0 required
.venv/bin/python -m pytest tests -q              # unit tests
.venv/bin/python scripts/ui_test.py              # headless UI, must print UI OK
.venv/bin/streamlit run app.py                   # UI on http://localhost:8501
```

Run all four before every commit that touches `engine.py` or `app.py`.

Production environment with the real package: `export COSTBOT_DATA_DIR=/path/to/data`
before `streamlit run` or any script; no code edit needed.

## Data: mock vs real

- `data/` is SYNTHETIC. Row counts and column names match what `engine.py`
  reads; values are random with plausible magnitudes. Never quote accuracy
  numbers computed on it.
- `_golden_baseline.json` is a snapshot of engine output, not reference
  values. After an intentional model change, regenerate it with the mock
  script and say so in the commit message.
- If the real package ever arrives: put it in `data/_real/`, point
  `DataStore(data_dir=...)` at it, never commit it.

## Engine conventions

- Every model runner is `run_<model>(scope, data) -> dict` with `can_fire`,
  `model_id`, `estimate_musd`, `estimate_low_musd`, `estimate_high_musd`,
  and `no_fire_reason` when it cannot fire. Component models set
  `is_component=True` and stay out of the ensemble median.
- `screen_project` swallows exceptions per model into `no_fire_reason`, so a
  `NameError` looks like "model did not fire". The smoke test greps for
  "not defined" to catch that.
- Pool estimates are in 2024 USD; `basis_year != 2024` triggers CP30
  escalation at the GOM index. Calculators are not escalated by CP30.
- Benchmark region comes from `scope['country']`, derived from the UI
  location via `resolve_country`. Keep both in sync when adding locations.
- Archetype exclusions live in `ARCHETYPE_EXCLUSIONS`; the HTML report reads
  from it, do not hard-code rule lists elsewhere.
- UI dropdown contents (`FACILITY_TYPE_OPTIONS`, `LOCATION_OPTIONS`) are
  defined in the engine next to the tables they must match. Add there, not in app.py.
- Models may return a `warning` string; the UI and the HTML report surface it.

## UI conventions

- List-editing cards (equipment, scope items) are `st.fragment`s with
  `on_click` callbacks. Never call `st.rerun()` after a button click; it
  doubles the rerun and shows as a page reload on slow links.
- Session state keys are initialised once at the top of `app.py` with `setdefault`.
- Use `width='stretch'`, never `use_container_width`.

## Known deviations from the README (need manager sign-off, do not "fix")

- README excludes Benchmark for `offshore_fpso` and `onshore_unconventional`;
  engine removed those exclusions.
- README says OSBL runs whenever any model fires; engine runs it only when
  Calculator_Onshore yields an ISBL.
- README lists 9 models; the app has 10 (Composite added from the wireframe).
- `TEC_MULTIPLIERS['brownfield']=1.30` is defined but plain brownfield scope
  uses the expansion multiplier 2.61 on purpose (see comment in
  `run_calculator_onshore`). Docs say 1.30.

## Style

- Python 3.13, pandas/numpy/sklearn/plotly/streamlit only. No new deps
  without a reason in the PR.
- Keep the engine pure: no Streamlit imports in `engine.py`.
- Commit messages: imperative, one line summary, body explains why.
