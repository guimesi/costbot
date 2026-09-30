# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo.

## What this is

GP Screening Cost Estimator: a Streamlit POC that produces Class 5 screening
cost estimates for capital projects from scope parameters. Up to 10
deterministic models fire progressively as the user adds inputs; an ensemble
combines them into P50, a P20 to P80 range and a confidence tier.
No LLM, no database, no Spark. Everything runs from flat files in `data/`.

The spec is the manager's brief in `docs/spec/task_brief_2026-09-15.md` plus
the update email in `docs/spec/requirement_update_2026-09-16.md` (Sep 16).
`docs/spec/wireframe_v1.md` is an OLDER UX state and is superseded where they
conflict. `README.md` at the root is the repo's own readme, not the spec. The reference
implementation (`cost_bot_api.py` and 15 other modules) is confidential and not
tracked; the files the manager shares are dropped in `reference/` (gitignored) and
compared module by module in `docs/PARITY_cost_bot_api.md`. Ported so far:
`cost_bot_api.py`, `analogue_estimator.py`, `onshore_calculator.py`. Treat those
files, then README/email, as the source of truth and flag deviations instead of
silently changing them.

## Layout

| Path | Role |
|---|---|
| `app.py` | Streamlit entry point: page config, session-state init, header, `st.navigation` (top) over `app_pages/`. |
| `app_pages/estimator.py` | Inputs (left) + live readiness and results (right). Direct script, no `main()`. |
| `app_pages/models.py`, `app_pages/data.py` | Reference pages: model specs / routing / reported accuracy, and the loaded data package. |
| `ui/common.py` | `load_data()` (cached DataStore), labels, `musd`/`musd_md` formatters, mock detection. |
| `ui/cards.py` | Fragment cards that edit lists in session_state (equipment, scope items) and their callbacks. |
| `ui/results.py` | Readiness checklist, KPI row, Altair model chart, per-model tabs, analogues, bid check, what-if, download. |
| `.streamlit/config.toml` | Theme (light, navy accent, Inter). The only place looks are defined; no CSS in code. |
| `costbot/` | The engine as a package. `constants.py`, `data.py`, `escalation.py`, `models/<one file per model>.py`, `ensemble.py`, `screening.py`, `report.py`. `models/benchmark.py` is the reference analogue model; `models/benchmark_engine.py` the first build's size-band variant, chosen with `scope['benchmark_mode']` (engine default `reference`; the app selects `engine`). |
| `engine.py` | Compatibility facade re-exporting every `costbot` name. Tests and scripts still import from it; new code imports from `costbot.*`. |
| `tests/test_golden_baseline.py` | Runs the 4 calculators against `data/extracted_files/_golden_baseline.json`; script and pytest. |
| `scripts/generate_mock_data.py` | Writes the synthetic `data/` package (seed 42). |
| `scripts/smoke_test.py` | Runs the DEMO_SCRIPT scenarios through the engine, no UI. |
| `scripts/ui_test.py` | Headless Streamlit `AppTest`: fills scenario 1, exercises the list cards, clicks Run, renders every page. |
| `scripts/evaluate_truth.py` | LOOCV hit rate at +/-30% per archetype from `project_truth.csv` (ensemble P50: what a user sees). Meaningless on mock data. |
| `scripts/evaluate_harness.py` | The reference `evaluation_harness.py` convention: every model alone, any model within +/-30% counts, per-model matrix. This is what the brief's 40/52 measures. |
| `tests/` | pytest: ensemble rules, CP30, bid validation, equipment vector, readiness, report, golden baseline. |
| `docs/` | `spec/` (manager's brief, email, wireframe), app documentation, demo script, review, backlog, validation runbook, validation rounds (`VALIDATION_2026-09-28.md`, `VALIDATION_2026-09-30.md`), parity notes. |
| `Makefile` | `make install`, `make test`, `make run`, `make mock`, `make screenshots`, `make evaluate`. |
| `scripts/screenshot.py` | Boots the app and captures the main screens with Playwright + local Chrome. |
| `scripts/validate.py` | Runs every check and writes `validation_report.txt` (redacted) for the real-data validation. |
| `data/` | Mock data package (tracked). Real data goes in `data/_real/` (gitignored) or wherever `COSTBOT_DATA_DIR` points. |
| `docs/APP_DOCUMENTATION.md`, `docs/DEMO_SCRIPT.md` | Docs from the first build, aligned on 2026-09-26; accuracy numbers in them are unverified. |

## Run and test

```bash
/opt/anaconda3/bin/python3.13 -m venv .venv      # once (system 3.14 has no packages)
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/generate_mock_data.py   # only if data/ is missing or schema changed
.venv/bin/python scripts/smoke_test.py           # engine end-to-end, must print SMOKE OK
.venv/bin/python -m pytest tests -q              # unit tests + golden baseline (exit 0 required)
.venv/bin/python tests/test_golden_baseline.py   # same golden check with a readable report
.venv/bin/python scripts/ui_test.py              # headless UI, must print UI OK
.venv/bin/streamlit run app.py                   # UI on http://localhost:8501
```

`make test` runs all of them. Run it before every commit that touches `costbot/`, `app_pages/` or `ui/`.

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

- Add a model as `costbot/models/<name>.py` exposing `run_<name>(scope, data)`,
  register it in `_MODEL_FN_MAP` (`costbot/screening.py`) and in
  `ARCHETYPE_MODELS` (`costbot/constants.py`), and add its name to the
  facade list in `engine.py`.
- Cross-module imports inside the package are explicit (`from costbot.constants import X`);
  no star imports, no imports from `engine`.

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
- Benchmark has two variants behind one `model_id`: `benchmark_mode='reference'` (engine default,
  the analogue_estimator port) or `'engine'` (first build, size band; the app's default since 2026-09-30). `benchmark_compare=True`
  makes `screen_project` also run the other one into `results['benchmark_alternate']`. Pool
  models take `exclude_planview_ids` for LOOCV; never read the project's own pool row otherwise.

## UI conventions

- Pages are direct scripts under `app_pages/`; shared logic goes in `ui/` or `costbot/`,
  never copied between pages. Each page that needs data calls `ui.common.load_data()`.
- Navigation is `st.navigation(..., position="top")` in `app.py`; add a page there.
- No injected CSS or HTML for styling; theme lives in `.streamlit/config.toml`. Use native
  elements: `st.container(border=True)` cards, `st.metric(border=True)`, `st.badge` and
  `:green-badge[...]` inline badges, Material icons (`:material/name:`), sentence case labels.
- Charts are Altair (or `st.bar_chart`), not Plotly.
- Any `$` inside `st.markdown`/`st.caption` text must be escaped (`musd_md`), otherwise
  Streamlit renders `$...$` as LaTeX. Widget values (`st.metric`) are not markdown.
- The readiness checklist is `costbot.screening.model_readiness(scope)`: it predicts firing
  without computing. Keep its gates in sync with the runners; `tests/test_readiness.py`
  asserts it matches `screen_project` on the smoke scenarios.
- `scripts/ui_test.py` drives the real widgets by `key`; keep keys stable or update the test.

- List-editing cards (equipment, scope items) are `st.fragment`s with
  `on_click` callbacks. Never call `st.rerun()` after a button click; it
  doubles the rerun and shows as a page reload on slow links.
- Session state keys are initialised once at the top of `app.py` with `setdefault`.
- Use `width='stretch'`, never `use_container_width`.

## Reference parity

`cost_bot_api.py` (the spec's source of truth) was compared line by line on
2026-09-29: `docs/PARITY_cost_bot_api.md`. Routing, exclusions, ensemble rules,
calculator input handling and ranges, EquipmentVector gates, Unconventional
interpolation and analogue scoring follow the API. First-build variations
survive only behind `scope['ensemble_mode'] = 'engine'` for evaluation.
Reference files live in `reference/` (gitignored). When a new reference file
arrives, extend the parity doc and align the corresponding module.

## Known deviations from the README (need manager sign-off, do not "fix")

- README excludes Benchmark for `offshore_fpso` and `onshore_unconventional`;
  engine removed those exclusions.
- README says OSBL runs whenever any model fires; engine runs it only when
  Calculator_Onshore yields an ISBL.
- README lists 9 models; the app has 10 (Composite added from the wireframe).
- Docs say brownfield uses 1.30; the API sends `BF-expansion` (2.61) for every
  brownfield / expansion / modification scope. 1.30 (`BF-unit-mod`) is reached only
  when the facility name says modification / conversion / debottleneck, or by a direct
  calculator call (`calculator_scope_type`). Ported verbatim from `onshore_calculator.py`.
- Calculator_Onshore converts the capacity unit when it can (KBPD -> BPD); the
  reference uses the raw number whatever the unit. Unknown units: raw + warning.

## Style

- Python 3.13, pandas/numpy/sklearn/altair/streamlit only (Streamlit >= 1.52 for horizontal containers, badges, `width=`). No new deps
  without a reason in the PR.
- Keep the engine pure: no Streamlit imports in `engine.py`.
- Commit messages: imperative, one line summary, body explains why.
